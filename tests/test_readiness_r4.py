"""Dependency readiness: actual behavior, not only source text."""
import threading
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.readiness import DependencyReadiness
from backend.firebase import Firebase

ROOT = Path(__file__).resolve().parents[1]


class ReadinessTests(unittest.TestCase):
    def test_initial_success_and_positive_cache(self):
        service = DependencyReadiness(5)
        calls = []
        def probe():
            calls.append(True)
            return True
        self.assertTrue(service.ready(probe, now=100))
        self.assertTrue(service.ready(lambda: False, now=104.999))
        self.assertEqual(calls, [True])
        self.assertFalse(service.ready(lambda: False, now=105))

    def test_failed_probe_caches_short_term_but_recovers(self):
        service = DependencyReadiness(5)
        def offline(): raise RuntimeError('secret auth diagnostic')
        self.assertFalse(service.ready(offline, now=100))
        self.assertFalse(service.ready(lambda: True, now=101))
        self.assertTrue(service.ready(lambda: True, now=105))

    def test_missing_or_truthy_but_not_boolean_true_denied(self):
        for result in (None, False, 1, 'ok', {'status':'ok'}, [], True):
            state = DependencyReadiness()
            self.assertEqual(state.ready(lambda: result, now=12), result is True)

    def test_clock_rollback_forces_new_probe(self):
        state = DependencyReadiness()
        self.assertTrue(state.ready(lambda: True, now=500))
        self.assertFalse(state.ready(lambda: False, now=499))

    def test_invalid_ttls_and_clocks_fail(self):
        for val in (-1, 0, True, float('nan'), float('inf'), '1'):
            with self.subTest(val=val), self.assertRaises(ValueError): DependencyReadiness(val)
        state = DependencyReadiness()
        for val in (-1, False, float('nan'), float('inf'), 'x'):
            with self.subTest(val=val), self.assertRaises(ValueError): state.ready(lambda: True, now=val)

    def test_parallel_checks_are_coalesced(self):
        service = DependencyReadiness(5)
        lock = threading.Lock()
        calls = []
        def work():
            with lock: calls.append(True)
            return True
        threads = [threading.Thread(target=lambda: self.assertTrue(service.ready(work, now=2))) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(calls), 1)

    def test_auth_and_rtdb_both_probed_without_root_dump(self):
        fake_auth, fake_db = MagicMock(), MagicMock()
        with patch('backend.firebase._firebase',return_value=(fake_auth,fake_db)):
            self.assertIs(Firebase.probe_dependencies(), True)
        fake_auth.list_users.assert_called_once_with(max_results=1)
        fake_db.reference.assert_called_once_with('server_security/readiness')
        fake_db.reference.return_value.get.assert_called_once_with()

    def test_backend_error_is_not_misreported_healthy(self):
        fake_auth, fake_db = MagicMock(), MagicMock()
        fake_db.reference.return_value.get.side_effect=OSError('private origin unavailable')
        with patch('backend.firebase._firebase',return_value=(fake_auth,fake_db)):
            self.assertFalse(DependencyReadiness().ready(Firebase.probe_dependencies, now=0))

    def test_gateway_and_http_routes_separate_liveness(self):
        text = (ROOT/'ops/nginx/gateway.official.conf').read_text()
        self.assertIn('health$|ready$',text)
        source = (ROOT/'backend/endpoints.py').read_text()
        self.assertIn('@app.get("/health")',source)
        self.assertIn('@app.get("/ready")',source)
        self.assertIn('dependency_readiness.ready(Firebase.probe_dependencies)',source)
        self.assertIn('"unavailable", "service": "coursesphere-api"}), 503',source)
        docker = (ROOT/'backend/Dockerfile.official').read_text()
        self.assertIn('127.0.0.1:8091/health',docker)

if __name__=='__main__': unittest.main()
