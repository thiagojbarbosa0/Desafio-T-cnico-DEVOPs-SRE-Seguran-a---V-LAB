"""CORS policy regression; no Flask or Firebase dependencies required."""
import unittest
from backend.cors_policy import parse_allowed_origins, DEFAULT_ORIGIN


class CorsPolicyRegression(unittest.TestCase):
    def test_default_dev_origin(self):
        self.assertEqual(parse_allowed_origins(None), (DEFAULT_ORIGIN,))

    def test_local_react_origins(self):
        self.assertEqual(parse_allowed_origins('http://localhost:5173,http://127.0.0.1:5173'),
                         ('http://localhost:5173', 'http://127.0.0.1:5173'))

    def test_secure_production_origin(self):
        self.assertEqual(parse_allowed_origins('https://courses.example.org'),
                         ('https://courses.example.org',))

    def test_loopback_ipv6(self):
        self.assertEqual(parse_allowed_origins('http://[::1]:5173'), ('http://[::1]:5173',))

    def test_duplicate_removal(self):
        self.assertEqual(parse_allowed_origins('https://courses.example.org, https://courses.example.org'),
                         ('https://courses.example.org',))

    def test_reject_insecure_or_ambiguous_origins(self):
        invalid = [
            '', ' ', ' * ', 'https://*.example.org', 'null',
            'http://courses.example.org', 'http://192.168.1.20:5173',
            'https://example.org/path', 'https://example.org/?debug=1',
            'https://example.org#fragment', 'https://u:p@example.org',
            'ftp://example.org', 'https://example.org:bad',
            'https://example.org:0', 'https://EXAMPLE.org',
            'https://example.org.', 'https://example.org,',
            'https://example.org,,https://other.org',
            'https://example.org/../../foo', 'https://example.org:443',
            'https://example.org\nhttps://bad.org',
            'https://example.org,'*17,
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_allowed_origins(value)


if __name__ == '__main__':
    unittest.main()

class CorsEvidenceBinding(unittest.TestCase):
    def test_http_proof_rejects_old_evidence_without_new_cors_policy_digest(self):
        from scripts.release_gate_v12 import validate_http_evidence, sha256, ROOT
        sources = {
            'original': 'audit/baseline/endpoints_original.txt',
            'corrected': 'backend/endpoints.py',
            'test_harness': 'integration/test_original_http_stubbed.py',
            'security_core': 'backend/security_core.py',
            'shared_quota': 'backend/shared_quota.py',
            'observability': 'backend/observability.py',
        }
        proof = {
            'validated': True, 'tests_run': 15,
            'failures': 0, 'errors': 0, 'skipped': 0,
            'cases': {str(n): {} for n in range(15)},
            'source_sha256': {k: sha256(ROOT / path) for k, path in sources.items()},
        }
        self.assertFalse(validate_http_evidence(proof))
        proof['source_sha256']['cors_policy'] = sha256(ROOT / 'backend/cors_policy.py')
        self.assertTrue(validate_http_evidence(proof))

    def test_wsgi_runner_evidence_rejects_skips(self):
        from integration.run_v19_6_cors_runtime import SOURCES, ROOT
        import json
        result_path = ROOT / 'evidence/generated/FLASK_CORS_RUNTIME_V19_6.json'
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding='utf-8'))
            if result.get('skipped', 0):
                self.assertFalse(result['validated'])
        self.assertIn('backend/cors_policy.py', SOURCES)
