"""R10 evidence cannot be forged, replayed or count as V19.15 acceptance."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from scripts.prove_r10_deadline import SOURCES
from scripts.release_gate_r10 import PROOF,REQUIRED,add_r10,assess_proof


class R10GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for rel in SOURCES:
            path=self.root/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('r10 fixture: '+rel)
        self.payload={'version':'R10-derived-V19.9','validated':True,
                      'checks':{key:True for key in REQUIRED},
                      'source_sha256':{rel:hashlib.sha256((self.root/rel).read_bytes()).hexdigest() for rel in SOURCES},
                      'additional_acceptance_points':0}
        self.save()

    def save(self):
        path=self.root/PROOF
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.payload))

    def valid(self):return assess_proof(self.root)['confirmed_current_source']

    def test_valid_zero_points(self):
        self.assertTrue(self.valid())
        self.assertEqual(assess_proof(self.root)['additional_acceptance_points'],0)

    def test_missing_proof(self):
        (self.root/PROOF).unlink();self.assertFalse(self.valid())

    def test_invalid_json(self):
        (self.root/PROOF).write_text('[');self.assertFalse(self.valid())

    def test_cross_version(self):
        self.payload['version']='R9-derived-V19.9';self.save();self.assertFalse(self.valid())

    def test_false_validation(self):
        self.payload['validated']=False;self.save();self.assertFalse(self.valid())

    def test_fake_boolean(self):
        self.payload['checks'][REQUIRED[0]]=1;self.save();self.assertFalse(self.valid())

    def test_missing_check(self):
        self.payload['checks'].pop(REQUIRED[0]);self.save();self.assertFalse(self.valid())

    def test_extra_check_rejected(self):
        self.payload['checks']['fake']=True;self.save();self.assertFalse(self.valid())

    def test_fake_acceptance(self):
        self.payload['additional_acceptance_points']=True;self.save();self.assertFalse(self.valid())

    def test_modified_source(self):
        (self.root/SOURCES[0]).write_text('changed');self.assertFalse(self.valid())

    def test_extra_binding(self):
        self.payload['source_sha256']['hidden']='0'*64;self.save();self.assertFalse(self.valid())

    def test_missing_binding(self):
        self.payload['source_sha256'].pop(SOURCES[0]);self.save();self.assertFalse(self.valid())

    def test_symlink_source(self):
        path=self.root/SOURCES[0]
        path.rename(self.root/'backed.txt')
        path.symlink_to(self.root/'backed.txt')
        self.assertFalse(self.valid())

    def test_symlink_proof(self):
        path=self.root/PROOF
        path.rename(self.root/'backed.json')
        path.symlink_to(self.root/'backed.json')
        self.assertFalse(self.valid())

    def test_oversized_proof(self):
        (self.root/PROOF).write_bytes(b' '*65537);self.assertFalse(self.valid())

    def test_missing_source(self):
        (self.root/SOURCES[0]).unlink();self.assertFalse(self.valid())

    def test_report_never_marks_ready(self):
        report=add_r10({'ready_for_submission':True},self.root)
        self.assertFalse(report['ready_for_submission'])
        self.assertTrue(report['r10_synthetic_absolute_deadline']['confirmed_current_source'])


if __name__=='__main__':unittest.main()
