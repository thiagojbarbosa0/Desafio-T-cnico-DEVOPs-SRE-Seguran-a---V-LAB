"""Real Flask+CORS WSGI contract; Firebase/QueryManager stay synthetic.

Run only against loopback/synthetic adapters. Unlike the offline tests, this
imports actual Flask and flask-cors and inspects real response headers.
"""
from __future__ import annotations
import os
import unittest
from unittest import mock
from integration.test_original_http_stubbed import HAS_FLASK, load_app, SOURCES


@unittest.skipUnless(HAS_FLASK, 'Flask and Flask-Cors are required (not executed)')
class CorsWSGIIntegration(unittest.TestCase):
    def patched_app(self, origins):
        with mock.patch.dict(os.environ, {'ALLOWED_ORIGINS': origins}):
            return load_app(SOURCES['after'], 'cors_v19_6_' + str(abs(hash(origins))))

    def test_local_react_preflight(self):
        app = self.patched_app('http://localhost:5173')
        response = app.test_client().options('/users/info', headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'http://localhost:5173')

    def test_untrusted_origin_does_not_get_access_header(self):
        response = self.patched_app('https://courses.example.org').test_client().get(
            '/health', headers={'Origin': 'https://attacker.invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get('Access-Control-Allow-Origin'))

    def test_explicit_https_origin(self):
        response = self.patched_app('https://courses.example.org').test_client().get(
            '/health', headers={'Origin': 'https://courses.example.org'})
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'https://courses.example.org')

    def test_wildcard_cannot_start_server(self):
        with self.assertRaises(ValueError):
            self.patched_app('*')

    def test_insecure_remote_http_cannot_start_server(self):
        with self.assertRaises(ValueError):
            self.patched_app('http://courses.example.org')
