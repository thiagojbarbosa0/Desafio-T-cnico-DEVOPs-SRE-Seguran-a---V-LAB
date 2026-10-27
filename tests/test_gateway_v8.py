"""Integration tests for the actual local UI gateway (no Flask, Firebase or Docker)."""
from __future__ import annotations
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from backend.dev_gateway import Gateway
from backend.local_server import make_server


class GatewayIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coursesphere-gateway-v8-')
        cls.api = make_server('127.0.0.1', 0, str(Path(cls.tmp.name) / 'synthetic.db'), secret='L' * 48, instance='gateway-test')
        cls.old_port = os.environ.get('PORT')
        os.environ['PORT'] = str(cls.api.server_address[1])
        cls.gateway = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        cls.api_thread = threading.Thread(target=cls.api.serve_forever, daemon=True)
        cls.gateway_thread = threading.Thread(target=cls.gateway.serve_forever, daemon=True)
        cls.api_thread.start(); cls.gateway_thread.start()
        cls.host = '127.0.0.1'
        cls.port = cls.gateway.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.gateway.shutdown(); cls.gateway.server_close(); cls.gateway_thread.join(timeout=3)
        cls.api.shutdown(); cls.api.server_close(); cls.api_thread.join(timeout=3)
        if cls.old_port is None: os.environ.pop('PORT', None)
        else: os.environ['PORT'] = cls.old_port
        cls.tmp.cleanup()

    def call(self, path):
        try: response = urlopen(f'http://{self.host}:{self.port}{path}',timeout=4)
        except HTTPError as e: response = e
        return response.status, response.read(), dict(response.headers)

    def test_dashboard_html_served(self):
        code, body, headers = self.call('/lab/')
        self.assertEqual(code, 200)
        self.assertIn(b'<title>CourseSphere | Painel de seguran', body)
        self.assertIn('text/html', headers.get('Content-Type',''))
        self.assertIn('nosniff', headers.get('X-Content-Type-Options',''))
        self.assertEqual(headers.get('Cross-Origin-Opener-Policy'), 'same-origin')
        self.assertIn("style-src 'self';", headers.get('Content-Security-Policy',''))

    def test_assets_available(self):
        for asset, phrase in [('style.css',b'--surface:#fff'),('app.js',b'exportEvidence')]:
            with self.subTest(asset=asset):
                code, body, _ = self.call('/lab/' + asset)
                self.assertEqual(code, 200)
                self.assertIn(phrase, body)

    def test_ready_proxied_to_real_sandbox(self):
        code, body, headers = self.call('/api/ready')
        self.assertEqual(code, 200)
        self.assertIn(b'"instance": "gateway-test"', body)
        self.assertEqual(headers.get('X-CourseSphere-Instance'), 'gateway-test')

    def test_metrics_not_exposed(self):
        code, _, headers = self.call('/metrics')
        self.assertEqual(code, 403)
        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')

    def test_unknown_static_url_denied(self):
        self.assertEqual(self.call('/lab/../../.env')[0],404)

    def http_json(self, method, path, payload=None, token=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=4)
        headers = {'Content-Type': 'application/json'} if payload is not None else {}
        if token: headers['Authorization'] = 'Bearer ' + token
        conn.request(method, path, body=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        response = conn.getresponse()
        body = json.loads(response.read())
        status = response.status
        request_id = response.getheader('X-Request-ID')
        instance = response.getheader('X-CourseSphere-Instance')
        conn.close()
        return status, body, request_id, instance

    def test_authz_via_real_gateway(self):
        code, login, _, _ = self.http_json('POST', '/api/demo/session', {'uid': 'alice'})
        self.assertEqual(code, 200)
        token = login['access_token']
        code, catalog, _, _ = self.http_json('GET', '/api/courses', token=token)
        self.assertEqual(code, 200)
        bob = next(x for x in catalog['courses'] if x['owner_uid'] == 'bob')
        alice = next(x for x in catalog['courses'] if x['owner_uid'] == 'alice')
        denied, _, trace, instance = self.http_json('PUT', f"/api/courses/{bob['id']}", {'title': bob['title'], 'description': bob['description']}, token=token)
        self.assertEqual(denied, 403)
        self.assertTrue(trace)
        self.assertEqual(instance, 'gateway-test')
        allowed, _, _, _ = self.http_json('PUT', f"/api/courses/{alice['id']}", {'title': alice['title'], 'description': alice['description']}, token=token)
        self.assertEqual(allowed, 200)

    def test_transfer_encoding_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port,timeout=4)
        conn.putrequest('POST','/api/demo/session')
        conn.putheader('Transfer-Encoding','chunked')
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status,400)
        response.read(); conn.close()

    def test_malformed_content_length_rejected(self):
        conn = http.client.HTTPConnection(self.host, self.port,timeout=4)
        conn.putrequest('POST','/api/demo/session')
        conn.putheader('Content-Length','invalid')
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status,400)
        response.read(); conn.close()


if __name__ == '__main__': unittest.main()
