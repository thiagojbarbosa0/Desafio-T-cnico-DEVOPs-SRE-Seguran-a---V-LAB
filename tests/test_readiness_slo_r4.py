"""SLO scopes: synthetic probe traffic must not falsify user availability."""
import json
import unittest
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

class ReadinessSLOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=(ROOT/'ops/prometheus/alerts.official.yml').read_text()
        segments=re.split(r'(?=^      - alert: )',raw,flags=re.M)
        cls.alerts={}
        for chunk in segments:
            match=re.search(r'^      - alert: ([A-Za-z0-9]+)',chunk,re.M)
            if match:
                name=match.group(1)
                if name in cls.alerts: raise AssertionError('duplicate alert rule name')
                cls.alerts[name]={'expr':chunk}
        cls.dashboard=json.loads((ROOT/'ops/grafana/dashboards-original/coursesphere-original.json').read_text())

    def test_all_five_alerts_unique(self):
        alerts=list(self.alerts)
        self.assertEqual(set(alerts),{
            'OriginalAPIReplicaUnavailable', 'OriginalAPIAvailabilitySLO',
            'OriginalAPILatencySLO','OriginalAPIDependencyReadinessDegraded',
            'OriginalAPIReadinessTelemetryMissing'})

    def test_user_availability_excludes_health_and_ready(self):
        expr=self.alerts['OriginalAPIAvailabilitySLO']['expr']
        self.assertEqual(expr.count('route!~"/health|/ready"'),2)
        self.assertIn('status_class="5xx"',expr)

    def test_user_latency_excludes_both_probe_endpoints(self):
        expr=self.alerts['OriginalAPILatencySLO']['expr']
        self.assertIn('route!~"/health|/ready"',expr)
        self.assertIn('histogram_quantile(0.95',expr)

    def test_dependency_readiness_alert_scoped(self):
        expr=self.alerts['OriginalAPIDependencyReadinessDegraded']['expr']
        self.assertIn('coursesphere_original_firebase_ready',expr)
        self.assertIn('== 0',expr)
        self.assertNotIn('server_security/',expr)

    def test_missing_readiness_gauge_alert_ignores_down_replicas(self):
        expr=self.alerts['OriginalAPIReadinessTelemetryMissing']['expr']
        self.assertIn('up{job="coursesphere-original"} == 1',expr)
        self.assertIn('unless on(job, instance) coursesphere_original_firebase_ready',expr)

    def test_dashboard_matches_availability_and_latency_scope(self):
        panels={p['title']:p for p in self.dashboard['panels']}
        for title in ('5xx error fraction (5m)','p95 request latency (seconds)'):
            self.assertIn('route!~"/health|/ready"',panels[title]['targets'][0]['expr'])

    def test_dashboard_readiness_panel(self):
        panels={p['title']:p for p in self.dashboard['panels']}
        self.assertIn('Firebase Auth + RTDB readiness per replica',panels)
        self.assertIn('coursesphere_original_firebase_ready',panels['Firebase Auth + RTDB readiness per replica']['targets'][0]['expr'])

    def test_original_prometheus_runtime_gate_checks_readiness_alert(self):
        verifier=(ROOT/'scripts/verify_official_observability_v19_8.py').read_text()
        self.assertIn("'OriginalAPIDependencyReadinessDegraded',",verifier)
        self.assertIn("'OriginalAPIReadinessTelemetryMissing'}<=names",verifier)

if __name__=='__main__':unittest.main()
