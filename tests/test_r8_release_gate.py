"""Fail-closed evidence binding tests without requiring Docker or production services."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.prove_r8_atomic_audit import SOURCES
from scripts.release_gate_r8 import PROOF, REQUIRED, assess_proof, add_r8


class R8EvidenceContract(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for rel in SOURCES:
            path=self.root/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('test '+rel,encoding='utf-8')
        import hashlib
        self.record={
            'version':'R8-derived-V19.9',
            'validated':True,
            'checks':{k:True for k in REQUIRED},
            'source_sha256':{rel:hashlib.sha256((self.root/rel).read_bytes()).hexdigest() for rel in SOURCES},
            'additional_acceptance_points':0,
        }
        self.write()
    def write(self):
        path=self.root/PROOF
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.record),encoding='utf-8')
    def test_good_proof_confirmed_but_no_points(self):
        value=assess_proof(self.root)
        self.assertTrue(value['confirmed_current_source'])
        self.assertEqual(value['additional_acceptance_points'],0)
    def test_missing_proof_fails(self):
        (self.root/PROOF).unlink()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_stale_hash_fails(self):
        (self.root/SOURCES[0]).write_text('updated')
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_false_validation_fails(self):
        self.record['validated']=False;self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_non_boolean_check_fails(self):
        self.record['checks'][REQUIRED[0]]=1;self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_incomplete_check_fails(self):
        del self.record['checks'][REQUIRED[0]];self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_wrong_version_fails(self):
        self.record['version']='R7-derived-V19.9';self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_extra_file_hash_fails(self):
        self.record['source_sha256']['extra']='a'*64;self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_hash_changed_by_attacker_fails(self):
        self.record['source_sha256'][SOURCES[0]]='a'*64;self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_false_points_fails(self):
        self.record['additional_acceptance_points']=25;self.write()
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_symlinked_proof_fails(self):
        p=self.root/PROOF
        backup=self.root/'backup.json'
        p.rename(backup)
        p.symlink_to(backup)
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_symlinked_source_fails(self):
        p=self.root/SOURCES[0]
        backup=self.root/'backup.py'
        p.rename(backup)
        p.symlink_to(backup)
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_non_object_json_fails(self):
        (self.root/PROOF).write_text('[]')
        self.assertFalse(assess_proof(self.root)['confirmed_current_source'])
    def test_r8_wrapper_always_not_submission_ready(self):
        enriched=add_r8({'ready_for_submission':True,'weighted_acceptance_verified_percent':100},self.root)
        self.assertFalse(enriched['ready_for_submission'])
        self.assertEqual(enriched['r8_synthetic_atomic_audit']['additional_acceptance_points'],0)

if __name__=='__main__':unittest.main()
