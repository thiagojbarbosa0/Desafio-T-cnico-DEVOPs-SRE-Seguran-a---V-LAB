"""V16: evidence must expire when any operational dependency changes."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import source_fingerprint
from scripts.doctor_v16 import LABELS, COMMANDS, render_html
from scripts.release_gate_v12 import validate_http_evidence, sha256, ROOT


class SourceProofV16(unittest.TestCase):
    def test_content_mutation_invalidates_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'src').mkdir()
            file = root / 'src/code.py'
            file.write_text('safe = True\n')
            with patch.object(source_fingerprint, 'ROOT', root):
                a = source_fingerprint.fingerprint(['src/code.py'])
                file.write_text('safe = False\n')
                b = source_fingerprint.fingerprint(['src/code.py'])
            self.assertNotEqual(a, b)

    def test_runtime_fingerprint_covers_real_dependencies(self):
        project = source_fingerprint.ROOT
        for target in ('backend/demo_store.py', 'backend/security_core.py',
                       'ops/prometheus/alerts.yml', 'ops/nginx/gateway.conf',
                       'ops/grafana/dashboards/coursesphere.json'):
            self.assertTrue((project / target).is_file())
        files = set(source_fingerprint.files_below('ops'))
        self.assertIn('ops/prometheus/alerts.yml', files)

    def test_flask_http_rejects_missing_helper_hashes(self):
        payload = {
            'validated': True, 'tests_run': 15,
            'failures': 0, 'errors': 0, 'skipped': 0,
            'cases': {str(i): 200 for i in range(15)},
            'source_sha256': {
                'original': sha256(ROOT / 'audit/baseline/endpoints_original.txt'),
                'corrected': sha256(ROOT / 'backend/endpoints.py'),
                'test_harness': sha256(ROOT / 'integration/test_original_http_stubbed.py'),
            }
        }
        self.assertFalse(validate_http_evidence(payload))
        payload['source_sha256']['security_core'] = sha256(ROOT / 'backend/security_core.py')
        payload['source_sha256']['observability'] = sha256(ROOT / 'backend/observability.py')
        self.assertFalse(validate_http_evidence(payload))
        payload['source_sha256']['shared_quota'] = sha256(ROOT / 'backend/shared_quota.py')
        self.assertFalse(validate_http_evidence(payload))
        payload['source_sha256']['cors_policy'] = sha256(ROOT / 'backend/cors_policy.py')
        self.assertTrue(validate_http_evidence(payload))
        payload['source_sha256']['security_core'] = 'bad'
        self.assertFalse(validate_http_evidence(payload))

    def test_status_dashboard_never_hides_incomplete_gates(self):
        sample = {'implementation_estimate_percent': 64,
                  'verified_acceptance_percent': 15,
                  'warnings': ['No live Firebase verified'],
                  'gates': [{'id': 'x', 'name': 'Check', 'weight': 85,
                             'verified': False, 'next_step': 'run tests',
                             'note': 'Not executed'}]}
        page = render_html(sample)
        self.assertIn('Pendente', page)
        self.assertIn('15%', page)
        self.assertIn('No live Firebase verified', page)
        self.assertNotIn('Comprovado</span>', page)

    def test_status_escapes_untrusted_strings(self):
        sample = {'implementation_estimate_percent': 64,
                  'verified_acceptance_percent': 0,
                  'warnings': ['<script>alert(1)</script>'],
                  'gates': []}
        page = render_html(sample)
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_every_gate_is_explained_and_actionable(self):
        self.assertEqual(set(LABELS), set(COMMANDS))
        self.assertEqual(len(LABELS), 8)
        self.assertTrue(all(COMMANDS.values()))

    def test_source_fingerprint_includes_pinned_frontend_inputs(self):
        self.assertEqual(len(source_fingerprint.frontend_fingerprint()), 64)
        self.assertEqual(len(source_fingerprint.docker_fingerprint()), 64)
        self.assertEqual(len(source_fingerprint.nginx_fingerprint()), 64)

    def test_missing_fingerprint_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(source_fingerprint, 'ROOT', Path(folder)):
                with self.assertRaises(FileNotFoundError):
                    source_fingerprint.fingerprint(['missing.txt'])


if __name__ == '__main__':
    unittest.main()
