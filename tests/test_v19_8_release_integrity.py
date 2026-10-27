"""Source-bound gates must reject incomplete or stale evidence.

Reports in these tests are SYNTHETIC IN-MEMORY OBJECTS, never acceptance proof.
"""
from __future__ import annotations
import hashlib
import unittest
from scripts import release_gate_v19_8 as gate
from integration.run_v19_8_metrics_runtime import SOURCES as WSGI_FILES,EXPECTED
from scripts.verify_official_observability_v19_8 import FILES as DOCKER_FILES


def hash_report(files):
    return {path:hashlib.sha256((gate.ROOT/path).read_bytes()).hexdigest() for path in files}


class ReleaseV198Gates(unittest.TestCase):
    def test_missing_evidence_is_never_valid(self):
        self.assertFalse(gate.metrics_wsgi_valid(None))
        self.assertFalse(gate.observability_valid(None))

    def test_skipped_wsgi_is_not_success(self):
        report={'version':'V19.8','validated':True,'tests_run':EXPECTED,'skipped':1,'errors':0,'failures':0,
                'scope':'Real Flask WSGI with synthetic Firebase',
                'source_sha256':hash_report(WSGI_FILES)}
        self.assertFalse(gate.metrics_wsgi_valid(report))

    def test_missing_docker_failover_and_recovery_is_not_success(self):
        report={'version':'V19.8','validated':True,'scope':'Original Flask metrics test synthetic object',
                'source_sha256':hash_report(DOCKER_FILES),'tests':{
                    'compose_config':'pass','grafana_healthy':'pass',
                    'original_dashboard_provisioned':'pass','two_slo_alerts_and_replica_alert_loaded':'pass',
                    'two_authenticated_scrapes':'pass','original_http_metrics_both_replicas':'pass',
                    'edge_metrics_denied':'pass'}}
        self.assertFalse(gate.observability_valid(report))

    def test_stale_docker_hash_rejected_even_with_all_flags(self):
        tests={key:'pass' for key in ('compose_config','grafana_healthy','original_dashboard_provisioned',
                   'two_slo_alerts_and_replica_alert_loaded','two_authenticated_scrapes',
                   'both_replica_readiness_metrics_observed',
                   'original_http_metrics_both_replicas','edge_metrics_denied',
                   'prometheus_detected_replica_failure','replica_restored')}
        tests['gateway_still_available']='8/8 pass'
        tests['firebase_readiness_status']={'official_api_a:8091':'ready','official_api_b:8091':'degraded'}
        report={'version':'V19.8','validated':True,'scope':'Original Flask metrics actual integration',
                'source_sha256':hash_report(DOCKER_FILES),'tests':tests,
                'application_ready_for_authenticated_traffic':False}
        self.assertTrue(gate.observability_valid(report))
        report['source_sha256']['backend/endpoints.py']='deadbeef'
        self.assertFalse(gate.observability_valid(report))


if __name__=='__main__':unittest.main()
