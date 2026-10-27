"""Evidence is invalid if any test skipped or source changes after execution."""
import hashlib
import unittest
from pathlib import Path
from unittest import mock
from scripts.release_gate_v19_4 import ROOT, SOURCES, valid_wsgi


class EvidenceGateV194(unittest.TestCase):
    def record(self):
        return {'validated':True, 'tests_run':7, 'skipped':0,
                'failures':0, 'errors':0,
                'source_sha256':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                                 for path in SOURCES}}

    def test_complete_current_evidence_is_accepted(self):
        self.assertTrue(valid_wsgi(self.record()))

    def test_skips_do_not_count_as_passes(self):
        record=self.record();record['skipped']=7
        self.assertFalse(valid_wsgi(record))

    def test_synthetic_forged_count_rejected(self):
        record=self.record();record['tests_run']=6
        self.assertFalse(valid_wsgi(record))

    def test_changed_source_invalidates_evidence(self):
        record=self.record();record['source_sha256']['backend/endpoints.py']='0'*64
        self.assertFalse(valid_wsgi(record))

    def test_missing_source_hash_rejected(self):
        record=self.record();record['source_sha256'].pop('backend/shared_quota.py')
        self.assertFalse(valid_wsgi(record))


if __name__=='__main__':unittest.main()
