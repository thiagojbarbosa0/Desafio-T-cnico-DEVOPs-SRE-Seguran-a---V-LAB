"""R5: exercise the ACTUAL private Flask metrics handler without Flask installed.

Extract only the undecorated function body from the original source. The real
Flask network, Firebase Admin and Prometheus integrations are separate gates.
"""
from __future__ import annotations
import ast
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import threading
import unittest
from unittest.mock import Mock

from backend.readiness import DependencyReadiness
from backend.observability import HTTPMetrics

ROOT = Path(__file__).resolve().parents[1]


def load_real_handler(*, authorized=True, probe=None, ttl=5):
    tree = ast.parse((ROOT/'backend/endpoints.py').read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'prometheus_metrics')
    function.decorator_list = []
    compiled = compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                       str(ROOT/'backend/endpoints.py'), 'exec')
    metrics = HTTPMetrics()
    fake_auth = type('Auth', (), {'probe_dependencies': staticmethod(probe or (lambda: True))})
    request = type('Request', (), {'remote_addr': '10.0.0.7', 'headers': {'Authorization': 'Bearer synthetic'}})()
    environment = {'metrics_authorized': lambda *a: authorized,
                   'request': request, 'error_response': lambda message, status: ({'error': message}, status),
                   'metrics': metrics, 'dependency_readiness': DependencyReadiness(ttl),
                   'Firebase': fake_auth, 'Response': lambda body, content_type: (body, content_type)}
    exec(compiled, environment)
    return environment['prometheus_metrics'], metrics


class ReadinessScrapeR5(unittest.TestCase):
    def test_authorized_scrape_exposes_one_for_both_dependencies(self):
        handler, metrics = load_real_handler(probe=lambda: True)
        body, ctype = handler()
        self.assertIn('text/plain; version=0.0.4', ctype)
        self.assertIn('coursesphere_original_firebase_ready 1\n', body)
        self.assertIn('# TYPE coursesphere_original_firebase_ready gauge\n', body)

    def test_unavailable_auth_or_rtdb_exposes_zero_without_leaking_errors(self):
        def bad_probe():
            raise RuntimeError('SYNTHETIC_SECRET_MARKER_NO_REAL_TOKEN')
        handler, _ = load_real_handler(probe=bad_probe)
        body, _ = handler()
        self.assertIn('coursesphere_original_firebase_ready 0\n', body)
        self.assertNotIn('SYNTHETIC_SECRET_MARKER', body)
        self.assertNotIn('uid=', body)
        self.assertNotIn('server_security/', body)

    def test_unauthorized_scrape_does_not_call_firebase(self):
        called = Mock(return_value=True)
        handler, metrics = load_real_handler(authorized=False, probe=called)
        self.assertEqual(handler(), ({'error': 'Not found'},404))
        called.assert_not_called()
        self.assertNotIn('coursesphere_original_firebase_ready 1',metrics.render())

    def test_private_scrapes_use_cache_and_update_after_expiry(self):
        observations = iter((False, True))
        called = Mock(side_effect=lambda: next(observations))
        handler, _ = load_real_handler(probe=called, ttl=5)
        import backend.readiness as module
        with unittest.mock.patch.object(module.time, 'monotonic', side_effect=(100,101,106)):
            self.assertIn('coursesphere_original_firebase_ready 0',handler()[0])
            self.assertIn('coursesphere_original_firebase_ready 0',handler()[0])
            self.assertIn('coursesphere_original_firebase_ready 1',handler()[0])
        self.assertEqual(called.call_count,2)

    def test_real_metric_rejects_nonboolean_probe_statuses(self):
        for status in ({'ok':True}, 1, 'healthy', None, False):
            with self.subTest(status=status):
                handler, _ = load_real_handler(probe=lambda:status)
                self.assertIn('coursesphere_original_firebase_ready 0',handler()[0])

    def test_metrics_gauge_is_low_cardinality_and_rejects_nonbool_setter(self):
        m=HTTPMetrics()
        for x in (None,0,1,'True',[],{}):
            with self.subTest(x=x),self.assertRaises(ValueError):m.set_firebase_readiness(x)
        self.assertNotIn('coursesphere_original_firebase_ready 0',m.render())
        m.set_firebase_readiness(False)
        m.set_firebase_readiness(True)
        line=[x for x in m.render().splitlines() if x.startswith('coursesphere_original_firebase_ready ')]
        self.assertEqual(line,['coursesphere_original_firebase_ready 1'])

    def test_parallel_scrapes_share_one_readiness_probe(self):
        counter=[]
        lock=threading.Lock()
        def probe():
            with lock:counter.append(1)
            return True
        handler, _ = load_real_handler(probe=probe)
        with ThreadPoolExecutor(max_workers=12) as pool:
            results=list(pool.map(lambda _ :handler()[0],range(50)))
        self.assertEqual(len(counter),1)
        self.assertTrue(all('coursesphere_original_firebase_ready 1' in body for body in results))

    def test_alert_and_dashboard_consume_exact_scrape_gauge(self):
        alert=(ROOT/'ops/prometheus/alerts.official.yml').read_text()
        section=alert.split('- alert: OriginalAPIDependencyReadinessDegraded',1)[1]
        self.assertIn('coursesphere_original_firebase_ready{job="coursesphere-original"} == 0', section)
        self.assertNotIn('rate(coursesphere_original_http_requests_total{route="/ready"', section)
        dashboard=json.loads((ROOT/'ops/grafana/dashboards-original/coursesphere-original.json').read_text())
        panel=next(p for p in dashboard['panels'] if 'readiness per replica' in p['title'])
        self.assertEqual(panel['targets'][0]['expr'],'coursesphere_original_firebase_ready{job="coursesphere-original"}')
        self.assertEqual(panel['fieldConfig']['defaults']['max'],1)

    def test_missing_gauge_triggers_stale_replica_alert(self):
        alert=(ROOT/'ops/prometheus/alerts.official.yml').read_text()
        section=alert.split('- alert: OriginalAPIReadinessTelemetryMissing',1)[1]
        self.assertIn('up{job="coursesphere-original"} == 1',section)
        self.assertIn('unless on(job, instance) coursesphere_original_firebase_ready',section)
        self.assertNotIn('uid',section)

    def test_runtime_gate_requires_each_replica_not_aggregate(self):
        verifier=(ROOT/'scripts/verify_official_observability_v19_8.py').read_text()
        self.assertIn('set(samples)==EXPECTED',verifier)
        self.assertIn('both_replica_readiness_metrics_observed',verifier)
        self.assertNotIn('query(\'sum(coursesphere_original_firebase_ready',verifier)

    def test_prometheus_scrapes_directly_per_replica_using_private_token(self):
        settings=(ROOT/'ops/prometheus/prometheus.official.yml').read_text()
        self.assertIn('metrics_path: /metrics',settings)
        self.assertIn('credentials_file: /run/secrets/official_metrics_token',settings)
        self.assertIn('official_api_a:8091',settings)
        self.assertIn('official_api_b:8091',settings)
        gateway=(ROOT/'ops/nginx/gateway.official.conf').read_text()
        self.assertIn('location = /metrics { return 403; }',gateway)

    def test_prometheus_metric_serializer_no_new_token_label(self):
        handler,m=load_real_handler(probe=lambda:True)
        body,_=handler()
        self.assertEqual(len(re.findall(r'^coursesphere_original_firebase_ready [01]$',body,re.M)),1)
        self.assertNotIn('Authorization',body)
        self.assertNotIn('synthetic',body)


if __name__=='__main__':unittest.main()
