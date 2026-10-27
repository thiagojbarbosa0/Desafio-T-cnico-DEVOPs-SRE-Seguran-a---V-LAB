"""R13 coordinator failure-safety tests; do NOT imply real Firebase is running."""
import json
import base64
import unittest
from unittest.mock import Mock, patch

from integration import run_r13_two_replica_quota as runner
from scripts.verify_official_replica_quota_r11 import VerificationFailure




def fake_account(uid='synthetic123'):
    body = json.dumps({'sub':uid, 'aud':runner.PROJECT, 'iss':'https://securetoken.google.com/'+runner.PROJECT}).encode()
    token = 'e30.' + base64.urlsafe_b64encode(body).rstrip(b'=').decode() + '.c2ln'
    return runner.SyntheticAccount(uid,token)

class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(runner.REQUIRED_ENV)

    def test_accepts_dedicated_emulators_without_credentials(self):
        self.assertIsNone(runner.check_environment(self.env))

    def test_rejects_missing_emulator_flag(self):
        data = dict(self.env); data.pop('COURSESPHERE_USE_FIREBASE_EMULATORS')
        with self.assertRaises(VerificationFailure): runner.check_environment(data)

    def test_rejects_live_mode(self):
        with self.assertRaises(VerificationFailure):
            runner.check_environment(dict(self.env, COURSESPHERE_USE_FIREBASE_EMULATORS='0'))

    def test_rejects_non_demo_project(self):
        with self.assertRaises(VerificationFailure):
            runner.check_environment(dict(self.env, GCLOUD_PROJECT='production'))

    def test_rejects_remote_auth(self):
        with self.assertRaises(VerificationFailure):
            runner.check_environment(dict(self.env, FIREBASE_AUTH_EMULATOR_HOST='firebase.test:9099'))

    def test_rejects_remote_database(self):
        with self.assertRaises(VerificationFailure):
            runner.check_environment(dict(self.env, FIREBASE_DATABASE_EMULATOR_HOST='10.0.0.2:9000'))

    def test_rejects_credential_configurations(self):
        for key in runner.FORBIDDEN_ENV:
            with self.subTest(key=key), self.assertRaises(VerificationFailure):
                runner.check_environment(dict(self.env, **{key:'/private/credentials.json'}))

    def test_rejects_other_demo_project(self):
        with self.assertRaises(VerificationFailure):
            runner.check_environment(dict(self.env, GCLOUD_PROJECT='demo-other'))

    def test_signup_rejects_transport_failure_without_leaking(self):
        with patch.object(runner.http.client, 'HTTPConnection') as connection:
            connection.return_value.request.side_effect=ConnectionRefusedError('secret user data')
            with self.assertRaisesRegex(VerificationFailure, 'not reachable') as err:
                runner.synthetic_signup()
            self.assertNotIn('secret', str(err.exception))

    def test_signup_rejects_malformed_json(self):
        with patch.object(runner.http.client, 'HTTPConnection') as conn:
            conn.return_value.getresponse.return_value.status=200
            conn.return_value.getresponse.return_value.read.return_value=b'not json'
            with self.assertRaises(VerificationFailure): runner.synthetic_signup()

    def test_signup_rejects_absent_token(self):
        with patch.object(runner.http.client, 'HTTPConnection') as conn:
            conn.return_value.getresponse.return_value.status=200
            conn.return_value.getresponse.return_value.read.return_value=b'{"localId":"a"}'
            with self.assertRaises(VerificationFailure): runner.synthetic_signup()

    def test_signup_rejects_redirect_without_following(self):
        with patch.object(runner.http.client, 'HTTPConnection') as conn:
            conn.return_value.getresponse.return_value.status=302
            conn.return_value.getresponse.return_value.read.return_value=b''
            with self.assertRaises(VerificationFailure): runner.synthetic_signup()

    def test_signup_never_places_token_in_request_url(self):
        with patch.object(runner.http.client, 'HTTPConnection') as conn:
            conn.return_value.getresponse.return_value.status=200
            account = fake_account()
            conn.return_value.getresponse.return_value.read.return_value=json.dumps({'idToken':account.token,'localId':account.uid}).encode()
            created=runner.synthetic_signup()
            self.assertEqual(created,account)
            args, kwargs=conn.return_value.request.call_args
            self.assertEqual(args[0], 'POST')
            self.assertEqual(args[1], '/identitytoolkit.googleapis.com/v1/accounts:signUp?key=demo-key')
            self.assertNotIn(account.token, str(kwargs))

    def test_start_replica_no_shell_and_no_credentials(self):
        env=dict(self.env, FIREBASE_CREDENTIALS_FILE='should-be-removed')
        with patch.object(runner.subprocess, 'Popen') as spawn:
            runner.start_replica('official_api_a', 31001, env)
            args, kwargs=spawn.call_args
            self.assertEqual(args[0][0], runner.sys.executable)
            self.assertNotIn('FIREBASE_CREDENTIALS_FILE', kwargs['env'])
            self.assertEqual(kwargs['env']['COURSESPHERE_REPLICA_NAME'],'official_api_a')
            self.assertEqual(kwargs['stdout'],runner.subprocess.DEVNULL)
            self.assertEqual(kwargs['stderr'],runner.subprocess.DEVNULL)

    def test_start_replica_removes_stray_token_from_environment(self):
        env=dict(self.env,COURSESPHERE_R11_FIREBASE_ID_TOKEN='PRIVATE_TOKEN_SHOULD_STAY_PARENT')
        with patch.object(runner.subprocess,'Popen') as spawn:
            runner.start_replica('official_api_a',31001,env)
            forwarded=spawn.call_args.kwargs['env']
            self.assertNotIn('COURSESPHERE_R11_FIREBASE_ID_TOKEN',forwarded)

    def test_start_rejects_invalid_label(self):
        with self.assertRaises(VerificationFailure):
            runner.start_replica('untrusted_label', 30001, self.env)

    def test_start_rejects_invalid_port(self):
        with self.assertRaises(VerificationFailure):
            runner.start_replica('official_api_a', 80, self.env)

    def test_wait_health_rejects_process_exit(self):
        dead=Mock(); dead.poll.return_value=1
        with self.assertRaises(VerificationFailure): runner.wait_health(30001,dead,deadline_seconds=0.1)

    def test_stop_all_reaps_every_process(self):
        a=Mock(); b=Mock()
        a.poll.return_value=None; b.poll.return_value=0
        runner.stop_all([a,b])
        a.terminate.assert_called_once(); b.terminate.assert_not_called()
        a.wait.assert_called_once(); b.wait.assert_called_once()

    def test_stop_all_force_kills_hung_processes(self):
        from subprocess import TimeoutExpired
        a=Mock(); a.poll.return_value=None; a.wait.side_effect=[TimeoutExpired('flask',4),0]
        runner.stop_all([a]); a.terminate.assert_called_once(); a.kill.assert_called_once()

    def test_execute_deletes_stale_pass_before_environment_validation(self):
        fake=Mock(); fake.unlink=Mock()
        with patch.object(runner,'ROOT',Mock(__truediv__=Mock(return_value=fake))):
            with self.assertRaises(VerificationFailure): runner.execute({})
        fake.unlink.assert_called_once_with(missing_ok=True)

    def test_execute_writes_sanitized_proof_and_closes_both_replicas(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp)
            fake_a=Mock(); fake_b=Mock()
            fake_a.poll.return_value=None; fake_b.poll.return_value=None
            expected={'validated':True,'checks':{'quota_ok':True},'scope':'local emulator only'}
            with patch.object(runner,'ROOT',temp), \
                 patch.object(runner,'QUOTA_PROOF','evidence/generated/quota.json'), \
                 patch.object(runner,'synthetic_signup',return_value=fake_account()), \
                 patch.object(runner,'validate_emulator_environment'), \
                 patch.object(runner,'start_replica',side_effect=[fake_a,fake_b]), \
                 patch.object(runner,'wait_health'), \
                 patch.object(runner,'verify_quota',return_value=expected), \
                 patch.object(runner,'free_loopback_port',side_effect=[30001,30002]), \
                 patch.object(runner.time,'time',return_value=30.0), \
                 patch.object(runner,'cleanup_fixture'), \
                 patch.object(runner,'validate_proof'):
                result=runner.execute(self.env)
            text=(temp/'evidence/generated/quota.json').read_text()
            self.assertNotIn(fake_account().token,text)
            self.assertTrue(result['validated'])
            fake_a.terminate.assert_called_once()
            fake_b.terminate.assert_called_once()

    def test_execute_failure_never_leaves_old_pass_and_stops_servers(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            output=root/'evidence/generated/quota.json'
            output.parent.mkdir(parents=True)
            output.write_text('{"validated":true}')
            fake_a=Mock(); fake_b=Mock()
            fake_a.poll.return_value=None; fake_b.poll.return_value=None
            with patch.object(runner,'ROOT',root), \
                 patch.object(runner,'QUOTA_PROOF','evidence/generated/quota.json'), \
                 patch.object(runner,'synthetic_signup',return_value=fake_account()), \
                 patch.object(runner,'validate_emulator_environment'), \
                 patch.object(runner,'start_replica',side_effect=[fake_a,fake_b]), \
                 patch.object(runner,'wait_health'), \
                 patch.object(runner,'verify_quota',side_effect=VerificationFailure('not shared')), \
                 patch.object(runner,'free_loopback_port',side_effect=[30001,30002]), \
                 patch.object(runner.time,'time',return_value=30.0), \
                 patch.object(runner,'cleanup_fixture'), \
                 patch.object(runner,'validate_proof'):
                with self.assertRaises(VerificationFailure): runner.execute(self.env)
            self.assertFalse(output.exists())
            fake_a.terminate.assert_called_once()
            fake_b.terminate.assert_called_once()

    def test_main_returns_failure_when_environment_missing(self):
        with patch.object(runner,'execute',side_effect=VerificationFailure('private-secret-must-not-log')):
            from io import StringIO
            from contextlib import redirect_stdout
            buffer=StringIO()
            with redirect_stdout(buffer): result=runner.main()
            self.assertEqual(result,1)
            self.assertNotIn('private-secret',buffer.getvalue())


if __name__ == '__main__': unittest.main()
