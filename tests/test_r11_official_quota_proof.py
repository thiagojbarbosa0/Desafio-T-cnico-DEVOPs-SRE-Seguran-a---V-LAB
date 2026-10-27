"""R11: original Flask quota proof protocol; mocks never count as emulator proof."""
import base64
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.verify_official_replica_quota_r11 import (
    CHECKS, SOURCES, VerificationFailure, parse_target,
    validate_emulator_environment, request, run,
)

def _url64(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')

TOKEN = (_url64({'alg':'none','typ':'JWT'}) + '.' +
         _url64({'aud':'demo-coursesphere-vlab',
                 'iss':'https://securetoken.google.com/demo-coursesphere-vlab',
                 'sub':'test-user'}) + '.fakeSignature')
ENV = {
    'COURSESPHERE_USE_FIREBASE_EMULATORS': '1',
    'GCLOUD_PROJECT': 'demo-coursesphere-vlab',
    'COURSESPHERE_R11_FIREBASE_ID_TOKEN': TOKEN,
    'FIREBASE_AUTH_EMULATOR_HOST': '127.0.0.1:9099',
    'FIREBASE_DATABASE_EMULATOR_HOST': '127.0.0.1:9000',
}


class SharedFake:
    """Pure fake HTTP server, not Flask/Firebase; negative controls for CLI."""
    def __init__(self, independent=False, wrong_labels=False):
        self.count = 0
        self.profile = {'about': ''}
        self.lock = threading.Lock()
        self.a = self._serve('official_api_a')
        self.b = self._serve('official_api_a' if wrong_labels else 'official_api_b',
                             self if not independent else SharedFakeState())
        for item in (self.a, self.b):
            threading.Thread(target=item.serve_forever, daemon=True).start()

    def _serve(self, name, storage=None):
        data = storage or self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def route(self):
                if self.headers.get('Authorization') != 'Bearer ' + TOKEN or self.path != '/users/info':
                    code, obj = 401, {'error':'denied'}
                elif self.command == 'GET':
                    with data.lock:
                        code, obj = 200, (dict(data.profile) if data.profile is not None else None)
                elif self.command == 'POST':
                    size = int(self.headers.get('Content-Length',0))
                    body = json.loads(self.rfile.read(size))
                    with data.lock:
                        if data.count >= 20:
                            code, obj = 429, {'error':'quota'}
                        else:
                            data.count += 1
                            data.profile = {'about':body['about']}
                            code, obj = 200, {'message':'ok'}
                else:
                    code, obj = 405, {}
                data_bytes = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header('X-CourseSphere-Replica', name)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(data_bytes)))
                self.end_headers()
                self.wfile.write(data_bytes)
            do_GET = route
            do_POST = route
        return ThreadingHTTPServer(('127.0.0.1',0), Handler)

    def origins(self):
        return [f'http://127.0.0.1:{item.server_address[1]}' for item in (self.a,self.b)]

    def close(self):
        for server in (self.a, self.b):
            server.shutdown();server.server_close()


class SharedFakeState:
    def __init__(self):
        self.count = 0
        self.profile = {'about':''}
        self.lock = threading.Lock()


class TestR11(unittest.TestCase):
    def test_valid_loopback(self):
        self.assertEqual(parse_target('http://127.0.0.1:8091'), ('127.0.0.1',8091))
        self.assertEqual(parse_target('http://[::1]:8092'), ('::1',8092))

    def test_hostile_targets_fail_closed(self):
        values = (
            'https://127.0.0.1:80', 'http://8.8.8.8:8091',
            'http://localhost:8091', 'http://127.0.0.1',
            'http://127.0.0.1:8091/users/info',
            'http://user:password@127.0.0.1:80',
            'http://127.0.0.1:80?auth=x', 'http://127.0.0.1:8091#x',
            'http://127.0.0.1:0', 'file:///etc/passwd', 'http://127.0.0.1:99999',
            'http://127.0.0.1:8091@evil.com', 'http://127.0.0.1:8091;hack',
        )
        for v in values:
            with self.subTest(target=v), self.assertRaises(VerificationFailure): parse_target(v)

    def test_emulator_guard(self):
        self.assertEqual(validate_emulator_environment(ENV), TOKEN)
        for mutation in (
            {'COURSESPHERE_USE_FIREBASE_EMULATORS':'0'},
            {'GCLOUD_PROJECT':'real-project'},
            {'GCLOUD_PROJECT':'demo-abc/evil'},
            {'COURSESPHERE_R11_FIREBASE_ID_TOKEN':'secret'},
            {'COURSESPHERE_R11_FIREBASE_ID_TOKEN':'x'*20000},
            {'COURSESPHERE_R11_FIREBASE_ID_TOKEN':TOKEN.split('.')[0]+'.'+_url64({'aud':'real-project','iss':'https://securetoken.google.com/real-project','sub':'test-user'})+'.fakeSignature'},
            {'FIREBASE_AUTH_EMULATOR_HOST':'evil.com:9099'},
            {'FIREBASE_DATABASE_EMULATOR_HOST':'localhost.attacker.com:9000'},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(VerificationFailure):
                validate_emulator_environment({**ENV,**mutation})

    def test_two_http_servers_share_quota(self):
        demo = SharedFake()
        try:
            result = run(*demo.origins(),env=ENV,clock=lambda:120.0)
            self.assertTrue(result['validated'])
            self.assertEqual(set(result['checks']),set(CHECKS))
            self.assertTrue(all(result['checks'].values()))
            self.assertEqual(result['additional_acceptance_points'],0)
            self.assertNotIn(TOKEN,json.dumps(result))
            self.assertNotIn('access_token',json.dumps(result))
            self.assertEqual(demo.count,20)
        finally:
            demo.close()

    def test_uninitialized_emulator_profile_is_accepted(self):
        demo = SharedFake()
        demo.profile = None
        try:
            result = run(*demo.origins(), env=ENV, clock=lambda:120)
            self.assertTrue(result['validated'])
            self.assertEqual(demo.count, 20)
        finally:
            demo.close()

    def test_altered_backend_label_during_run_is_rejected(self):
        demo=SharedFake()
        calls = {}
        def changing_client(replica, method, path, token, payload=None):
            value = request(replica, method, path, token, payload)
            calls[replica] = calls.get(replica,0)+1
            if calls[replica] == 3:
                return value[0], 'official_api_b' if value[1]=='official_api_a' else 'official_api_a', value[2]
            return value
        try:
            with self.assertRaisesRegex(VerificationFailure,'switched replica'):
                run(*demo.origins(),env=ENV,clock=lambda:120,client=changing_client)
        finally:
            demo.close()

    def test_duplicate_jwt_aud_claims_are_rejected(self):
        payload=('{'+'"aud":"real-production","aud":"demo-coursesphere-vlab",'
                 '"iss":"https://securetoken.google.com/demo-coursesphere-vlab",'
                 '"sub":"test-user"}')
        malicious=(TOKEN.split('.')[0] + '.' + base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')
                   + '.fakeSignature')
        with self.assertRaises(VerificationFailure):
            validate_emulator_environment({**ENV,'COURSESPHERE_R11_FIREBASE_ID_TOKEN':malicious})

    def test_isolated_quota_is_rejected(self):
        demo=SharedFake(independent=True)
        try:
            with self.assertRaisesRegex(VerificationFailure,'21st write'):
                run(*demo.origins(),env=ENV,clock=lambda:120.0)
        finally:
            demo.close()

    def test_duplicate_replica_labels_are_rejected(self):
        demo=SharedFake(wrong_labels=True)
        try:
            with self.assertRaisesRegex(VerificationFailure,'distinct Flask replicas'):
                run(*demo.origins(),env=ENV,clock=lambda:120.0)
        finally:
            demo.close()

    def test_same_origin_rejected(self):
        with self.assertRaisesRegex(VerificationFailure,'distinct'):
            run('http://127.0.0.1:9999','http://127.0.0.1:9999',env=ENV)

    def test_minute_boundary_guard(self):
        with self.assertRaisesRegex(VerificationFailure,'window'):
            run('http://127.0.0.1:9998','http://127.0.0.1:9999',env=ENV,clock=lambda:119)

    def test_no_network_or_redirect_on_malformed_origin(self):
        with patch('http.client.HTTPConnection') as conn:
            with self.assertRaises(VerificationFailure):
                run('http://example.com:9000','http://127.0.0.1:8000',env=ENV)
            conn.assert_not_called()

    def test_source_bindings_include_original_backend_and_ci(self):
        self.assertIn('backend/endpoints.py', SOURCES)
        self.assertIn('backend/shared_quota.py', SOURCES)
        self.assertIn('.github/workflows/ci.yml', SOURCES)
        text = (Path(__file__).resolve().parents[1]/'backend/endpoints.py').read_text()
        self.assertIn('"X-CourseSphere-Replica"', text)
        self.assertIn('replica_label(', text)


if __name__ == '__main__':
    unittest.main()
