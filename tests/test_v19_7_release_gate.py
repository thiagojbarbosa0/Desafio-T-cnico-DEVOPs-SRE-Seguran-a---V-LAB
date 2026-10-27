"""Evidence anti-forgery regressions for optional original-stack runtime tests."""
import copy
import hashlib
from pathlib import Path
import unittest
from scripts.release_gate_v19_7 import (valid_native, valid_official_docker,
                                        NATIVE_FILES, DOCKER_FILES, ROOT)


def fingerprints(files):
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}


def native():
    return {'validated': True, 'version':'V19.7',
            'scope':'REAL Nginx. Upstream Flask and React mocked; local synthetic.',
            'source_sha256':fingerprints(NATIVE_FILES),
            'tests': {'nginx_config':'pass','api_route_original_prefix':'pass',
                      'react_spa_gateway':'pass','metrics_denied':'pass',
                      'query_blocking':'pass','no_token_query_in_edge_logs':'pass',
                      'survivor_after_backend_stop':'8/8 pass',
                      'backend_distribution':{'a':20,'b':20}}}


def official_docker():
    return {'validated': True, 'version':'V19.7',
            'source_sha256': fingerprints(DOCKER_FILES),
            'tests':{
                **{k:'pass' for k in ('compose_config','original_flask_health',
                  'anonymous_profile_denied','original_react_served','spa_fallback',
                  'public_metrics_denied','api_query_rejected',
                  'query_marker_not_logged','stopped_replica_restored')},
                'two_original_flask_replicas':{
                    'result':'pass','replicas':2,'distribution':[21,19]},
                'original_failover':{'result':'pass','responses':8},
            }}


class EvidenceContracts(unittest.TestCase):
    def test_native_requires_all_source_hashes(self):
        doc=native();self.assertTrue(valid_native(doc))
        doc['source_sha256'].pop('ops/nginx/gateway.official.conf')
        self.assertFalse(valid_native(doc))

    def test_native_denies_fake_no_second_replica(self):
        doc=native();doc['tests']['backend_distribution']['b']=0
        self.assertFalse(valid_native(doc))

    def test_native_denies_old_scope_and_missing_log_proof(self):
        doc=native();doc['scope']='Docker real Flask/Firebase'
        self.assertFalse(valid_native(doc))
        doc=native();doc['tests']['no_token_query_in_edge_logs']='skip'
        self.assertFalse(valid_native(doc))

    def test_docker_requires_failover_and_restart(self):
        doc=official_docker();self.assertTrue(valid_official_docker(doc))
        doc['tests']['stopped_replica_restored']='FAILED'
        self.assertFalse(valid_official_docker(doc))
        doc=official_docker();doc['tests']['original_failover']['responses']=7
        self.assertFalse(valid_official_docker(doc))

    def test_docker_rejects_only_one_upstream_or_old_config(self):
        doc=official_docker();doc['tests']['two_original_flask_replicas']['distribution']=[40]
        self.assertFalse(valid_official_docker(doc))
        doc=official_docker();doc['source_sha256']['backend/endpoints.py']='0'*64
        self.assertFalse(valid_official_docker(doc))

    def test_unvalidated_never_counts(self):
        doc=official_docker();doc['validated']=False
        self.assertFalse(valid_official_docker(doc))
        doc=native();doc['validated']=False
        self.assertFalse(valid_native(doc))


if __name__=='__main__':
    unittest.main()
