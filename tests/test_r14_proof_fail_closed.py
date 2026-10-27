"""R14: tamper-resistant, zero-credit Flask quota attestation tests."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from integration import run_r13_two_replica_quota as r
from scripts import verify_official_replica_quota_r11 as proof
from scripts.verify_official_replica_quota_r11 import VerificationFailure
from tests.test_r14_scoped_fixture_cleanup import account, env


def fixture(root):
    for rel in proof.SOURCES:
        path=root / rel
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('synthetic '+rel)
    return {
        'version':'R11-derived-V19.9',
        'scope':'two original Flask replicas + local Firebase Auth/RTDB emulators only',
        'validated':True,
        'checks':{key:True for key in proof.CHECKS},
        'generated_utc':'2026-10-27T00:00:00+00:00',
        'source_sha256':{rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in proof.SOURCES},
        'additional_acceptance_points':0,
        'user_data_in_report':False,
    }


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.report=fixture(self.root)
        self.patcher=patch.object(r,'ROOT',self.root)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop();self.temp.cleanup()

    def test_untampered_proof_is_accepted(self):
        r.validate_proof(self.report)

    def test_reject_false_check(self):
        tamper=copy.deepcopy(self.report)
        tamper['checks'][proof.CHECKS[0]]=False
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_missing_check(self):
        tamper=copy.deepcopy(self.report);tamper['checks'].pop(proof.CHECKS[1])
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_extra_check(self):
        tamper=copy.deepcopy(self.report);tamper['checks']['faked_integrated_runtime']=True
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_missing_source(self):
        tamper=copy.deepcopy(self.report);tamper['source_sha256'].pop(proof.SOURCES[1])
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_modified_source(self):
        (self.root/proof.SOURCES[1]).write_text('modified')
        with self.assertRaises(VerificationFailure):r.validate_proof(self.report)

    def test_reject_linked_source(self):
        target=self.root/proof.SOURCES[1]
        target.unlink();target.symlink_to(self.root/proof.SOURCES[0])
        with self.assertRaises(VerificationFailure):r.validate_proof(self.report)

    def test_reject_extra_credit_even_if_checks_pass(self):
        tamper=copy.deepcopy(self.report);tamper['additional_acceptance_points']=1
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_boolean_fake_zero_credit(self):
        tamper=copy.deepcopy(self.report);tamper['additional_acceptance_points']=False
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_user_data_claim(self):
        tamper=copy.deepcopy(self.report);tamper['user_data_in_report']=True
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_unexpected_token_field(self):
        tamper=copy.deepcopy(self.report);tamper['idToken']='accidental-leak'
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_reject_wrong_scope(self):
        tamper=copy.deepcopy(self.report);tamper['scope']='production firebase'
        with self.assertRaises(VerificationFailure):r.validate_proof(tamper)

    def test_failed_teardown_prevents_validated_file(self):
        fake_a=Mock();fake_b=Mock()
        fake_a.poll.return_value=None;fake_b.poll.return_value=None
        with patch.object(r,'synthetic_signup',return_value=account()), \
             patch.object(r,'validate_emulator_environment'), \
             patch.object(r,'start_replica',side_effect=[fake_a,fake_b]), \
             patch.object(r,'wait_health'), \
             patch.object(r,'verify_quota',return_value=self.report), \
             patch.object(r,'free_loopback_port',side_effect=[30001,30002]), \
             patch.object(r.time,'time',return_value=30.0), \
             patch.object(r,'cleanup_fixture',side_effect=VerificationFailure('cleanup failed')), \
             patch.object(r,'QUOTA_PROOF','evidence/generated/r14.json'):
            with self.assertRaises(VerificationFailure):r.execute(env())
        self.assertFalse((self.root/'evidence/generated/r14.json').exists())
        fake_a.terminate.assert_called_once();fake_b.terminate.assert_called_once()

    def test_flask_child_does_not_receive_login_token(self):
        fake_a=Mock();fake_b=Mock()
        fake_a.poll.return_value=None;fake_b.poll.return_value=None
        observed=[]
        def spawn(label,port,childenv):
            observed.append(childenv.copy())
            return (fake_a,fake_b)[len(observed)-1]
        with patch.object(r,'synthetic_signup',return_value=account()), \
             patch.object(r,'validate_emulator_environment'), \
             patch.object(r,'start_replica',side_effect=spawn), \
             patch.object(r,'wait_health'), \
             patch.object(r,'verify_quota',return_value=self.report), \
             patch.object(r,'free_loopback_port',side_effect=[30001,30002]), \
             patch.object(r.time,'time',return_value=30.0), \
             patch.object(r,'cleanup_fixture') as cleanup, \
             patch.object(r,'QUOTA_PROOF','evidence/generated/r14.json'):
            self.assertTrue(r.execute(env())['validated'])
        self.assertEqual(len(observed),2)
        self.assertTrue(all('COURSESPHERE_R11_FIREBASE_ID_TOKEN' not in x for x in observed))
        self.assertEqual(cleanup.call_count,1)

if __name__=='__main__':unittest.main()
