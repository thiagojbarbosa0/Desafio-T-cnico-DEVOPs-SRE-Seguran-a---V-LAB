"""Pure-Python security regression for original Flask -> private monitoring.

These tests prove authorization decisions and configuration contracts, NOT the
Docker stack. Runtime HTTP, Prometheus scraping and Grafana remain separate.
"""
from __future__ import annotations
import json
from pathlib import Path
import os
import stat
import tempfile
import unittest
from unittest import mock

from backend.metrics_access import metrics_authorized
from scripts.official_observability_preflight_v19_8 import check

ROOT=Path(__file__).resolve().parents[1]
TOKEN='SYNTHETIC_PRIVATE_TEST_TOKEN_0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ'


class PrivateMetricsAccess(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'token'
        self.path.write_text(TOKEN+'\n')
        self.env={'COURSESPHERE_METRICS_ENABLED':'1', 'COURSESPHERE_METRICS_TOKEN_FILE':str(self.path)}

    def test_disabled_is_denied_even_with_loopback(self):
        for address in ('127.0.0.1','::1','172.20.0.4'):
            self.assertFalse(metrics_authorized(address,'Bearer '+TOKEN,env={}))

    def test_loopback_diagnostics_when_opted_in(self):
        for address in ('127.0.0.1','::1'):
            self.assertTrue(metrics_authorized(address,None,env=self.env))

    def test_remote_denied_without_header(self):
        self.assertFalse(metrics_authorized('172.20.0.4',None,env=self.env))

    def test_correct_secret_allows_remote_scrape(self):
        self.assertTrue(metrics_authorized('172.20.0.4','Bearer '+TOKEN,env=self.env))

    def test_wrong_and_partial_token_rejected(self):
        for header in ('Bearer '+'x'*70,'Bearer '+TOKEN[:-1],TOKEN, 'Basic '+TOKEN, 'Bearer '+TOKEN+' ', 'Bearer '+TOKEN+'\n'):
            with self.subTest(header=header[:9]):
                self.assertFalse(metrics_authorized('172.20.0.4',header,env=self.env))

    def test_secret_missing_fails_closed(self):
        self.path.unlink()
        self.assertFalse(metrics_authorized('172.20.0.4','Bearer '+TOKEN,env=self.env))

    def test_secret_too_short_fails_closed(self):
        self.path.write_text('guessme')
        self.assertFalse(metrics_authorized('172.20.0.4','Bearer '+TOKEN,env=self.env))

    def test_file_unreadable_or_invalid_fails_closed(self):
        self.path.write_bytes(b'\xff\xfe')
        self.assertFalse(metrics_authorized('172.20.0.4','Bearer '+TOKEN,env=self.env))
        self.path.write_bytes(b'x'*5000)
        self.assertFalse(metrics_authorized('172.20.0.4','Bearer '+TOKEN,env=self.env))

    def test_forged_forwarded_for_cannot_override_remote(self):
        # The access function deliberately accepts no forwarding headers.
        self.assertFalse(metrics_authorized('192.0.2.55',None,env=self.env))

    def test_bad_ip_does_not_enable_loopback(self):
        self.assertFalse(metrics_authorized('127.0.0.1, 192.0.2.1',None,env=self.env))

    def test_secret_must_be_explicit_file_not_env_value(self):
        env={'COURSESPHERE_METRICS_ENABLED':'1','COURSESPHERE_METRICS_TOKEN':TOKEN}
        self.assertFalse(metrics_authorized('172.20.0.4','Bearer '+TOKEN,env=env))


class OriginalObservabilityContracts(unittest.TestCase):
    def read(self,rel): return (ROOT/rel).read_text()

    def test_overlay_uses_original_replicas_and_no_public_metrics_port(self):
        compose=self.read('compose.official.observability.yaml')
        self.assertIn('official_api_a:',compose)
        self.assertIn('official_api_b:',compose)
        self.assertIn('COURSESPHERE_METRICS_TOKEN_FILE:',compose)
        self.assertIn('secrets: [official_metrics_token]',compose)
        self.assertIn('127.0.0.1:9092:9090',compose)
        self.assertIn('127.0.0.1:3001:3000',compose)
        self.assertNotIn('0.0.0.0:9090',compose)

    def test_prometheus_uses_bearer_file_and_scrapes_individually(self):
        conf=self.read('ops/prometheus/prometheus.official.yml')
        self.assertIn('coursesphere-original',conf)
        self.assertIn('credentials_file: /run/secrets/official_metrics_token',conf)
        self.assertIn('official_api_a:8091',conf)
        self.assertIn('official_api_b:8091',conf)
        self.assertNotIn('official_gateway:8081',conf)

    def test_original_metrics_not_the_synthetic_metrics(self):
        dash=json.loads(self.read('ops/grafana/dashboards-original/coursesphere-original.json'))
        all_expr=' '.join(p['targets'][0]['expr'] for p in dash['panels'])
        self.assertIn('coursesphere_original_http_requests_total',all_expr)
        self.assertIn('coursesphere_original_http_duration_seconds_bucket',all_expr)
        self.assertIn('coursesphere_original_auth_attempts_total',all_expr)
        self.assertNotIn('coursesphere_http_requests_total{',all_expr)

    def test_alerts_include_two_distinct_slos(self):
        alert=self.read('ops/prometheus/alerts.official.yml')
        self.assertIn('OriginalAPIAvailabilitySLO',alert)
        self.assertIn('OriginalAPILatencySLO',alert)
        self.assertIn('> 0.01',alert)
        self.assertIn('> 0.5',alert)
        self.assertIn('up{job="coursesphere-original"}',alert)

    def test_grafana_not_provisioned_for_synthetic_service(self):
        prov=self.read('ops/grafana/provisioning-official/datasources/datasources.yml')
        self.assertIn('http://official_prometheus:9090',prov)
        self.assertNotIn('http://prometheus:9090',prov)

    def test_gateway_still_denies_public_metrics(self):
        self.assertIn('location = /metrics { return 403; }',self.read('ops/nginx/gateway.official.conf'))

    def test_docker_context_excludes_generated_secrets(self):
        ignore=self.read('.dockerignore')
        self.assertIn('.local',ignore)
        self.assertIn('.env.*',ignore)

    def test_preflight_rejects_absent_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors=check(Path(tmp))
            self.assertEqual(len(errors),2)

    def test_preflight_accepts_private_random_like_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'.local').mkdir()
            token=root/'.local/official_metrics_token'
            token.write_text(TOKEN+'\n');token.chmod(0o600)
            env=root/'.env.official.observability'
            env.write_text('OFFICIAL_GRAFANA_ADMIN_PASSWORD='+TOKEN+'\n');env.chmod(0o600)
            self.assertEqual(check(root),[])

    def test_preflight_rejects_world_readable_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.local').mkdir()
            token=root/'.local/official_metrics_token'
            token.write_text(TOKEN);token.chmod(0o644)
            env=root/'.env.official.observability'
            env.write_text('OFFICIAL_GRAFANA_ADMIN_PASSWORD='+TOKEN+'\n');env.chmod(0o600)
            self.assertTrue(any('permissions' in e for e in check(root)))

    def test_preflight_rejects_symlink_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.local').mkdir()
            other=root/'safe-source'
            other.write_text(TOKEN)
            (root/'.local/official_metrics_token').symlink_to(other)
            env=root/'.env.official.observability'
            env.write_text('OFFICIAL_GRAFANA_ADMIN_PASSWORD='+TOKEN+'\n');env.chmod(0o600)
            self.assertTrue(any('symbolic link' in e for e in check(root)))

    def test_monitoring_runtime_requires_real_dashboard_and_alerts(self):
        code=self.read('scripts/verify_official_observability_v19_8.py')
        self.assertIn('dashboard_is_provisioned',code)
        self.assertIn('alerts_are_loaded',code)
        self.assertIn('original_dashboard_provisioned',code)
        self.assertIn('two_slo_alerts_and_replica_alert_loaded',code)
        self.assertIn("'validated':False",code)

    def test_ci_has_original_observability_runtime_job(self):
        workflow=self.read('.github/workflows/ci.yml')
        self.assertIn('original-docker-observability-v19-8:',workflow)
        self.assertIn('verify_official_observability_v19_8.py --failover',workflow)
        self.assertIn('integration.run_v19_8_metrics_runtime',workflow)
        self.assertIn('if: always()',workflow)

    def test_preflight_rejects_invalid_dashboard_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.local').mkdir()
            token=root/'.local/official_metrics_token'
            token.write_text(TOKEN);token.chmod(0o600)
            env=root/'.env.official.observability'
            env.write_text('OFFICIAL_GRAFANA_ADMIN_PASSWORD=weak\n');env.chmod(0o600)
            self.assertTrue(any('dashboard' in e.lower() or 'Grafana' in e for e in check(root)))


if __name__=='__main__': unittest.main()
