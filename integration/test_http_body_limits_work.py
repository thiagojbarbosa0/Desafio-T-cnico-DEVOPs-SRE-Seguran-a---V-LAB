"""Regression for real Flask's 413 exception being swallowed by route handlers."""
import unittest
from integration.test_original_http_stubbed import (
    HAS_FLASK, SOURCES, SyntheticFirebase, load_app, local_http, http_call,
)

@unittest.skipUnless(HAS_FLASK, 'Real Flask required')
class BodyLimitHTTP(unittest.TestCase):
    def test_oversized_authenticated_requests_preserve_413(self):
        app = load_app(SOURCES['after'], 'work_body_limits')
        SyntheticFirebase.reset()
        with local_http(app) as base:
            for path in ('/users/info', '/users/query', '/hash', '/chats/demo/messages'):
                with self.subTest(path=path):
                    status, body, headers = http_call(base, path, 'POST',
                        {'query': 'x' * 40000}, token='SYNTHETIC_TOKEN')
                    self.assertEqual(status, 413)
                    self.assertEqual(body, {'error': 'Request body too large'})
                    self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(SyntheticFirebase.profiles, {})
        self.assertEqual(SyntheticFirebase.chats, {})

if __name__ == '__main__':
    unittest.main(verbosity=2)
