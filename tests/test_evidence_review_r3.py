"""Evidence diagnostics fail closed and do not award acceptance points."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.review_evidence_freshness_r3 import assess,audit,SEMANTIC_KEYS,EVIDENCE_ROSTER

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'backend').mkdir()
        (self.root/'backend/endpoints.py').write_text('good')
        (self.root/'evidence/generated').mkdir(parents=True)
        self.path='evidence/generated/test.json'
        self.rec={'validated':True,'skipped':0,'source_sha256':{'backend/endpoints.py':hashlib.sha256(b'good').hexdigest()}}
        self.save()
    def save(self): (self.root/self.path).write_text(json.dumps(self.rec))
    def check(self): return assess(self.root,'test',self.path)
    def test_valid_only_means_source_consistency(self):self.assertTrue(self.check()['source_consistent'])
    def test_source_drift_fails(self):
        (self.root/'backend/endpoints.py').write_text('changed')
        self.assertFalse(self.check()['source_consistent'])
        self.assertIn('source_changed:backend/endpoints.py',self.check()['failures'])
    def test_invalid_status_fails(self):
        self.rec['validated']=1;self.save();self.assertFalse(self.check()['source_consistent'])
    def test_skipped_tests_fails(self):
        self.rec['skipped']=3;self.save();self.assertFalse(self.check()['source_consistent'])
    def test_missing_source_fails(self):
        self.rec['source_sha256']={};self.save();self.assertFalse(self.check()['source_consistent'])
    def test_no_user_supplied_path_escape(self):
        self.rec['source_sha256']={'../../passwd':'f'*64};self.save()
        self.assertFalse(self.check()['source_consistent'])
    def test_file_missing_fails(self):
        (self.root/self.path).unlink();self.assertFalse(self.check()['source_consistent'])
    def test_malformed_duplicate_json_fails(self):
        (self.root/self.path).write_text('{"validated":true,"validated":true}')
        self.assertFalse(self.check()['source_consistent'])
    def test_hash_syntax_strict(self):
        self.rec['source_sha256']={'backend/endpoints.py':'b'*63};self.save()
        self.assertFalse(self.check()['source_consistent'])
    def test_roster_never_awards_credit(self):
        report=audit(self.root)
        self.assertFalse(report['can_infer_runtime_acceptance'])
        self.assertEqual(len(report['records']),len(EVIDENCE_ROSTER))
    def test_semantic_bindings_explicit(self):
        self.assertEqual(SEMANTIC_KEYS['shared_quota'],'backend/shared_quota.py')
        self.assertEqual(SEMANTIC_KEYS['original'],'audit/baseline/endpoints_original.txt')
if __name__=='__main__':unittest.main()
