"""Ensure newly introduced Flask/Nginx evidence cannot be forged by stale hashes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import release_gate_v19 as gate


class TestOriginalReplicaGate(unittest.TestCase):
    def setUp(self):
        self.evidence={
            'validated':True,
            'source_sha256':{
                name:hashlib.sha256((gate.ROOT/path).read_bytes()).hexdigest()
                for name,path in gate.SOURCES.items()},
            'tests':{
                'original_flask_replicas':{'flask-a':20,'flask-b':20},
                'original_flask_authorization':{'anonymous':401,'bearer_valid':200,'query_token':401},
                'survivor_after_flask_a_crash':{'instance':'flask-b','successes':8},
                'metrics_private':403,
                'edge_rejects_token_query':401,
                'encoded_query_blocked':400,
                'edge_access_log_redacted':True,
            }
        }

    def check(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'evidence.json'
            p.write_text(json.dumps(self.evidence))
            with mock.patch.object(gate,'OPTIONAL',p):
                return gate.valid_replica_proof()

    def test_complete_matching_evidence(self):
        self.assertTrue(self.check())

    def test_reject_outdated_source_hash(self):
        self.evidence['source_sha256']['endpoints']='0'*64
        self.assertFalse(self.check())

    def test_reject_one_replica_missing(self):
        self.evidence['tests']['original_flask_replicas']={'flask-a':40}
        self.assertFalse(self.check())

    def test_reject_false_success(self):
        self.evidence['validated']=False
        self.assertFalse(self.check())

    def test_reject_auth_bypass(self):
        self.evidence['tests']['original_flask_authorization']['query_token']=200
        self.assertFalse(self.check())

    def test_reject_unredacted_nginx_access_log(self):
        self.evidence['tests']['edge_access_log_redacted']=False
        self.assertFalse(self.check())

    def test_reject_token_not_blocked_at_edge(self):
        self.evidence['tests']['edge_rejects_token_query']=200
        self.assertFalse(self.check())

    def test_reject_failed_failover(self):
        self.evidence['tests']['survivor_after_flask_a_crash']['successes']=5
        self.assertFalse(self.check())

    def test_gate_does_not_promote_stubbed_flask_to_firebase(self):
        result=gate.evaluate()
        self.assertFalse(result['supplemental_original_flask_nginx']['counts_in_weighted_acceptance'])
        self.assertEqual(result['new_security_boundary']['emulator_expected_tests'], 23)


if __name__=='__main__': unittest.main()
