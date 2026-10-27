"""Real Flask loopback HTTP readiness proof; Firebase is a controlled fake.

Run only where Flask and Flask-Cors are installed (e.g., CI). Never connects to
actual or demo Firebase and never uses third-party account credentials.
"""
import unittest
from unittest import mock
from urllib import request, error
import json

from backend.readiness import DependencyReadiness
from integration.test_original_http_stubbed import (
    HAS_FLASK, SOURCES, SyntheticFirebase, load_app, local_http, http_call,
)


@unittest.skipUnless(HAS_FLASK, 'Flask absent; HTTP integration is not proven')
class ReadinessHTTPR4(unittest.TestCase):
    def setUp(self):
        self.app = load_app(SOURCES['after'], 'coursesphere_ready_http_r4')
        self.app.config['TESTING'] = True
        # Reset the isolated app's readiness cache for independent test cases.
        self.app.view_functions['ready'].__globals__['dependency_readiness'] = DependencyReadiness(5)

    def test_auth_and_rtdb_ready_returns_200(self):
        with mock.patch.object(SyntheticFirebase, 'probe_dependencies', return_value=True, create=True):
            with local_http(self.app) as host:
                status, payload, headers = http_call(host, '/ready')
        self.assertEqual(status, 200)
        self.assertEqual(payload, {'status':'ready','service':'coursesphere-api'})
        self.assertEqual(headers.get('Cache-Control'), 'no-store')

    def test_database_outage_returns_generic_503(self):
        with mock.patch.object(SyntheticFirebase, 'probe_dependencies',
                               side_effect=RuntimeError('SECRET_ENDPOINT_MARKER'),create=True):
            with local_http(self.app) as host:
                status, payload, headers = http_call(host, '/ready')
        self.assertEqual(status, 503)
        self.assertEqual(payload, {'status':'unavailable','service':'coursesphere-api'})
        self.assertNotIn('SECRET_ENDPOINT_MARKER', json.dumps(payload))
        self.assertEqual(headers.get('Cache-Control'), 'no-store')

    def test_liveness_remains_available_when_dependency_is_down(self):
        with mock.patch.object(SyntheticFirebase, 'probe_dependencies',
                               side_effect=RuntimeError('down'),create=True):
            with local_http(self.app) as host:
                readiness, _, _ = http_call(host, '/ready')
                liveness, payload, _ = http_call(host, '/health')
        self.assertEqual(readiness, 503)
        self.assertEqual(liveness, 200)
        self.assertEqual(payload['status'], 'ok')

    def test_readiness_cache_reduces_probes(self):
        with mock.patch.object(SyntheticFirebase, 'probe_dependencies', return_value=True,create=True) as probe:
            with local_http(self.app) as host:
                self.assertEqual(http_call(host,'/ready')[0],200)
                self.assertEqual(http_call(host,'/ready')[0],200)
        probe.assert_called_once()

    def test_authorized_metrics_scrape_actively_probes_firebase(self):
        import os
        with mock.patch.dict(os.environ, {'COURSESPHERE_METRICS_ENABLED':'1'}):
            with mock.patch.object(SyntheticFirebase,'probe_dependencies',return_value=True,create=True) as probe:
                with local_http(self.app) as host:
                    with request.urlopen(host+'/metrics', timeout=5) as resp:
                        self.assertEqual(resp.status,200)
                        body=resp.read().decode('utf-8')
        self.assertIn('coursesphere_original_firebase_ready 1',body)
        probe.assert_called_once()

    def test_metrics_scrape_firebase_outage_gauge_zero_but_http_200(self):
        import os
        with mock.patch.dict(os.environ, {'COURSESPHERE_METRICS_ENABLED':'1'}):
            with mock.patch.object(SyntheticFirebase, 'probe_dependencies',
                                   side_effect=RuntimeError('SYNTHETIC_SECRET_NEVER_LEAK'),create=True):
                with local_http(self.app) as host:
                    with request.urlopen(host+'/metrics',timeout=5) as resp:
                        self.assertEqual(resp.status,200)
                        body=resp.read().decode('utf-8')
        self.assertIn('coursesphere_original_firebase_ready 0',body)
        self.assertNotIn('SYNTHETIC_SECRET_NEVER_LEAK',body)

    def test_disabled_metrics_does_not_trigger_firebase_probe(self):
        import os
        with mock.patch.dict(os.environ, {'COURSESPHERE_METRICS_ENABLED':'0'}):
            with mock.patch.object(SyntheticFirebase,'probe_dependencies',return_value=True,create=True) as probe:
                with local_http(self.app) as host:
                    status,payload,_=http_call(host,'/metrics')
        self.assertEqual(status,404)
        probe.assert_not_called()

    def test_http_ready_and_metrics_share_a_cache(self):
        import os
        with mock.patch.dict(os.environ, {'COURSESPHERE_METRICS_ENABLED':'1'}):
            with mock.patch.object(SyntheticFirebase,'probe_dependencies',return_value=True,create=True) as probe:
                with local_http(self.app) as host:
                    self.assertEqual(http_call(host,'/ready')[0],200)
                    with request.urlopen(host+'/metrics',timeout=5) as resp:
                        self.assertIn(b'coursesphere_original_firebase_ready 1',resp.read())
        probe.assert_called_once()

    def test_query_token_never_reaches_dependency(self):
        with mock.patch.object(SyntheticFirebase, 'probe_dependencies', return_value=True,create=True) as probe:
            with local_http(self.app) as host:
                status, payload, _=http_call(host,'/ready?id_token=SYNTHETIC_ONLY')
        self.assertEqual(status,401)
        probe.assert_not_called()
        self.assertNotIn('SYNTHETIC_ONLY',json.dumps(payload))
