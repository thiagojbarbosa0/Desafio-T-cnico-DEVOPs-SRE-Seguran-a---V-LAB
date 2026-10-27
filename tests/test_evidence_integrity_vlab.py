"""Mutation tests: evidence must never count after relevant source/runtime drift."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from scripts.evidence_integrity_vlab import EvidenceError, load_json, safe_relative, verify, main

class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'backend').mkdir()
        (self.root/'backend/endpoints.py').write_text('current source')
        self.rel = 'backend/endpoints.py'
        self.doc = {
            'version':'V19.15', 'validated':True,
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'source_sha256':{self.rel:hashlib.sha256(b'current source').hexdigest()},
            'tests':{'quota_20_21':'pass','deployed_source_freshness':'pass'},
        }

    def check(self, **kwargs):
        return verify(self.root, self.doc, version='V19.15',
                      required_sources=(self.rel,), **kwargs)

    def test_requires_allowlisted_sources(self):
        result=verify(self.root,self.doc,version='V19.15',required_sources=())
        self.assertIn('invalid_expected_sources',result['failures'])
    def test_valid_offline(self): self.assertTrue(self.check()['validated'])
    def test_wrong_version(self):
        self.doc['version']='V19.14'; self.assertIn('wrong_version',self.check()['failures'])
    def test_nonboolean_status(self):
        self.doc['validated']=1; self.assertIn('not_validated',self.check()['failures'])
    def test_source_drift(self):
        (self.root/self.rel).write_text('changed')
        self.assertIn('stale_source:'+self.rel,self.check()['failures'])
    def test_source_missing(self):
        (self.root/self.rel).unlink()
        self.assertIn('source_unavailable:'+self.rel,self.check()['failures'])
    def test_missing_hash(self):
        self.doc['source_sha256']={}
        self.assertFalse(self.check()['validated'])
    def test_bad_hash_syntax(self):
        self.doc['source_sha256'][self.rel]='c'*63
        self.assertFalse(self.check()['validated'])
    def test_required_tests(self):
        self.assertTrue(self.check(required_tests=('quota_20_21',))['validated'])
        self.doc['tests']['quota_20_21']='8/8 pass'
        self.assertFalse(self.check(required_tests=('quota_20_21',))['validated'])
    def test_container_attestation_explicit(self):
        self.assertTrue(self.check(runtime=True)['validated'])
        self.doc['tests'].pop('deployed_source_freshness')
        self.assertIn('no_container_source_attestation',self.check(runtime=True)['failures'])
    def test_timestamp_fresh(self): self.assertTrue(self.check(max_age_hours=2)['validated'])
    def test_timestamp_too_old(self):
        self.doc['generated_utc']=(datetime.now(timezone.utc)-timedelta(hours=4)).isoformat()
        self.assertIn('evidence_outside_time_window',self.check(max_age_hours=2)['failures'])
    def test_future_timestamp(self):
        self.doc['generated_utc']=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
        self.assertFalse(self.check(max_age_hours=3)['validated'])
    def test_naive_timestamp(self):
        self.doc['generated_utc']='2026-10-25T12:00:00'
        self.assertFalse(self.check(max_age_hours=3)['validated'])
    def test_traversal_rejected(self):
        for path in ('../etc/passwd','/etc/passwd','backend/../x','backend\\x','C:/x','./backend/endpoints.py'):
            with self.subTest(path=path),self.assertRaises(EvidenceError): safe_relative(self.root,path)
    def test_symlink_rejected(self):
        (self.root/'backend/link.py').symlink_to('endpoints.py')
        with self.assertRaises(EvidenceError):safe_relative(self.root,'backend/link.py')
    def test_ancestor_symlink_rejected(self):
        (self.root/'src').symlink_to('backend',target_is_directory=True)
        with self.assertRaises(EvidenceError):safe_relative(self.root,'src/endpoints.py')
    def test_duplicate_json_key_rejected(self):
        p=self.root/'duplicate.json';p.write_text('{"validated":true,"validated":false}')
        with self.assertRaises(EvidenceError):load_json(p)
    def test_nan_rejected(self):
        p=self.root/'nan.json';p.write_text('{"count":NaN}')
        with self.assertRaises(EvidenceError):load_json(p)
    def test_oversized_evidence_rejected(self):
        p=self.root/'huge.json';p.write_bytes(b' '*3000001)
        with self.assertRaises(EvidenceError):load_json(p)
    def test_non_object_rejected(self):
        p=self.root/'list.json';p.write_text('[]')
        with self.assertRaises(EvidenceError):load_json(p)
    def test_legacy_gate_missing_file_fails_closed(self):
        from unittest import mock
        from scripts.release_gate_v19_8 import correct_hashes
        from scripts.release_gate_v19_7 import _hash_match
        with mock.patch('pathlib.Path.read_bytes', side_effect=FileNotFoundError):
            self.assertFalse(correct_hashes({'validated':True,'version':'V19.8','source_sha256':{}},['missing.py']))
            self.assertFalse(_hash_match({'validated':True,'source_sha256':{}},['missing.py']))
    def test_cli_no_auto_credit(self):
        p=self.root/'evidence.json';p.write_text(json.dumps(self.doc))
        self.assertEqual(main(['--root',str(self.root),'--evidence','evidence.json',
                               '--version','V19.15','--source',self.rel,'--test','quota_20_21']),0)
        self.assertEqual(main(['--root',str(self.root),'--evidence','evidence.json',
                               '--version','V19.15','--source',self.rel,'--test','quota_20_21',
                               '--require-runtime-attestation']),0)
        self.doc['tests']['deployed_source_freshness']='pending'
        p.write_text(json.dumps(self.doc))
        self.assertEqual(main(['--root',str(self.root),'--evidence','evidence.json',
                               '--version','V19.15','--source',self.rel,
                               '--require-runtime-attestation']),1)

if __name__=='__main__':unittest.main()
