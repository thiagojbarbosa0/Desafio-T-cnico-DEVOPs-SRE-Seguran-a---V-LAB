"""Proof chain for R7 synthetic HTTP; never awards weighted acceptance."""
import hashlib
import json
import unittest
from unittest.mock import patch
from scripts import release_gate_work_v19_9 as gate

FILES = ('backend/demo_store.py', 'backend/security_core.py',
         'backend/local_server.py', 'scripts/prove_r7_dual_replica_auth.py')


def fixture():
    return {'validated': True, 'version': 'R7-derived-V19.9',
            'checks': {k: True for k in ('two_liveness_checks','two_readiness_checks',
                      'cross_replica_signed_token','cross_user_access_blocked',
                      'shared_quota_across_both_replicas','no_increment_after_429')},
            'counts': {'successful_login_requests':30,'rate_limited_login_requests':11},
            'source_sha256': {f:hashlib.sha256((gate.ROOT/f).read_bytes()).hexdigest()
                              for f in FILES}}


class R7Gate(unittest.TestCase):
    def read_fixture(self,value):
        with patch.object(gate.Path,'read_text',return_value=json.dumps(value)):
            return gate.annotate({'gates':{},'weighted_acceptance_verified_percent':0})

    def test_valid_current_synthetic_proof(self):
        report=self.read_fixture(fixture())
        self.assertTrue(report['r7_synthetic_two_replica_http']['confirmed_current_source'])
        self.assertEqual(report['r7_synthetic_two_replica_http']['additional_acceptance_points'],0)
        self.assertFalse(report['ready_for_submission'])
        self.assertIn('NOT main V19.15',report['version'])

    def test_missing_report_is_not_accepted(self):
        with patch.object(gate.Path,'read_text',side_effect=OSError('missing')):
            report=gate.annotate({'gates':{}})
        self.assertFalse(report['r7_synthetic_two_replica_http']['confirmed_current_source'])

    def test_malformed_report_is_not_accepted(self):
        with patch.object(gate.Path,'read_text',return_value='{"validated":true}'):
            report=gate.annotate({'gates':{}})
        self.assertFalse(report['r7_synthetic_two_replica_http']['confirmed_current_source'])

    def test_stale_source_rejected(self):
        value=fixture(); value['source_sha256']['backend/demo_store.py']='0'*64
        self.assertFalse(self.read_fixture(value)['r7_synthetic_two_replica_http']['confirmed_current_source'])

    def test_counts_mismatch_rejected(self):
        value=fixture(); value['counts']['successful_login_requests']=31
        self.assertFalse(self.read_fixture(value)['r7_synthetic_two_replica_http']['confirmed_current_source'])

    def test_partial_replica_results_rejected(self):
        value=fixture(); value['checks']['cross_replica_signed_token']=False
        self.assertFalse(self.read_fixture(value)['r7_synthetic_two_replica_http']['confirmed_current_source'])
