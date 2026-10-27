"""Real Flask HTTP semantics for R11; Firebase adapter is synthetic.

Only GitHub CI/Fedora with Flask+Flask-Cors can execute these HTTP checks.
"""
from __future__ import annotations
import os
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from integration.test_original_http_stubbed import HAS_FLASK, SOURCES, load_app, local_http, http_call


@unittest.skipUnless(HAS_FLASK, 'Flask absent; no HTTP proof')
class R11FlaskReplicaHeader(unittest.TestCase):
    def setUp(self):
        self.app = load_app(SOURCES['after'], 'coursesphere_r11_flask_' + self._testMethodName)

    def test_replica_a_header_on_success(self):
        with patch.dict(os.environ, {'COURSESPHERE_REPLICA_NAME':'official_api_a'}):
            with local_http(self.app) as host:
                status, data, headers = http_call(host, '/health')
        self.assertEqual(status,200)
        self.assertEqual(headers['X-CourseSphere-Replica'],'official_api_a')

    def test_replica_b_header_on_auth_denial(self):
        with patch.dict(os.environ, {'COURSESPHERE_REPLICA_NAME':'official_api_b'}):
            with local_http(self.app) as host:
                status, data, headers = http_call(host, '/users/info')
        self.assertEqual(status,401)
        self.assertEqual(headers['X-CourseSphere-Replica'],'official_api_b')

    def test_spoofed_client_replica_label_ignored(self):
        with patch.dict(os.environ, {'COURSESPHERE_REPLICA_NAME':'official_api_a'}):
            with local_http(self.app) as host:
                req = Request(host+'/health', headers={'X-CourseSphere-Replica':'official_api_b'})
                with urlopen(req,timeout=5) as response:
                    label=response.headers['X-CourseSphere-Replica']
        self.assertEqual(label,'official_api_a')

    def test_unknown_or_high_cardinality_label_not_exposed(self):
        with patch.dict(os.environ, {'COURSESPHERE_REPLICA_NAME':'attacker-provided-user-id'}):
            with local_http(self.app) as host:
                _,_,headers=http_call(host,'/health')
        self.assertEqual(headers['X-CourseSphere-Replica'],'unknown')


if __name__=='__main__':unittest.main()
