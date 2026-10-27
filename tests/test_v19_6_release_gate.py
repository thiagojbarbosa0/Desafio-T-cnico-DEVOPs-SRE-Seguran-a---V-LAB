"""Regression guard against accepting skipped or stale CORS HTTP evidence."""
import hashlib
import unittest
from integration.run_v19_6_cors_runtime import EXPECTED, ROOT, SOURCES
from scripts.release_gate_v19_6 import valid_cors_runtime


class CorsRuntimeProofGate(unittest.TestCase):
    def sample(self):
        return {
            'validated': True,
            'tests_run': EXPECTED,
            'skipped': 0,
            'errors': 0,
            'failures': 0,
            'source_sha256': {
                path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                for path in SOURCES
            },
        }

    def test_valid_current_evidence(self):
        self.assertTrue(valid_cors_runtime(self.sample()))

    def test_skipped_or_failed_cannot_pass(self):
        for field in ('skipped', 'errors', 'failures'):
            with self.subTest(field=field):
                case = self.sample()
                case[field] = 1
                self.assertFalse(valid_cors_runtime(case))

    def test_source_change_invalidates_proof(self):
        case = self.sample()
        case['source_sha256']['backend/cors_policy.py'] = '0'*64
        self.assertFalse(valid_cors_runtime(case))

    def test_missing_evidence_fails_closed(self):
        self.assertFalse(valid_cors_runtime({}))
        self.assertFalse(valid_cors_runtime(None))

    def test_incomplete_suite_fails(self):
        case = self.sample()
        case['tests_run'] -= 1
        self.assertFalse(valid_cors_runtime(case))
