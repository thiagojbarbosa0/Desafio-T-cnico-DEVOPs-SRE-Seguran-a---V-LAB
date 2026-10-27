"""True HTTP requests through ORIGINAL and PATCHED Flask apps, with a fake Firebase.

This proves which route behaviors differ without credentials or network calls to
Firebase. Flask and Werkzeug are real; *only the service adapters* are synthetic.
The archived upstream source is never exposed on non-loopback interfaces.
Run: python -m unittest integration.test_original_http_stubbed -v
"""
from __future__ import annotations
import importlib.util
import json
import sys
import threading
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from urllib import request, error

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'before': ROOT / 'audit/baseline/endpoints_original.txt',
    'after': ROOT / 'backend/endpoints.py',
}

try:
    import flask  # noqa: F401
    import flask_cors  # noqa: F401
    from werkzeug.serving import make_server
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


class SyntheticFirebase:
    """No remote services. All values and identities are synthetic."""
    fail_profile = False
    profiles: dict = {}
    chats: dict = {}

    @classmethod
    def reset(cls):
        cls.fail_profile = False
        cls.profiles = {}
        cls.chats = {}

    @staticmethod
    def probe_dependencies():
        # Explicit synthetic readiness for HTTP tests; real Firebase is proved separately.
        return True

    @staticmethod
    def enforce_quota(uid, action):
        # The HTTP before/after suite isolates route authorization/contract
        # and deliberately mocks the shared Firebase RTDB transaction.
        assert uid == 'alice' and action in {'recommendation', 'message_id', 'chat_write', 'profile_write', 'chat_delete'}

    @staticmethod
    def create_user(email, password):
        return {'user_id': 'synthetic-user', 'email': email}

    @staticmethod
    def verify_id_token(token):
        if token != 'SYNTHETIC_TOKEN':
            raise ValueError('SYNTHETIC_INTERNAL_AUTH_DETAILS')
        return {'uid': 'alice'}

    @classmethod
    def get_user_info(cls, uid):
        if cls.fail_profile:
            raise RuntimeError('SYNTHETIC_INTERNAL_DB_DETAILS')
        return cls.profiles.get(uid, {'majors': ['Synthetic Studies']})

    @classmethod
    def set_user_info(cls, uid, user_info):
        cls.profiles[uid] = user_info

    @classmethod
    def try_get_user_info(cls, token):
        return cls.profiles.get('alice') if token == 'SYNTHETIC_TOKEN' else None

    @classmethod
    def save_chat(cls, uid, chat_id, messages):
        cls.chats[(uid, chat_id)] = messages

    @classmethod
    def delete_chat(cls, uid, chat_id):
        cls.chats.pop((uid, chat_id), None)

    @classmethod
    def list_chats(cls, uid):
        return []


class SyntheticQueryManager:
    def __init__(self, query, user_data):
        self.response = {'botResponse': 'SYNTHETIC_REPLY', 'newRecommendations': []}


def load_app(source: Path, name: str):
    """Execute archived endpoint module with synthetic service imports, real Flask."""
    firebase_mod = types.ModuleType('firebase')
    firebase_mod.Firebase = SyntheticFirebase
    query_mod = types.ModuleType('query_manager')
    query_mod.QueryManager = SyntheticQueryManager
    main_mod = types.ModuleType('main')
    main_mod.hashFunction = lambda data: 'synthetic_message_id'
    module = types.ModuleType(name)
    module.__file__ = str(source)
    backend_path = str(ROOT / 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    with mock.patch.dict(sys.modules, {
        'firebase': firebase_mod, 'query_manager': query_mod,
        'main': main_mod, name: module,
    }):
        exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), module.__dict__)
    module.app.config.update(TESTING=True)
    return module.app


@contextmanager
def local_http(app):
    """Real loopback HTTP; no production endpoints or Firebase access."""
    server = make_server('127.0.0.1', 0, app, threaded=True,
                         request_handler=app.config.get('SAFE_REQUEST_HANDLER'))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def http_call(base: str, path: str, method='GET', data=None, token=None, origin=None):
    body = json.dumps(data).encode() if data is not None else None
    headers = {'Content-Type': 'application/json'} if body is not None else {}
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    if origin is not None:
        headers['Origin'] = origin
    req = request.Request(base + path, data=body, headers=headers, method=method)
    try:
        resp = request.urlopen(req, timeout=5)
    except error.HTTPError as exc:
        resp = exc
    with resp:
        raw = resp.read()
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = {'non_json': True}
        return resp.status, payload, dict(resp.headers)


@unittest.skipUnless(HAS_FLASK, 'Real Flask/Flask-Cors unavailable: run on Fedora or GitHub CI')
class OriginalHTTPBeforeAfter(unittest.TestCase):
    """Each case observes REAL Flask routing over HTTP, fake Firebase storage."""
    results = {}

    @classmethod
    def setUpClass(cls):
        cls.before = load_app(SOURCES['before'], 'coursesphere_http_before_v11')
        cls.after = load_app(SOURCES['after'], 'coursesphere_http_after_v11')
        cls.results = {}

    def setUp(self):
        SyntheticFirebase.reset()

    def compare(self, name, path, method='GET', data=None, token=None, origin=None):
        with local_http(self.before) as original:
            old = http_call(original, path, method, data, token, origin)
        with local_http(self.after) as corrected:
            new = http_call(corrected, path, method, data, token, origin)
        self.__class__.results[name] = {
            'method': method, 'path': path.split('?')[0],
            'original_http_status': old[0], 'corrected_http_status': new[0],
            'original_content_type': old[2].get('Content-Type', ''),
            'corrected_content_type': new[2].get('Content-Type', ''),
            'original_error_leaks_internal_marker': 'SYNTHETIC_INTERNAL_' in json.dumps(old[1]),
            'corrected_error_leaks_internal_marker': 'SYNTHETIC_INTERNAL_' in json.dumps(new[1]),
            'original_cors_allows_untrusted_origin': bool(old[2].get('Access-Control-Allow-Origin')),
            'corrected_cors_allows_untrusted_origin': bool(new[2].get('Access-Control-Allow-Origin')),
        }
        return old, new

    def test_anonymous_privileged_signup(self):
        old, new = self.compare('A01_privileged_signup', '/users/create', 'POST',
                                {'email':'synthetic@example.invalid','password':'SYNTHETIC_ONLY'})
        self.assertEqual((old[0], new[0]), (200,410))

    def test_unauthenticated_user_query(self):
        old, new = self.compare('A02_unauthenticated_query', '/users/query', 'POST',
                                {'query': 'synthetic-only'})
        self.assertEqual((old[0], new[0]), (200,401))

    def test_token_accepted_from_query_string(self):
        # Deliberately synthetic marker, NEVER an actual user credential.
        old, new = self.compare('A03_query_string_token', '/users/info?id_token=SYNTHETIC_TOKEN')
        self.assertEqual((old[0], new[0]), (200,401))

    def test_invalid_token_leaks_internal_detail(self):
        old, new = self.compare('A04_auth_error_information_leak', '/users/info?id_token=SYNTHETIC_BAD',
                                token='SYNTHETIC_BAD')
        self.assertIn('SYNTHETIC_INTERNAL_AUTH_DETAILS', json.dumps(old[1]))
        self.assertNotIn('SYNTHETIC_INTERNAL_AUTH_DETAILS', json.dumps(new[1]))
        self.assertEqual(new[0],401)

    def test_unbounded_profile_input(self):
        old, new = self.compare('A05_oversized_profile', '/users/info', 'POST',
                                {'id_token':'SYNTHETIC_TOKEN','about':'x'*2000},
                                token='SYNTHETIC_TOKEN')
        self.assertEqual((old[0],new[0]),(200,400))

    def test_unbounded_chat_messages(self):
        old, new = self.compare('A06_chat_input_limit', '/chats/synthetic_chat/messages', 'POST',
                                {'messages':[{'sender':'user','content':'hello','messageID':'msg'}]*101},
                                token='SYNTHETIC_TOKEN')
        self.assertEqual((old[0],new[0]),(200,400))

    def test_permissive_cors_restricted(self):
        old, new = self.compare('A07_cors_policy', '/health', origin='https://malicious.example.invalid')
        self.assertEqual(old[2].get('Access-Control-Allow-Origin'), 'https://malicious.example.invalid')
        self.assertIsNone(new[2].get('Access-Control-Allow-Origin'))
        self.assertEqual(new[0],200)

    def test_profile_update_rejects_body_only_token(self):
        # Upstream trusts a bearer equivalent supplied in JSON; corrected API
        # accepts authentication ONLY in the Authorization header.
        old, new = self.compare('A10_body_token_profile_update', '/users/info', 'POST',
                                {'id_token': 'SYNTHETIC_TOKEN', 'majors': ['Synthetic Studies']})
        self.assertEqual((old[0], new[0]), (200, 401))

    def test_hash_without_authorization_returns_auth_error(self):
        # An unauthenticated request raised an exception treated as HTTP 500.
        # The revised handler makes this an explicit authentication failure.
        old, new = self.compare('A11_hash_auth_error_semantics', '/hash', 'POST',
                                {'content': 'synthetic-only'})
        self.assertEqual((old[0], new[0]), (500, 401))
        self.assertNotIn('Traceback', json.dumps(new[1]))

    def test_chat_delete_without_authorization_is_denied(self):
        old, new = self.compare('A12_chat_delete_auth_semantics',
                                '/chats/synthetic_chat', 'DELETE')
        self.assertEqual((old[0], new[0]), (400, 401))

    def test_query_size_is_bounded(self):
        old, new = self.compare('A13_query_size_limit', '/users/query', 'POST',
                                {'query': 'x' * 2001}, token='SYNTHETIC_TOKEN')
        self.assertEqual((old[0], new[0]), (200, 400))

    def test_metrics_disabled_by_default(self):
        # Default deployment must NOT reveal metrics without explicit opt-in.
        with mock.patch.dict('os.environ', {'COURSESPHERE_METRICS_ENABLED': ''}):
            old, new = self.compare('A14_metrics_disabled_by_default', '/metrics')
        self.assertEqual((old[0], new[0]), (404, 404))

    def test_local_metrics_opt_in(self):
        with mock.patch.dict('os.environ', {'COURSESPHERE_METRICS_ENABLED': '1'}):
            old, new = self.compare('A15_local_metrics_explicit_opt_in', '/metrics')
            self.assertEqual((old[0], new[0]), (404, 200))
            with local_http(self.after) as corrected:
                status, payload, headers = http_call(corrected, '/metrics')
                self.assertEqual(status, 200)
                self.assertIn('text/plain', headers['Content-Type'])
                self.assertTrue(payload.get('non_json'))
                with request.urlopen(corrected + '/metrics', timeout=5) as response:
                    metrics_text = response.read().decode()
                    self.assertIn('coursesphere_original_http_requests_total', metrics_text)
                    self.assertNotIn('SYNTHETIC_TOKEN', metrics_text)

    def test_security_headers_added(self):
        old, new = self.compare('A08_security_headers', '/health')
        self.assertIsNone(old[2].get('X-Frame-Options'))
        self.assertEqual(new[2].get('X-Frame-Options'), 'DENY')
        self.assertEqual(new[2].get('X-Content-Type-Options'), 'nosniff')

    def test_backend_happy_path_preserved(self):
        # The original API accepted tokens in the query string. The corrected
        # API intentionally REJECTS such URLs, even with a valid Bearer header.
        # Verify each version's supported happy path instead of submitting a
        # deliberately forbidden URL to the corrected version.
        with local_http(self.before) as original:
            old = http_call(original, '/users/info?id_token=SYNTHETIC_TOKEN')
        with local_http(self.after) as corrected:
            new = http_call(corrected, '/users/info', token='SYNTHETIC_TOKEN')
            rejected = http_call(corrected,
                                 '/users/info?id_token=SYNTHETIC_TOKEN',
                                 token='SYNTHETIC_TOKEN')
        self.__class__.results['A09_authorized_profile_read'] = {
            'method': 'GET',
            'original_path': '/users/info?{token}',
            'corrected_path': '/users/info',
            'original_http_status': old[0],
            'corrected_http_status': new[0],
            'corrected_query_token_rejected_status': rejected[0],
            'original_content_type': old[2].get('Content-Type', ''),
            'corrected_content_type': new[2].get('Content-Type', ''),
        }
        self.assertEqual((old[0], new[0]), (200, 200))
        self.assertEqual(rejected[0], 401)
        self.assertEqual(old[1].get('majors'), new[1].get('majors'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
