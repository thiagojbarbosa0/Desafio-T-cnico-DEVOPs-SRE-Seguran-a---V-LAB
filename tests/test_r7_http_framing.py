"""R7 actual loopback HTTP server tests (not Flask/Docker)."""
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.local_server import make_server


class ActualHttpFramingR7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.server=make_server('127.0.0.1',0,str(Path(cls.tmp.name)/'database.sqlite3'),secret='A'*48,instance='R7-A')
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
        cls.tmp.cleanup()

    def get(self,path):
        request=Request(f'http://127.0.0.1:{self.port}{path}')
        try: response=urlopen(request,timeout=3)
        except HTTPError as exc: response=exc
        with response: return response.status,response.read().decode()

    def raw_request(self,data):
        with socket.create_connection(('127.0.0.1',self.port),timeout=4) as connection:
            connection.sendall(data)
            connection.shutdown(socket.SHUT_WR)
            response=bytearray()
            while True:
                part=connection.recv(65536)
                if not part: break
                response.extend(part)
        return response.decode('latin1')

    def test_plain_health(self):
        status,body=self.get('/api/health')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['mode'],'synthetic-demo')
    def test_transfer_encoding_chunked_rejected(self):
        response=self.raw_request(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\nContent-Type: application/json\r\n\r\n0\r\n\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_duplicate_content_length_rejected(self):
        response=self.raw_request(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\nContent-Length: 0\r\n\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_comma_combined_content_length_rejected(self):
        response=self.raw_request(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0, 0\r\n\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_absolute_form_rejected(self):
        response=self.raw_request(b'GET http://evil.example/api/health HTTP/1.1\r\nHost: localhost\r\n\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_scheme_relative_form_never_reaches_route(self):
        response=self.raw_request(b'GET //evil.example/api/health HTTP/1.1\r\nHost: localhost\r\n\r\n')
        # stdlib normalizes leading // before dispatch; the request is
        # still safely rejected as an unmatched path (404).
        self.assertIn(' 404 ',response.splitlines()[0])
    def test_duplicate_json_identity_rejected(self):
        body=b'{"uid":"student","uid":"admin"}'
        req=(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\n'
             b'Content-Type: application/json\r\nContent-Length: '
             + str(len(body)).encode() + b'\r\n\r\n' + body)
        self.assertIn(' 400 ',self.raw_request(req).splitlines()[0])
    def test_nonfinite_json_rejected(self):
        body=b'{"uid":NaN}'
        req=(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\n'
             b'Content-Type: application/json\r\nContent-Length: '
             + str(len(body)).encode() + b'\r\n\r\n' + body)
        self.assertIn(' 400 ',self.raw_request(req).splitlines()[0])
    def test_no_exception_details_in_error_log(self):
        with patch.object(self.server.RequestHandlerClass.context.store,'list_courses',side_effect=RuntimeError('SUPER-SECRET-DO-NOT-LOG')):
            with patch('backend.local_server.LOGGER.error') as logger:
                # Obtain a synthetic signed credential directly for this read-only test.
                token=self.server.RequestHandlerClass.context.tokens.issue('alice','instructor')
                request=Request(f'http://127.0.0.1:{self.port}/api/courses',headers={'Authorization':'Bearer '+token})
                try: urlopen(request,timeout=3)
                except HTTPError as exc:
                    self.assertEqual(exc.code,500)
                    self.assertNotIn('SUPER-SECRET',exc.read().decode())
                else: self.fail('Expected 500')
                self.assertTrue(logger.called)
                self.assertNotIn('SUPER-SECRET',str(logger.call_args))
