"""R12: authenticated HTTP coverage of the original Flask routes, mock Firebase.

Real Flask/Werkzeug HTTP, but deliberately no live Firebase credentials.
"""
from __future__ import annotations
import json
import unittest
from unittest import mock
from urllib import error, request
from integration.test_original_http_stubbed import (
    HAS_FLASK, SOURCES, SyntheticFirebase, load_app, local_http,
)


@unittest.skipUnless(HAS_FLASK, 'Flask not installed; HTTP integration is UNVERIFIED')
class R12FlaskIngress(unittest.TestCase):
    def setUp(self):
        SyntheticFirebase.reset()
        self.app = load_app(SOURCES['after'], 'r12_original_flask_' + self._testMethodName)

    @staticmethod
    def call(origin, path, body, content_type='application/json'):
        headers={'Authorization':'Bearer SYNTHETIC_TOKEN','Content-Type':content_type}
        req=request.Request(origin+path, data=body, headers=headers, method='POST')
        try:response=request.urlopen(req,timeout=5)
        except error.HTTPError as exc:response=exc
        with response:
            return response.status, json.loads(response.read().decode())

    def test_profile_duplicate_keys_fail_before_quota_and_write(self):
        with mock.patch.object(SyntheticFirebase,'enforce_quota', wraps=SyntheticFirebase.enforce_quota) as debit:
            with local_http(self.app) as host:
                status,_=self.call(host,'/users/info', b'{"about":"ok","about":"evil"}')
        self.assertEqual(status,400);debit.assert_not_called()
        self.assertEqual(SyntheticFirebase.profiles,{})

    def test_profile_valid_json_still_succeeds(self):
        with local_http(self.app) as host:
            status,_=self.call(host,'/users/info',b'{"about":"safe"}')
        self.assertEqual(status,200)
        self.assertEqual(SyntheticFirebase.profiles['alice']['about'],'safe')

    def test_recommendation_nested_duplicate_keys_fail_closed(self):
        with local_http(self.app) as host:
            status,_=self.call(host,'/users/query',b'{"query":"computer science","extra":{"x":1,"x":2}}')
        self.assertEqual(status,400)

    def test_hash_rejects_nonfinite_without_quota(self):
        with mock.patch.object(SyntheticFirebase,'enforce_quota', wraps=SyntheticFirebase.enforce_quota) as debit:
            with local_http(self.app) as host:
                status,_=self.call(host,'/hash',b'{"a":NaN}')
        self.assertEqual(status,400);debit.assert_not_called()

    def test_chat_rejects_invalid_unicode_without_writing(self):
        with local_http(self.app) as host:
            status,_=self.call(host,'/chats/chat1/messages',b'{"messages":[{"sender":"user","content":"\\ud800"}]}')
        self.assertEqual(status,400)
        self.assertEqual(SyntheticFirebase.chats,{})

    def test_content_type_mismatch_415(self):
        with local_http(self.app) as host:
            status,_=self.call(host,'/users/info',b'{"about":"safe"}', 'text/plain')
        self.assertEqual(status,415)
        self.assertEqual(SyntheticFirebase.profiles,{})

    def test_floating_point_overflow_rejected(self):
        with local_http(self.app) as host:
            status,_=self.call(host,'/hash',b'{"score":1e9999}')
        self.assertEqual(status,400)

    def test_anonymous_invalid_request_never_consumes_quota(self):
        req=request.Request('http://invalid',data=b'{"x":1,"x":2}',method='POST')
        with mock.patch.object(SyntheticFirebase,'enforce_quota', wraps=SyntheticFirebase.enforce_quota) as debit:
            with local_http(self.app) as host:
                req=request.Request(host+'/users/info',data=b'{"x":1,"x":2}',
                                    headers={'Content-Type':'application/json'},method='POST')
                try:response=request.urlopen(req,timeout=5)
                except error.HTTPError as exc:response=exc
                with response:self.assertEqual(response.status,401)
        debit.assert_not_called()


if __name__ == '__main__':unittest.main()
