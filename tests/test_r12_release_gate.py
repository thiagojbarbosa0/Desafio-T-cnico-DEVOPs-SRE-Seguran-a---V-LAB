"""R12 evidence gate adversarial checks; entirely offline."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.prove_r12_strict_json import ROOT, OUT, SOURCES, EXPECTED
from scripts.release_gate_r12 import assess, add_r12


class GateR12(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory()
        self.root=Path(self.scratch.name)
        for name in SOURCES:
            dest=self.root/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT/name).read_bytes())
        self.path=self.root/OUT
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.doc={
            'version':'R12-derived-V19.9','validated':True,
            'scope':'standard-library strict JSON parser, offline only; no Flask/Firebase/Docker claims',
            'tests_run':EXPECTED,'skipped':0,'failures':0,'errors':0,
            'additional_acceptance_points':0,
            'source_sha256':{p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in SOURCES},
        }
        self.save()
    def tearDown(self):self.scratch.cleanup()
    def save(self):self.path.write_text(json.dumps(self.doc))

    def test_valid_offline_proof_is_zero_weight(self):
        result=assess(self.root)
        self.assertTrue(result['confirmed_current_source'])
        self.assertEqual(result['additional_acceptance_points'],0)

    def test_never_claims_ready_for_submission(self):
        result=add_r12({'ready_for_submission':True},self.root)
        self.assertFalse(result['ready_for_submission'])

    def test_missing_report_fails_closed(self):
        self.path.unlink()
        self.assertFalse(assess(self.root)['confirmed_current_source'])

    def test_modified_source_invalidates_proof(self):
        (self.root/'backend/strict_request_json.py').write_text('tampered')
        result=assess(self.root)
        self.assertFalse(result['confirmed_current_source'])
        self.assertTrue(any('stale_source' in x for x in result['reasons']))

    def test_symlinked_source_is_rejected(self):
        p=self.root/'backend/strict_request_json.py'
        p.unlink();p.symlink_to(ROOT/'backend/strict_request_json.py')
        self.assertFalse(assess(self.root)['confirmed_current_source'])

    def test_forged_acceptance_points_fail(self):
        for amount in (1,100,True,'0'):
            with self.subTest(amount=amount):
                self.doc['additional_acceptance_points']=amount
                self.save()
                self.assertFalse(assess(self.root)['confirmed_current_source'])

    def test_skipped_or_failed_tests_cannot_be_pass(self):
        for field in ('skipped','errors','failures'):
            with self.subTest(field=field):
                self.doc[field]=1;self.save()
                self.assertFalse(assess(self.root)['confirmed_current_source'])
                self.doc[field]=0

    def test_scope_cannot_upgrade_to_real_firebase(self):
        self.doc['scope']='original Flask + Firebase emulators'
        self.save()
        self.assertFalse(assess(self.root)['confirmed_current_source'])

    def test_missing_source_binding_fails(self):
        del self.doc['source_sha256']['backend/endpoints.py']
        self.save()
        self.assertFalse(assess(self.root)['confirmed_current_source'])


if __name__ == '__main__':unittest.main()
