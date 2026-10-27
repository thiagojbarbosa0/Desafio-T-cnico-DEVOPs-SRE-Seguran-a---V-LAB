"""The V13 acceptance gate must reject stale and incomplete evidence."""
import unittest
from scripts.release_gate_v13 import valid_docker, valid_frontend, valid_nginx, valid_offline, evaluate, offline_fingerprint
from scripts.source_fingerprint import docker_fingerprint,frontend_fingerprint,nginx_fingerprint

class EvidenceIntegrityV13(unittest.TestCase):
    def test_gate_stays_unapproved_without_manual_assessment(self):
        result=evaluate()
        self.assertFalse(result['ready_for_submission'])
        self.assertFalse(result['gates']['five_findings_three_root_cause_fixes']['passed'])

    def test_offline_requires_version_and_real_count(self):
        doc={'validated':True,'tests_run':134,'failures':0,'errors':0,'source_fingerprint':offline_fingerprint()}
        self.assertTrue(valid_offline(doc))
        doc['source_fingerprint']='0'*64
        self.assertFalse(valid_offline(doc))

    def test_docker_failover_and_restart_cannot_be_skipped(self):
        doc={'validated':True,'source_fingerprint':docker_fingerprint(),'tests':{
            k:'pass' for k in ('compose_config','dashboard','metrics_not_public','prometheus_scrapes_two',
                               'grafana_database_health','grafana_provisioned_dashboard','api_a_restarted')}}
        doc['tests']['replica_distribution']={'api-a':20,'api-b':20}
        doc['tests']['nginx_failover_after_api_a_stop']={'result':'pass'}
        self.assertTrue(valid_docker(doc))
        doc['tests']['api_a_restarted']='FAILED_RESTART_MANUALLY'
        self.assertFalse(valid_docker(doc))
        doc['tests']['api_a_restarted']='pass'
        doc['tests']['grafana_provisioned_dashboard']='not_checked'
        self.assertFalse(valid_docker(doc))
        doc['tests']['grafana_provisioned_dashboard']='pass'
        doc['source_fingerprint']='old'
        self.assertFalse(valid_docker(doc))

    def test_frontend_needs_current_source(self):
        self.assertTrue(valid_frontend({'validated':True,'source_fingerprint':frontend_fingerprint()}))
        self.assertFalse(valid_frontend({'validated':True,'source_fingerprint':'stale'}))

    def test_nginx_proof_needs_two_replicas(self):
        doc={'result':'PASSED','source_fingerprint':nginx_fingerprint(),'cases':{
            'request_distribution':{'counts':{'api-a':20,'api-b':20}},
            'failover_after_process_crash':{'result':'passed'},
            'metrics_not_public':{'result':'passed'}}}
        self.assertTrue(valid_nginx(doc))
        doc['cases']['request_distribution']['counts'].pop('api-a')
        self.assertFalse(valid_nginx(doc))

if __name__=='__main__': unittest.main()
