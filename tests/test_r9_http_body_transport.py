"""R9: actual TCP read-timeouts and framing regression, synthetic API only."""
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.local_server import make_server, DEFAULT_CLIENT_READ_TIMEOUT
from backend.security_core import Principal

HEADERS=(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\n'
         b'Content-Type: application/json\r\n')


class R9TransportHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.server=make_server('127.0.0.1',0,str(Path(cls.temp.name)/'db.sqlite3'),
                               secret='local-test-only-'+('X'*40),instance='r9-transport',read_timeout=0.25)
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2);cls.temp.cleanup()

    def raw(self, payload, shutdown=True, timeout=2):
        with socket.create_connection(('127.0.0.1',self.port),timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(payload)
            if shutdown: sock.shutdown(socket.SHUT_WR)
            chunks=[]
            while True:
                part=sock.recv(65536)
                if not part: break
                chunks.append(part)
            return b''.join(chunks)

    def request(self,method,path,data=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=2)
        try:
            conn.request(method,path,body=data,headers=headers or {})
            res=conn.getresponse()
            return res.status,res.read()
        finally: conn.close()

    def test_default_timeout_bounded(self):
        self.assertGreater(DEFAULT_CLIENT_READ_TIMEOUT,0)
        self.assertLessEqual(DEFAULT_CLIENT_READ_TIMEOUT,30)
    def test_valid_body_works(self):
        body=b'{"uid":"alice"}'
        status,payload=self.request('POST','/api/demo/session',body,{'Content-Type':'application/json'})
        self.assertEqual(status,200,payload)
        self.assertIn(b'access_token',payload)
    def test_truncated_but_valid_json_prefix_rejected(self):
        body=b'{"uid":"alice"}'
        packet=HEADERS+b'Content-Length: '+str(len(body)+4).encode()+b'\r\n\r\n'+body
        result=self.raw(packet)
        self.assertIn(b' 400 ',result.splitlines()[0])
        self.assertNotIn(b'access_token',result)
    def test_truncated_json_prefix_rejected(self):
        result=self.raw(HEADERS+b'Content-Length: 100\r\n\r\n{"uid":')
        self.assertIn(b' 400 ',result.splitlines()[0])
    def test_declared_zero_length_rejected(self):
        result=self.raw(HEADERS+b'Content-Length: 0\r\n\r\n')
        self.assertIn(b' 413 ',result.splitlines()[0])
    def test_declared_oversized_body_rejected_without_reading(self):
        result=self.raw(HEADERS+b'Content-Length: 32769\r\n\r\n')
        self.assertIn(b' 413 ',result.splitlines()[0])
    def test_timeout_partial_body_returns_408_and_closes(self):
        start=time.monotonic()
        result=self.raw(HEADERS+b'Content-Length: 20\r\n\r\n{"uid":',shutdown=False)
        self.assertIn(b' 408 ',result.splitlines()[0])
        self.assertLess(time.monotonic()-start,1.8)
        self.assertNotIn(b'access_token',result)
    def test_idle_headers_bounded(self):
        start=time.monotonic()
        with socket.create_connection(('127.0.0.1',self.port),timeout=2) as sock:
            sock.settimeout(2)
            sock.sendall(b'GET /api/health HTTP/1.1\r\nHost: ')
            out=sock.recv(8192)
        self.assertLess(time.monotonic()-start,1.8)
        self.assertNotIn(b' 200 ',out)
    def test_post_timeout_server_still_healthy(self):
        self.raw(HEADERS+b'Content-Length: 30\r\n\r\n{}',shutdown=False)
        self.assertEqual(self.request('GET','/api/health')[0],200)
    def test_no_audit_or_mutation_for_truncated_write(self):
        ctx=self.server.RequestHandlerClass.context
        token=ctx.tokens.issue('alice','instructor')
        before=ctx.store.list_courses()
        events=ctx.store.list_events(Principal('admin','admin'))
        body=b'{"title":"Must not persist"}'
        packet=(b'POST /api/courses HTTP/1.1\r\nHost: localhost\r\n'
                b'Content-Type: application/json\r\nAuthorization: Bearer '+token.encode()
                +b'\r\nContent-Length: '+str(len(body)+5).encode()+b'\r\n\r\n'+body)
        result=self.raw(packet)
        self.assertIn(b' 400 ',result.splitlines()[0])
        self.assertEqual(ctx.store.list_courses(),before)
        self.assertEqual(ctx.store.list_events(Principal('admin','admin')),events)
    def test_no_audit_or_mutation_for_timed_out_write(self):
        ctx=self.server.RequestHandlerClass.context
        token=ctx.tokens.issue('alice','instructor')
        before=ctx.store.list_courses()
        packet=(b'POST /api/courses HTTP/1.1\r\nHost: localhost\r\n'
                b'Content-Type: application/json\r\nAuthorization: Bearer '+token.encode()
                +b'\r\nContent-Length: 100\r\n\r\n{"title":')
        result=self.raw(packet,shutdown=False)
        self.assertIn(b' 408 ',result.splitlines()[0])
        self.assertEqual(ctx.store.list_courses(),before)
    def test_header_timeout_is_per_request(self):
        with socket.create_connection(('127.0.0.1',self.port),timeout=2) as sock:
            sock.settimeout(2)
            sock.sendall(b'GET /api/health HTTP/1.1\r\n')
            sock.recv(8192)
        self.assertEqual(self.request('GET','/api/ready')[0],200)
    def test_timeout_configuration_rejects_invalid_types_and_ranges(self):
        bad=[True,False,-1,0,0.01,31,float('inf'),float('nan'),'5',None]
        for value in bad:
            with self.subTest(value=value),self.assertRaises(ValueError):
                make_server('127.0.0.1',0,read_timeout=value)
    def test_valid_read_timeout_boundaries(self):
        self.assertEqual(self.server.RequestHandlerClass.read_timeout,0.25)
        self.assertFalse(self.server.RequestHandlerClass.context.instance=='')
    def test_error_response_omits_request_body(self):
        packet=HEADERS+b'Content-Length: 99\r\n\r\n{"uid":"admin"}'
        result=self.raw(packet)
        self.assertIn(b' 400 ',result.splitlines()[0])
        self.assertNotIn(b'"uid":"admin"',result)

if __name__=='__main__': unittest.main()

class R9BoundedClients(unittest.TestCase):
    def test_client_limit_rejects_boolean_and_invalid_values(self):
        for value in (True,False,0,-1,513,'2',None,1.25):
            with self.subTest(value=value),self.assertRaises(ValueError):
                make_server(max_active_clients=value)

    def test_default_max_clients_is_bounded(self):
        from backend.local_server import DEFAULT_MAX_ACTIVE_CLIENTS
        self.assertGreater(DEFAULT_MAX_ACTIVE_CLIENTS,0)
        self.assertLessEqual(DEFAULT_MAX_ACTIVE_CLIENTS,512)

    def test_excess_client_dropped_and_capacity_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            server=make_server('127.0.0.1',0,str(Path(tmp)/'limited.db'),
                               secret='synthetic-only-'+'x'*40,instance='r9-capacity',
                               read_timeout=0.55,max_active_clients=2)
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            clients=[]
            try:
                port=server.server_address[1]
                for _ in range(2):
                    client=socket.create_connection(('127.0.0.1',port),timeout=2)
                    client.settimeout(2)
                    client.sendall(b'GET /api/health HTTP/1.1\r\nHost: ')
                    clients.append(client)
                deadline=time.monotonic()+1
                while server._handler_slots._value!=0 and time.monotonic()<deadline:
                    time.sleep(.005)
                self.assertEqual(server._handler_slots._value,0)
                with socket.create_connection(('127.0.0.1',port),timeout=2) as other:
                    other.settimeout(1)
                    other.sendall(b'GET /api/health HTTP/1.1\r\nHost: localhost\r\n\r\n')
                    try: response=other.recv(8192)
                    except ConnectionResetError: response=b''
                    self.assertNotIn(b' 200 ',response)
                for client in clients:
                    try: client.recv(8192)
                    except (ConnectionResetError,BrokenPipeError,TimeoutError): pass
                deadline=time.monotonic()+2
                while server._handler_slots._value!=2 and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertEqual(server._handler_slots._value,2)
                connection=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
                try:
                    connection.request('GET','/api/health')
                    res=connection.getresponse()
                    self.assertEqual(res.status,200)
                    res.read()
                finally: connection.close()
            finally:
                for client in clients: client.close()
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_capacity_slot_returned_after_rejected_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            server=make_server('127.0.0.1',0,str(Path(tmp)/'single.db'),
                               secret='synthetic-only-'+'x'*40,instance='r9-single',
                               read_timeout=0.4,max_active_clients=1)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                port=server.server_address[1]
                with socket.create_connection(('127.0.0.1',port),timeout=2) as sock:
                    sock.sendall(HEADERS+b'Content-Length: 100\r\n\r\n{}')
                    sock.shutdown(socket.SHUT_WR)
                    response=sock.recv(8192)
                    self.assertIn(b' 400 ',response)
                deadline=time.monotonic()+2
                while server._handler_slots._value!=1 and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertEqual(server._handler_slots._value,1)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=2)
