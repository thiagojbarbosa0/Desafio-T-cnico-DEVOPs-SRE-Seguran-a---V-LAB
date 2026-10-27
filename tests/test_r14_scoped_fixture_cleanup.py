"""R14: real loopback HTTP cleanup tests, no Firebase SDK or credentials."""
from __future__ import annotations

import base64
from contextlib import ExitStack
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch

from integration import emulator_fixture_cleanup_r14 as fixtures
from scripts.verify_official_replica_quota_r11 import VerificationFailure


def account(uid='synthetic123', project=fixtures.PROJECT, **extra):
    payload = {'sub':uid, 'aud':project, 'iss':'https://securetoken.google.com/'+project}
    payload.update(extra)
    segment = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    return fixtures.SyntheticAccount(uid, 'e30.'+segment+'.c2ln')


def env():
    return {'COURSESPHERE_USE_FIREBASE_EMULATORS':'1', 'GCLOUD_PROJECT':fixtures.PROJECT,
            'FIREBASE_AUTH_EMULATOR_HOST':'127.0.0.1:9099',
            'FIREBASE_DATABASE_EMULATOR_HOST':'127.0.0.1:9000'}


class RecordingEmulator(BaseHTTPRequestHandler):
    records = []
    response_status = 200
    def log_message(self, *args):
        pass
    def _handle(self):
        n = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(n) if n else b''
        self.records.append((self.command, self.path, dict(self.headers), body))
        self.send_response(self.response_status)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(b'null' if self.command == 'GET' else b'{}')
    def do_DELETE(self): self._handle()
    def do_POST(self): self._handle()
    def do_GET(self): self._handle()


class CleanupTests(unittest.TestCase):
    def test_accept_valid_synthetic_account(self):
        fixtures.validate_account(account())

    def test_reject_uid_path_traversal(self):
        for uid in ('../../users','foo/bar','a.b','', 'x'*129, '%2F', 'á'):
            with self.subTest(uid=uid), self.assertRaises(VerificationFailure):
                fixtures.validate_account(account(uid))

    def test_reject_mismatched_subject(self):
        with self.assertRaises(VerificationFailure):
            fixtures.validate_account(fixtures.SyntheticAccount('other', account().token))

    def test_reject_other_demo_project(self):
        with self.assertRaises(VerificationFailure):
            fixtures.validate_account(account(project='demo-another'))

    def test_reject_missing_token(self):
        with self.assertRaises(VerificationFailure):
            fixtures.validate_account(fixtures.SyntheticAccount('synthetic123', ''))

    def test_reject_bad_jwt_claim_encoding(self):
        with self.assertRaises(VerificationFailure):
            fixtures.validate_account(fixtures.SyntheticAccount('synthetic123','e30.Zm9v.c2ln'))

    def test_reject_duplicate_claims(self):
        raw = '{"sub":"synthetic123","sub":"other","aud":"demo-coursesphere-vlab"}'
        bad = 'e30.' + base64.urlsafe_b64encode(raw.encode()).rstrip(b'=').decode() + '.c2ln'
        with self.assertRaises(VerificationFailure):
            fixtures.validate_account(fixtures.SyntheticAccount('synthetic123',bad))

    def test_fail_closed_wrong_emulator_environment(self):
        for key, val in [('GCLOUD_PROJECT','real-production'),
                         ('FIREBASE_DATABASE_EMULATOR_HOST','remote:9000'),
                         ('COURSESPHERE_USE_FIREBASE_EMULATORS','0'),
                         ('FIREBASE_CREDENTIALS_FILE','/secrets/live.json'),
                         ('GOOGLE_APPLICATION_CREDENTIALS','/secrets/live.json')]:
            with self.subTest(key=key), self.assertRaises(VerificationFailure):
                fixtures.cleanup(account(), dict(env(), **{key:val}))

    def test_real_http_cleanup_only_own_uid_and_quota(self):
        records = []
        class Handler(RecordingEmulator):
            pass
        Handler.records=records
        auth = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        db = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threads=[]
        for server in (auth, db):
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start();threads.append(thread)
        original=fixtures._local_request
        def reroute(port, method, path, **kwargs):
            return original(auth.server_port if port == 9099 else db.server_port,
                            method, path, **kwargs)
        try:
            with patch.object(fixtures,'_local_request',side_effect=reroute):
                fixtures.cleanup(account(),env())
        finally:
            for server in (auth,db): server.shutdown();server.server_close()
            for thread in threads: thread.join(timeout=2)
        self.assertEqual(len(records),5)
        paths=[record[1] for record in records]
        uid='synthetic123'
        key=hashlib.sha256(uid.encode()).hexdigest()
        self.assertEqual(paths[0],f'/users/{uid}.json?ns=demo-coursesphere-vlab-default-rtdb')
        self.assertEqual(paths[1],f'/server_security/rate_limits/{key}.json?ns=demo-coursesphere-vlab-default-rtdb')
        self.assertEqual(paths[2],paths[0])
        self.assertEqual(paths[3],paths[1])
        self.assertEqual(paths[4],'/identitytoolkit.googleapis.com/v1/accounts:delete?key=demo-key')
        self.assertEqual([rec[0] for rec in records],['DELETE','DELETE','GET','GET','POST'])
        self.assertEqual([rec[2].get('Authorization') for rec in records],['Bearer owner','Bearer owner','Bearer owner','Bearer owner',None])
        self.assertEqual(json.loads(records[4][3])['idToken'],account().token)
        self.assertNotIn(account().token,''.join(paths))
        self.assertNotIn('/users.json',''.join(paths))

    def test_stale_rtdb_node_blocks_auth_deletion(self):
        # Even HTTP 200 does not prove the data was actually removed.
        class StillPresent(RecordingEmulator):
            records=[]
        server=ThreadingHTTPServer(('127.0.0.1',0),StillPresent)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        original=fixtures._local_request
        def reroute(port, method, path, **kwargs):
            if method == 'GET':
                return b'{"still_here":true}'
            return original(server.server_port,method,path,**kwargs)
        try:
            with patch.object(fixtures,'_local_request',side_effect=reroute):
                with self.assertRaisesRegex(VerificationFailure,'not fully removed'):
                    fixtures.cleanup(account(),env())
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertFalse(any('accounts:delete' in r[1] for r in StillPresent.records))

    def test_server_rejects_cleanup_response(self):
        class Denied(RecordingEmulator):
            response_status=403
            records=[]
        server=ThreadingHTTPServer(('127.0.0.1',0),Denied)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with self.assertRaises(VerificationFailure):
                fixtures._local_request(server.server_port,'DELETE','/users/synthetic123.json')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_missing_server_is_not_claimed_as_cleanup_success(self):
        import socket
        with socket.socket() as s:
            s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
        with self.assertRaises(VerificationFailure):
            fixtures._local_request(port,'DELETE','/users/only-one.json',timeout=0.1)


if __name__=='__main__': unittest.main()
