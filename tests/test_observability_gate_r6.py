"""R6 source-binding and anti-contradiction regression tests (synthetic inputs)."""
import unittest
import hashlib
from scripts import release_gate_v19_8 as gate
from scripts.verify_official_observability_v19_8 import FILES


class ObservabilityGateR6(unittest.TestCase):
    def report(self, statuses):
        flags={key:'pass' for key in ('compose_config','grafana_healthy',
          'original_dashboard_provisioned','two_slo_alerts_and_replica_alert_loaded',
          'two_authenticated_scrapes','both_replica_readiness_metrics_observed',
          'original_http_metrics_both_replicas','edge_metrics_denied',
          'prometheus_detected_replica_failure','replica_restored')}
        flags['gateway_still_available']='8/8 pass'
        flags['firebase_readiness_status']=statuses
        return {'version':'V19.8','validated':True,
                'scope':'Original Flask metrics integration; synthetic regression only',
                'source_sha256':{f:hashlib.sha256((gate.ROOT/f).read_bytes()).hexdigest() for f in FILES},
                'application_ready_for_authenticated_traffic':all(x=='ready' for x in statuses.values()),
                'tests':flags}

    def test_report_with_two_ready_is_internally_consistent(self):
        r=self.report({'official_api_a:8091':'ready','official_api_b:8091':'ready'})
        self.assertTrue(gate.observability_valid(r))

    def test_report_with_degradation_consistent_but_not_auth_ready(self):
        r=self.report({'official_api_a:8091':'ready','official_api_b:8091':'degraded'})
        self.assertTrue(gate.observability_valid(r))
        self.assertFalse(r['application_ready_for_authenticated_traffic'])

    def test_forged_application_ready_is_rejected(self):
        r=self.report({'official_api_a:8091':'ready','official_api_b:8091':'degraded'})
        r['application_ready_for_authenticated_traffic']=True
        self.assertFalse(gate.observability_valid(r))

    def test_forged_unready_on_both_ready_is_rejected(self):
        r=self.report({'official_api_a:8091':'ready','official_api_b:8091':'ready'})
        r['application_ready_for_authenticated_traffic']=False
        self.assertFalse(gate.observability_valid(r))

    def test_emulator_gate_requires_configuration_and_runner_source_hashes(self):
        from scripts.release_gate_v12 import validate_emulator_evidence
        required={
            'endpoints':'backend/endpoints.py',
            'firebase':'backend/firebase.py',
            'firebase_configuration':'backend/firebase_configuration.py',
            'security_core':'backend/security_core.py',
            'shared_quota':'backend/shared_quota.py',
            'cors_policy':'backend/cors_policy.py',
            'rules':'ops/firebase/database.rules.json',
            'emulator_harness':'integration/test_official_emulators.py',
            'emulator_runner':'integration/run_official_emulator_tests.py',
        }
        record={'validated':True,'tests_run':23,'project':'demo-coursesphere-vlab',
                'skipped':0,'failures':0,'errors':0,
                'cases':{str(i):'pass' for i in range(23)},
                'source_sha256':{key:hashlib.sha256((gate.ROOT/path).read_bytes()).hexdigest()
                                 for key,path in required.items()}}
        self.assertTrue(validate_emulator_evidence(record))
        for key in ('firebase_configuration','emulator_runner'):
            with self.subTest(key=key):
                stale=dict(record,source_sha256=dict(record['source_sha256']))
                stale['source_sha256'].pop(key)
                self.assertFalse(validate_emulator_evidence(stale))

    def test_boolean_equivalent_integer_is_not_valid_proof(self):
        r=self.report({'official_api_a:8091':'ready','official_api_b:8091':'ready'})
        r['application_ready_for_authenticated_traffic']=1
        self.assertFalse(gate.observability_valid(r))

    def test_observability_proof_binds_real_firebase_code(self):
        required={'backend/firebase.py','backend/firebase_configuration.py',
                  'backend/readiness.py','backend/shared_quota.py',
                  'ops/firebase/database.rules.json'}
        self.assertTrue(required.issubset(set(FILES)))
        r=self.report({'official_api_a:8091':'ready','official_api_b:8091':'ready'})
        for path in required:
            with self.subTest(path=path):
                stale=dict(r,source_sha256=dict(r['source_sha256'],**{path:'0'*64}))
                self.assertFalse(gate.observability_valid(stale))


if __name__=='__main__':unittest.main()
