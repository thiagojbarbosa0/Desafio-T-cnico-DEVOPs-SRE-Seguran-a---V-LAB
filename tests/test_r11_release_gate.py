"""R11 source-bound proof gate; refuse synthetic and stale claims."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.release_gate_r11 import assess, add_r11
from scripts.verify_official_replica_quota_r11 import OUT, SOURCES, CHECKS, ROOT

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for src in SOURCES:
            dst = self.root/src
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes((ROOT/src).read_bytes())
        p = self.root/OUT
        p.parent.mkdir(parents=True,exist_ok=True)
        self.proof = {
            'version':'R11-derived-V19.9','validated':True,
            'scope':'two original Flask replicas + local Firebase Auth/RTDB emulators only',
            'checks':{name:True for name in CHECKS},
            'additional_acceptance_points':0,'user_data_in_report':False,
            'source_sha256':{path:hashlib.sha256((self.root/path).read_bytes()).hexdigest() for path in SOURCES},
        }
        self.write()
    def tearDown(self): self.temp.cleanup()
    def write(self):
        (self.root/OUT).write_text(json.dumps(self.proof))
    def test_accepts_current_shape_without_awarding_points(self):
        outcome=assess(self.root)
        self.assertTrue(outcome['confirmed_current_source'])
        self.assertEqual(outcome['additional_acceptance_points'],0)
    def test_rejects_missing_proof(self):
        (self.root/OUT).unlink()
        self.assertFalse(assess(self.root)['confirmed_current_source'])
    def test_rejects_stale_original_backend(self):
        (self.root/'backend/endpoints.py').write_text('changed')
        self.assertFalse(assess(self.root)['confirmed_current_source'])
    def test_rejects_missing_hash_or_extra_check(self):
        self.proof['source_sha256'].pop(SOURCES[0]);self.write()
        self.assertFalse(assess(self.root)['confirmed_current_source'])
        self.proof['source_sha256'][SOURCES[0]]=hashlib.sha256((self.root/SOURCES[0]).read_bytes()).hexdigest()
        self.proof['checks']['fake']=True;self.write()
        self.assertFalse(assess(self.root)['confirmed_current_source'])
    def test_rejects_spurious_acceptance_credit(self):
        for val in (True,1,100,'0'):
            with self.subTest(value=val):
                self.proof['additional_acceptance_points']=val;self.write()
                self.assertFalse(assess(self.root)['confirmed_current_source'])
    def test_rejects_untrusted_scope_or_report_privacy(self):
        self.proof['scope']='two fake HTTP servers'
        self.write();self.assertFalse(assess(self.root)['confirmed_current_source'])
        self.proof['scope']='two original Flask replicas + local Firebase Auth/RTDB emulators only'
        self.proof['user_data_in_report']=True
        self.write();self.assertFalse(assess(self.root)['confirmed_current_source'])
    def test_rejects_linked_source_or_proof(self):
        source=self.root/SOURCES[0]
        source.unlink();source.symlink_to(ROOT/SOURCES[0])
        self.assertFalse(assess(self.root)['confirmed_current_source'])
    def test_annotate_keeps_submission_blocked(self):
        r=add_r11({'ready_for_submission':True},self.root)
        self.assertFalse(r['ready_for_submission'])
        self.assertEqual(r['r11_original_flask_two_replica_quota']['additional_acceptance_points'],0)

if __name__=='__main__': unittest.main()
