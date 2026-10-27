"""R8 HTTP regression with a real loopback stdlib server (not Flask/Firebase)."""
import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from backend.local_server import ServerContext, make_server
from backend.security_core import SecurityError


class R8ActualHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server=make_server('127.0.0.1',0,str(Path(cls.tmp.name)/'data.db'),secret='Z'*50,instance='r8-a')
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        client=http.client.HTTPConnection('127.0.0.1',self.port,timeout=4)
        try:
            client.request(method,path,body=body,headers=headers or {})
            response=client.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            client.close()
    def raw(self,headers,b='{}',method='POST'):
        import socket
        raw=(f'{method} /api/demo/session HTTP/1.1\r\nHost: localhost\r\n'+headers+'\r\n').encode()+b.encode()
        with socket.create_connection(('127.0.0.1',self.port),timeout=4) as client:
            client.sendall(raw)
            client.shutdown(socket.SHUT_WR)
            return client.recv(8192).decode('latin1')
    def token(self,uid):
        payload=json.dumps({'uid':uid}).encode()
        status,body,_=self.request('POST','/api/demo/session',payload,{'Content-Type':'application/json'})
        self.assertEqual(status,200)
        return json.loads(body)['access_token']
    def test_repeated_authorization_denied_before_authentication(self):
        response=self.raw('Authorization: Bearer x\r\nAuthorization: Bearer y\r\nContent-Type: application/json\r\nContent-Length: 2\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_repeated_content_type_denied(self):
        response=self.raw('Content-Type: application/json\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_duplicate_host_denied(self):
        response=self.raw('Host: suspicious.example\r\nContent-Type: application/json\r\nContent-Length: 2\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_missing_http11_host_denied(self):
        # No Host; deliberately omit the default Host helper.
        import socket
        with socket.create_connection(('127.0.0.1',self.port),timeout=3) as client:
            client.sendall(b'GET /api/health HTTP/1.1\r\n\r\n')
            response=client.recv(8192).decode('latin1')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_signed_content_length_rejected(self):
        response=self.raw('Content-Type: application/json\r\nContent-Length: +2\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_surrounding_whitespace_length_rejected(self):
        response=self.raw('Content-Type: application/json\r\nContent-Length:  2 \r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_nondigit_content_length_rejected(self):
        response=self.raw('Content-Type: application/json\r\nContent-Length: 2x\r\n')
        self.assertIn(' 400 ',response.splitlines()[0])
    def test_readiness_returns_generic_503_on_database_failure(self):
        from contextlib import contextmanager
        ctx=self.server.RequestHandlerClass.context
        original=ctx.store.connect
        @contextmanager
        def broken():
            raise sqlite3.OperationalError('secret connection string was not reachable')
            yield
        ctx.store.connect=broken
        try:
            code,body,_=self.request('GET','/api/ready')
            self.assertEqual(code,503)
            self.assertNotIn(b'secret connection string',body)
            self.assertEqual(self.request('GET','/api/health')[0],200)
        finally:
            ctx.store.connect=original
        self.assertEqual(self.request('GET','/api/ready')[0],200)

    def test_ready_endpoint_succeeds_when_db_is_healthy(self):
        code,body,_=self.request('GET','/api/ready')
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)['status'],'ok')

    def test_normal_health_kept(self):
        status,body,headers=self.request('GET','/api/health')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['status'],'ok')
        self.assertEqual(headers['X-CourseSphere-Instance'],'r8-a')
    def test_real_http_create_audits_once(self):
        token=self.token('alice')
        before=len(self.server.RequestHandlerClass.context.store.list_events(
            self.server.RequestHandlerClass.context.tokens.verify(self.token('admin'))))
        data=json.dumps({'title':'HTTP atomic audit'}).encode()
        status,body,_=self.request('POST','/api/courses',data,{
            'Content-Type':'application/json','Authorization':'Bearer '+token})
        self.assertEqual(status,201,body)
        store=self.server.RequestHandlerClass.context.store
        admin=self.server.RequestHandlerClass.context.tokens.verify(self.token('admin'))
        self.assertEqual(len(store.list_events(admin)),before+1)
    def test_real_http_mutation_rollback_on_audit_failure(self):
        store=self.server.RequestHandlerClass.context.store
        before=store.list_courses()
        with store.connect() as db:
            db.execute('''CREATE TRIGGER deny_audit_http_r8 BEFORE INSERT ON audit_events
                       BEGIN SELECT RAISE(ABORT, 'test failure - should not leak'); END''')
        try:
            data=json.dumps({'title':'Should never persist'}).encode()
            status,body,_=self.request('POST','/api/courses',data,{
                'Content-Type':'application/json',
                'Authorization':'Bearer '+self.server.RequestHandlerClass.context.tokens.issue('alice','instructor')})
            self.assertEqual(status,500)
            self.assertNotIn(b'test failure',body)
            self.assertEqual(store.list_courses(),before)
        finally:
            with store.connect() as db: db.execute('DROP TRIGGER deny_audit_http_r8')


class ConfigValidationR8(unittest.TestCase):
    def test_instance_label_injection_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for value in ('api-a"} 10\nother_metric 1','api a','../x','', 'a'*65):
                with self.subTest(value=value):
                    if not value:  # empty explicit value falls back to safe env/default
                        continue
                    with self.assertRaises(SecurityError):
                        ServerContext(path=str(Path(tmp)/'test.db'),secret='x'*50,instance=value)
    def test_valid_metrics_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=ServerContext(path=str(Path(tmp)/'test.db'),secret='x'*50,instance='api-b_42')
            self.assertIn('instance="api-b_42"',ctx.metrics.render(ctx.instance) if ctx.metrics.counts else
                          (ctx.metrics.observe('GET','/api/health',200,0.01) or ctx.metrics.render(ctx.instance)))


if __name__ == '__main__': unittest.main()
