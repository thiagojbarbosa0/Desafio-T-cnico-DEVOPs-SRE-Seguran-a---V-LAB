"""R10: TCP slow-trickle resistance; synthetic loopback API, not Firebase."""
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from backend.local_server import (make_server, DEFAULT_REQUEST_READ_BUDGET,
                                  DeadlineSocketReader)
from backend.security_core import Principal


class R10AbsoluteDeadline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server = make_server('127.0.0.1', 0,
            str(Path(cls.tmp.name) / 'store.sqlite3'),
            secret='synthetic-r10-'+'X'*48, instance='r10-deadline',
            read_timeout=0.24, request_read_budget=0.46, max_active_clients=3)
        cls.port = cls.server.server_address[1]
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=3)
        cls.tmp.cleanup()

    def request(self, method='GET', path='/api/health', body=None, headers=None):
        conn=http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        try:
            conn.request(method,path,body=body,headers=headers or {})
            resp=conn.getresponse()
            return resp.status, resp.read()
        finally:
            conn.close()

    def trickle(self, prefix, drip=b'x', interval=0.075, max_time=1.35):
        start=time.monotonic()
        with socket.create_connection(('127.0.0.1', self.port),timeout=2) as sock:
            sock.settimeout(1.5)
            sock.sendall(prefix)
            while time.monotonic() - start < max_time:
                time.sleep(interval)
                try:
                    sock.sendall(drip)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break
            chunks=[]
            while True:
                try: part=sock.recv(65536)
                except (BrokenPipeError, ConnectionResetError, OSError): break
                if not part: break
                chunks.append(part)
        return time.monotonic()-start, b''.join(chunks)

    def test_default_budget_is_finite(self):
        self.assertGreater(DEFAULT_REQUEST_READ_BUDGET,0)
        self.assertLessEqual(DEFAULT_REQUEST_READ_BUDGET,120)

    def test_invalid_deadline_types_and_ranges_rejected(self):
        for value in (None,False,True,0,-5,0.01,120.01,float('nan'),float('inf'),'10',[],{}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                make_server('127.0.0.1',0,request_read_budget=value)

    def test_valid_budget_boundary(self):
        self.assertEqual(self.server.RequestHandlerClass.request_read_budget,0.46)

    def test_reader_refuses_expired_deadline_without_network_read(self):
        with socket.socket() as sock:
            reader=DeadlineSocketReader(sock,.1,time.monotonic()-1)
            with self.assertRaises(TimeoutError): reader.readinto(bytearray(8))
            reader.close()

    def test_reader_can_be_closed_without_closing_socket(self):
        with socket.socket() as sock:
            reader=DeadlineSocketReader(sock,.1,time.monotonic()+5)
            reader.close()
            self.assertNotEqual(sock.fileno(),-1)

    def test_slow_header_trickle_cannot_extend_handler_lifetime(self):
        elapsed,out=self.trickle(b'GET /api/health HTTP/1.1\r\nHost: lo')
        self.assertLess(elapsed,1.2)
        self.assertNotIn(b' 200 ',out)
        self.assertEqual(self.request()[0],200)

    def test_slow_body_trickle_expires_with_408(self):
        prefix=(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\n'
                b'Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{')
        elapsed,out=self.trickle(prefix,drip=b' ',interval=0.075)
        self.assertLess(elapsed,1.2)
        self.assertIn(b' 408 ',out.split(b'\r\n',1)[0])
        self.assertNotIn(b'access_token',out)

    def test_partial_authenticated_write_never_persists(self):
        ctx=self.server.RequestHandlerClass.context
        token=ctx.tokens.issue('alice','instructor')
        before=ctx.store.list_courses()
        events=ctx.store.list_events(Principal('admin','admin'))
        prefix=(b'POST /api/courses HTTP/1.1\r\nHost: localhost\r\n'
                b'Content-Type: application/json\r\nAuthorization: Bearer '+token.encode()+
                b'\r\nContent-Length: 200\r\n\r\n{')
        elapsed,out=self.trickle(prefix,drip=b' ',interval=0.075)
        self.assertIn(b' 408 ',out.split(b'\r\n',1)[0])
        self.assertEqual(ctx.store.list_courses(),before)
        self.assertEqual(ctx.store.list_events(Principal('admin','admin')),events)

    def test_valid_body_and_readiness_still_work(self):
        status,body=self.request('POST','/api/demo/session',b'{"uid":"alice"}',
                                 {'Content-Type':'application/json'})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['uid'],'alice')
        self.assertEqual(self.request('GET','/api/ready')[0],200)

    def test_capacity_recovers_after_deadline(self):
        # Repeated slow connections must release the same three handler slots.
        for _ in range(2):
            elapsed,_=self.trickle(b'GET /api/health HTTP/1.1\r\nHost: lo')
            self.assertLess(elapsed,1.2)
        self.assertEqual(self.request()[0],200)


if __name__=='__main__': unittest.main()
