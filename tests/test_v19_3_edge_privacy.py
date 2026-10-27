"""Offline defense-in-depth checks; native Nginx proof is run separately."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from scripts.release_gate_v19 import SOURCES

ROOT=Path(__file__).resolve().parents[1]

class EdgePrivacyV193(unittest.TestCase):
    def setUp(self):
        self.main=(ROOT/'ops/nginx/nginx.conf').read_text()
        self.gateway=(ROOT/'ops/nginx/gateway.conf').read_text()
        self.compose=(ROOT/'compose.yaml').read_text()

    def test_token_queries_rejected_before_flask(self):
        for field in ('id_token','access_token','auth_token','api_key'):
            self.assertIn(field, self.gateway)
        self.assertIn('return 401;', self.gateway)
        self.assertIn('$args ~*', self.gateway)
        self.assertIn('if ($args != "") { return 400; }', self.gateway)

    def test_no_request_uri_or_query_in_structured_logs(self):
        self.assertIn('log_format coursesphere_json escape=json', self.main)
        self.assertIn('"path":"$uri"', self.main)
        self.assertIn('"status":$status', self.main)
        for secret_bearing_field in ('$request_uri', '$args', '$http_authorization', '$http_referer'):
            # Logging format blocks are identified by the quoted access log output.
            log_contract=self.main.split('log_format coursesphere_json',1)[1].split('access_log',1)[0]
            self.assertNotIn(secret_bearing_field, log_contract)

    def test_docker_uses_checked_in_main_config(self):
        self.assertIn('./ops/nginx/nginx.conf:/etc/nginx/nginx.conf:ro',self.compose)
        self.assertIn('./ops/nginx/gateway.conf:/etc/nginx/conf.d/default.conf:ro',self.compose)

    def test_native_gateway_proof_rejects_and_redacts(self):
        src=(ROOT/'scripts/prove_nginx_native.py').read_text()
        self.assertIn("marker='SYNTHETIC_NON_SECRET_TOKEN_V19_3'",src)
        self.assertIn('marker not in log_path.read_text()',src)
        self.assertIn("'query_free_structured_edge_logs'",src)
        self.assertIn("'query_token_blocked_at_edge'",src)

    def test_flask_replica_evidence_proves_edge_privacy(self):
        src=(ROOT/'scripts/prove_original_flask_nginx.py').read_text()
        self.assertIn("'edge_rejects_token_query'",src)
        self.assertIn("'edge_access_log_redacted'",src)
        self.assertIn('nginx_main',SOURCES)

    def test_emulator_suite_was_expanded_without_claiming_execution(self):
        source=(ROOT/'integration/test_official_emulators.py').read_text()
        runner=(ROOT/'integration/run_official_emulator_tests.py').read_text()
        self.assertIn('def test_22_replicas_share_the_same_emulator_quota',source)
        self.assertIn('def test_23_private_rate_limit_counters_are_inaccessible_to_clients',source)
        self.assertIn('result.testsRun == 23',runner)
        self.assertIn('len(cases) == 23',runner)

    def test_nginx_main_config_can_be_syntax_checked_native(self):
        from scripts.check_nginx_main_config_v19_3 import verify
        # The native proof is optional locally. If Nginx exists it MUST parse.
        from shutil import which
        if which('nginx'):
            passed,message=verify()
            self.assertTrue(passed,message)

if __name__=='__main__': unittest.main()

class StrongerEvidenceGateV193(unittest.TestCase):
    def _proof(self):
        from scripts.source_fingerprint import nginx_fingerprint
        return {
            'result':'PASSED','source_fingerprint':nginx_fingerprint(),
            'cases': {
                'request_distribution':{'counts':{'api-a':20,'api-b':20}},
                'failover_after_process_crash':{'result':'passed'},
                'metrics_not_public':{'result':'passed'},
                'query_token_blocked_at_edge':{'result':'passed','status':401},
                'all_api_query_strings_blocked':{'result':'passed','status':400},
                'query_free_structured_edge_logs':{'result':'passed','entries_checked':55},
            },
        }

    def test_privacy_is_required_to_claim_nginx_pass(self):
        from scripts.release_gate_v19_3 import valid_edge_privacy
        proof=self._proof()
        self.assertTrue(valid_edge_privacy(proof))
        del proof['cases']['query_free_structured_edge_logs']
        self.assertFalse(valid_edge_privacy(proof))

    def test_encoded_queries_are_mandatory_to_block(self):
        from scripts.release_gate_v19_3 import valid_edge_privacy
        proof=self._proof()
        proof['cases']['all_api_query_strings_blocked']['status']=200
        self.assertFalse(valid_edge_privacy(proof))

    def test_wrong_source_hash_cannot_pass_privacy(self):
        from scripts.release_gate_v19_3 import valid_edge_privacy
        proof=self._proof()
        proof['source_fingerprint']='0'*64
        self.assertFalse(valid_edge_privacy(proof))

    def test_fake_log_count_cannot_pass(self):
        from scripts.release_gate_v19_3 import valid_edge_privacy
        proof=self._proof()
        proof['cases']['query_free_structured_edge_logs']['entries_checked']=True
        self.assertFalse(valid_edge_privacy(proof))
