"""Regression guards for the truthful V12 release evidence gates."""
import unittest
from scripts.release_gate_v12 import (
    EXPECTED_HTTP, EXPECTED_EMULATOR, ROOT, sha256,
    validate_emulator_evidence, validate_http_evidence,
)

class EvidenceGateV12(unittest.TestCase):
    def http_document(self):
        return {
            'validated': True, 'tests_run': EXPECTED_HTTP,
            'skipped': 0, 'failures': 0, 'errors': 0,
            'cases': {f'case_{i}': {'original_http_status': 400, 'corrected_http_status': 401}
                      for i in range(EXPECTED_HTTP)},
            'source_sha256': {
                'original': sha256(ROOT / 'audit/baseline/endpoints_original.txt'),
                'corrected': sha256(ROOT / 'backend/endpoints.py'),
                'test_harness': sha256(ROOT / 'integration/test_original_http_stubbed.py'),
                'security_core': sha256(ROOT / 'backend/security_core.py'),
                'shared_quota': sha256(ROOT / 'backend/shared_quota.py'),
                'cors_policy': sha256(ROOT / 'backend/cors_policy.py'),
                'observability': sha256(ROOT / 'backend/observability.py'),
            },
        }

    def test_missing_evidence_fails_closed(self):
        self.assertFalse(validate_http_evidence({}))
        self.assertFalse(validate_emulator_evidence({}))

    def test_only_current_sources_can_be_accepted(self):
        evidence = self.http_document()
        self.assertTrue(validate_http_evidence(evidence))
        evidence['source_sha256']['corrected'] = '0' * 64
        self.assertFalse(validate_http_evidence(evidence))

    def test_skipped_flask_test_never_counts(self):
        evidence = self.http_document()
        evidence['skipped'] = 1
        self.assertFalse(validate_http_evidence(evidence))

    def test_incomplete_or_failing_flask_suite_never_counts(self):
        evidence = self.http_document()
        evidence['cases'].pop('case_0')
        self.assertFalse(validate_http_evidence(evidence))
        evidence = self.http_document()
        evidence['errors'] = 1
        self.assertFalse(validate_http_evidence(evidence))

    def test_emulator_needs_exact_count_and_demo_project(self):
        doc = {
            'validated': True, 'tests_run': EXPECTED_EMULATOR,
            'skipped': 0, 'errors': 0, 'failures': 0,
            'project': 'demo-coursesphere-vlab',
            'source_sha256': {name: sha256(ROOT / path) for name, path in {
                'endpoints': 'backend/endpoints.py',
                'firebase': 'backend/firebase.py',
                'firebase_configuration': 'backend/firebase_configuration.py',
                'security_core': 'backend/security_core.py',
                'shared_quota': 'backend/shared_quota.py',
                'cors_policy': 'backend/cors_policy.py',
                'rules': 'ops/firebase/database.rules.json',
                'emulator_harness': 'integration/test_official_emulators.py',
                'emulator_runner': 'integration/run_official_emulator_tests.py',
            }.items()},
            'cases': {str(i): 200 for i in range(EXPECTED_EMULATOR)},
        }
        self.assertTrue(validate_emulator_evidence(doc))
        doc['project'] = 'real-project'
        self.assertFalse(validate_emulator_evidence(doc))
        doc['project'] = 'demo-coursesphere-vlab'
        doc['source_sha256']['firebase'] = 'f' * 64
        self.assertFalse(validate_emulator_evidence(doc))
        doc['source_sha256']['firebase'] = sha256(ROOT / 'backend/firebase.py')
        doc['skipped'] = 1
        self.assertFalse(validate_emulator_evidence(doc))

    def test_15_real_http_test_cases_in_source(self):
        from integration.test_original_http_stubbed import OriginalHTTPBeforeAfter
        methods = [name for name in dir(OriginalHTTPBeforeAfter) if name.startswith('test_')]
        self.assertEqual(len(methods), EXPECTED_HTTP)
        self.assertEqual(len(set(methods)), EXPECTED_HTTP)

if __name__ == '__main__':
    unittest.main()
