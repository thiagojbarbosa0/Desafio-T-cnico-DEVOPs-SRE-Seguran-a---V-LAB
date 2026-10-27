"""R14 release evidence: scope, freshness, teardown, zero-point policy."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from scripts.release_gate_r14 import assess, add_r14
from scripts.verify_official_replica_quota_r11 import OUT
from tests.test_r11_release_gate import GateTests as LegacyGateTests


class CleanupGateTests(unittest.TestCase):
    def setUp(self):
        self.legacy = LegacyGateTests(methodName='test_accepts_current_shape_without_awarding_points')
        self.legacy.setUp()
        self.root=self.legacy.root
        self.proof=self.legacy.proof
        self.now=datetime(2026,10,27,10,0,tzinfo=timezone.utc)
        self.proof['generated_utc']=self.now.isoformat()
        self.proof['fixture_cleanup_verified']=True
        self.proof['proof_origin']='r14_scoped_emulator_coordinator'
        self.write()

    def tearDown(self):self.legacy.tearDown()

    def write(self):
        (self.root / OUT).write_text(json.dumps(self.proof),encoding='utf-8')

    def test_good_cleanup_proof_no_acceptance_points(self):
        result=assess(self.root,now=self.now)
        self.assertTrue(result['confirmed_current_source'])
        self.assertEqual(result['additional_acceptance_points'],0)
        gate=add_r14({'ready_for_submission':True},self.root)
        self.assertFalse(gate['ready_for_submission'])

    def test_previous_direct_r11_proof_is_not_cleanup_proof(self):
        del self.proof['fixture_cleanup_verified'];self.write()
        self.assertIn('scoped_fixture_cleanup_not_proved',assess(self.root,now=self.now)['reasons'])

    def test_incorrect_coordinator_rejected(self):
        self.proof['proof_origin']='manual-direct-r11';self.write()
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])

    def test_expired_proof_rejected(self):
        self.proof['generated_utc']=(self.now-timedelta(hours=25)).isoformat();self.write()
        self.assertIn('integrated_proof_expired',assess(self.root,now=self.now)['reasons'])

    def test_future_proof_rejected(self):
        self.proof['generated_utc']=(self.now+timedelta(minutes=6)).isoformat();self.write()
        self.assertIn('integrated_proof_from_future',assess(self.root,now=self.now)['reasons'])

    def test_naive_timestamp_rejected(self):
        self.proof['generated_utc']='2026-10-27T10:00:00';self.write()
        self.assertIn('untrusted_naive_timestamp',assess(self.root,now=self.now)['reasons'])

    def test_missing_timestamp_rejected(self):
        self.proof.pop('generated_utc');self.write()
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])

    def test_false_cleanup_marker_rejected(self):
        self.proof['fixture_cleanup_verified']=1;self.write()
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])
        self.proof['fixture_cleanup_verified']=False;self.write()
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])

    def test_changed_source_still_fails(self):
        (self.root/'backend/endpoints.py').write_text('tampered')
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])

    def test_wrong_sources_still_fail_even_with_cleanup_marker(self):
        self.proof['source_sha256']={};self.write()
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])

    def test_cleanup_proof_does_not_validate_externally_supplied_token(self):
        self.proof['additional_acceptance_points']=20;self.write()
        self.assertFalse(assess(self.root,now=self.now)['confirmed_current_source'])

if __name__=='__main__':unittest.main()
