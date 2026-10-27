"""Privacy and gateway correlation contracts (offline and deterministic)."""
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.request_correlation import correlation_id, replica_label

ROOT = Path(__file__).resolve().parents[1]


class CorrelationTests(unittest.TestCase):
    def test_valid_gateway_nginx_hex_id_is_preserved_when_trusted(self):
        request_id = '0123456789abcdef0123456789abcdef'
        self.assertEqual(correlation_id(request_id, trust_gateway=True), request_id)
    def test_uppercase_normalized(self):
        self.assertEqual(correlation_id('A'*32, trust_gateway=True), 'a'*32)
    def test_untrusted_input_is_always_overwritten(self):
        value = 'a'*32
        with patch('backend.request_correlation.uuid.uuid4') as uid:
            uid.return_value.hex='b'*32
            self.assertEqual(correlation_id(value,trust_gateway=False),'b'*32)
    def test_malformed_gateway_input_replaced(self):
        for value in ('', 'ABCD', 'x'*32, 'A'*33, 'A'*32+'\nAuthorization: bad',
                      '../../etc/passwd', None, False, 1234, [], {}):
            with self.subTest(value=str(value)[:20]):
                result=correlation_id(value, trust_gateway=True)
                self.assertRegex(result,r'^[0-9a-f]{32}$')
                self.assertNotEqual(result, value)
    def test_no_replica_input_can_become_label(self):
        for value in (None, 'A'*3000, 'official_api_a\ninject', 'evil', 1, 'api-a'):
            self.assertEqual(replica_label(value), 'unknown')
    def test_replica_allowlist(self):
        for value in ('official_api_a','official_api_b'):
            self.assertEqual(replica_label(value),value)
    def test_gateway_overwrites_client_header(self):
        gateway=(ROOT/'ops/nginx/gateway.official.conf').read_text()
        self.assertIn('proxy_set_header X-Request-ID $request_id;',gateway)
        self.assertIn('location = /metrics { return 403; }',gateway)
    def test_compose_sets_private_gateway_trust_for_both_replicas(self):
        compose=(ROOT/'compose.official.yaml').read_text()
        self.assertIn("COURSESPHERE_TRUST_GATEWAY_REQUEST_ID: '1'",compose)
        self.assertIn('COURSESPHERE_REPLICA_NAME: official_api_a',compose)
        self.assertIn('COURSESPHERE_REPLICA_NAME: official_api_b',compose)
        self.assertIn("ports: ['127.0.0.1:8081:8081']",compose)
    def test_flask_logs_sanitized_replica_and_gateway_correlation(self):
        source=(ROOT/'backend/endpoints.py').read_text()
        self.assertIn('correlation_id(',source)
        self.assertIn("'COURSESPHERE_TRUST_GATEWAY_REQUEST_ID'",source)
        self.assertIn("replica_label(os.getenv('COURSESPHERE_REPLICA_NAME'))",source)
        self.assertIn('"request_id": getattr(g, "request_id", "unknown")',source)

if __name__=='__main__': unittest.main()
