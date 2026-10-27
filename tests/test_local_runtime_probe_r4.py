"""Local-only runtime smoke checker, including protocol regression fixtures."""
import unittest
from scripts.probe_official_local_runtime_r4 import get_local, inspect


class ProbeTests(unittest.TestCase):
    def fetch(self, status=200, ready='ready', metrics=403, token=401):
        def fake(port,path):
            self.assertEqual(port,8081)
            if path=='/health':return status,b'{"status":"ok","service":"coursesphere-api"}'
            if path=='/ready':
                return (200 if ready=='ready' else 503), ('{"status":"%s","service":"coursesphere-api"}'%ready).encode()
            if path=='/metrics':return metrics,b'forbidden'
            return token,b'{"error":"Use Authorization header"}'
        return fake

    def test_healthy_runtime_contract(self):
        report=inspect(fetch=self.fetch())
        self.assertTrue(report['checks_passed'])
        self.assertEqual(report['readiness'],'ready')
        self.assertFalse(report['runtime_attestation'])
        self.assertEqual(report['acceptance_credit'],0)

    def test_readiness_503_is_expected_degraded_contract(self):
        r=inspect(fetch=self.fetch(ready='unavailable'))
        self.assertTrue(r['checks_passed'])
        self.assertEqual(r['readiness'],'degraded')

    def test_liveness_500_is_detected(self):
        self.assertFalse(inspect(fetch=self.fetch(status=500))['checks_passed'])

    def test_public_metrics_exposure_is_rejected(self):
        self.assertEqual(inspect(fetch=self.fetch(metrics=200))['checks']['private_metrics_at_gateway'],'fail')

    def test_query_token_accepted_is_rejected(self):
        self.assertEqual(inspect(fetch=self.fetch(token=200))['checks']['reject_query_token'],'fail')

    def test_token_reflection_is_rejected(self):
        fake=self.fetch()
        def leak(port,path):
            if 'id_token=' in path:return 401,b'{"echo":"SYNTHETIC_ONLY"}'
            return fake(port,path)
        self.assertEqual(inspect(fetch=leak)['checks']['reject_query_token'],'fail')

    def test_offline_service_fails(self):
        def offline(*_):raise OSError('synthetic sensitive connection error')
        r=inspect(fetch=offline)
        self.assertFalse(r['checks_passed'])
        self.assertNotIn('sensitive',str(r))

    def test_wrong_json_contract_fails(self):
        original=self.fetch()
        def wrong(port,path):
            if path=='/ready':return 503,b'<html>not ready</html>'
            return original(port,path)
        self.assertEqual(inspect(fetch=wrong)['checks']['dependency_readiness_contract'],'fail')

    def test_port_restrictions_block_untrusted_urls(self):
        for port in (0,80,65536,False,None,'8081'):
            with self.subTest(port=port),self.assertRaises(ValueError):get_local(port,'/health')
        for path in ('/root','/health?Authorization=secret','http://example.com','/ready?token=foo'):
            with self.subTest(path=path),self.assertRaises(ValueError):get_local(8081,path)

if __name__=='__main__':unittest.main()
