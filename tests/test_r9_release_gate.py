"""R9 proof integrity: no stale, forged or cross-version evidence accepted."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prove_r9_transport import SOURCES
from scripts.release_gate_r9 import PROOF, REQUIRED, add_r9, assess_proof


class R9GateContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for rel in SOURCES:
            file=self.root/rel;file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text('fixture:'+rel,encoding='utf-8')
        self.record={
            'version':'R9-derived-V19.9','validated':True,
            'checks':{key:True for key in REQUIRED},
            'source_sha256':{p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in SOURCES},
            'additional_acceptance_points':0,
        }
        self.save()

    def save(self):
        file=self.root/PROOF;file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(json.dumps(self.record),encoding='utf-8')
    def verified(self): return assess_proof(self.root)['confirmed_current_source']
    def test_valid_but_no_points(self):
        self.assertTrue(self.verified())
        self.assertEqual(assess_proof(self.root)['additional_acceptance_points'],0)
    def test_missing_file_rejected(self):
        (self.root/PROOF).unlink();self.assertFalse(self.verified())
    def test_invalid_object_rejected(self):
        (self.root/PROOF).write_text('[]');self.assertFalse(self.verified())
    def test_wrong_version_rejected(self):
        self.record['version']='R8-derived-V19.9';self.save();self.assertFalse(self.verified())
    def test_failed_validation_rejected(self):
        self.record['validated']=False;self.save();self.assertFalse(self.verified())
    def test_check_int_instead_bool_rejected(self):
        self.record['checks'][REQUIRED[0]]=1;self.save();self.assertFalse(self.verified())
    def test_missing_check_rejected(self):
        self.record['checks'].pop(REQUIRED[0]);self.save();self.assertFalse(self.verified())
    def test_missing_binding_rejected(self):
        self.record['source_sha256'].pop(SOURCES[0]);self.save();self.assertFalse(self.verified())
    def test_extra_binding_rejected(self):
        self.record['source_sha256']['extra']='ab'*32;self.save();self.assertFalse(self.verified())
    def test_fake_acceptance_claim_rejected(self):
        self.record['additional_acceptance_points']=5;self.save();self.assertFalse(self.verified())
    def test_file_changed_rejected(self):
        (self.root/SOURCES[0]).write_text('new content');self.assertFalse(self.verified())
    def test_missing_source_rejected(self):
        (self.root/SOURCES[0]).unlink();self.assertFalse(self.verified())
    def test_symlink_source_rejected(self):
        file=self.root/SOURCES[0];file.rename(self.root/'copy.py');file.symlink_to(self.root/'copy.py')
        self.assertFalse(self.verified())
    def test_symlink_proof_rejected(self):
        file=self.root/PROOF;file.rename(self.root/'copy.json');file.symlink_to(self.root/'copy.json')
        self.assertFalse(self.verified())
    def test_oversized_proof_rejected(self):
        (self.root/PROOF).write_text(' ' *65537);self.assertFalse(self.verified())
    def test_source_size_bound_rejected(self):
        (self.root/SOURCES[0]).write_bytes(b'A'*3_000_001);self.assertFalse(self.verified())
    def test_add_r9_never_marks_submission_ready(self):
        report=add_r9({'ready_for_submission':True,'weighted_acceptance_verified_percent':100},self.root)
        self.assertFalse(report['ready_for_submission'])
        self.assertEqual(report['r9_synthetic_transport']['additional_acceptance_points'],0)
    def test_proof_never_awards_points_even_if_other_fields_present(self):
        self.record['weighted_acceptance_verified_percent']=100;self.save()
        self.assertTrue(self.verified())
        self.assertEqual(assess_proof(self.root)['additional_acceptance_points'],0)

if __name__=='__main__':unittest.main()
