#!/usr/bin/env python3
"""Independent R9 local TCP evidence (synthetic only; no Flask/Firebase/Docker)."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import socket
import tempfile
import threading
import time
from urllib.request import urlopen

from backend.local_server import make_server
from backend.security_core import Principal

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/R9_SYNTHETIC_HTTP_TRANSPORT.json'
SOURCES=(
    'backend/local_server.py','backend/security_core.py',
    'backend/demo_store.py','scripts/prove_r9_transport.py',
    'tests/test_r9_http_body_transport.py',
    'tests/test_r9_release_gate.py', 'scripts/release_gate_r9.py',
    '.github/workflows/ci.yml',
)


def raw_http(port, data, half_close=True):
    with socket.create_connection(('127.0.0.1',port),timeout=3) as sock:
        sock.settimeout(3)
        sock.sendall(data)
        if half_close: sock.shutdown(socket.SHUT_WR)
        result=b''
        while True:
            part=sock.recv(65536)
            if not part: break
            result+=part
            if len(result)>65536: raise ValueError('Response exceeded local demo bounds')
        return result


def status(response):
    return int(response.split(b'\r\n',1)[0].split()[1])


def run():
    checks={}
    with tempfile.TemporaryDirectory(prefix='coursesphere-r9-local-only-') as tmp:
        db=str(Path(tmp)/'shared.sqlite3')
        secret='r9-local-synthetic-'+'x'*40
        a=make_server('127.0.0.1',0,db,secret=secret,instance='transport-a',read_timeout=0.4)
        b=make_server('127.0.0.1',0,db,secret=secret,instance='transport-b',read_timeout=0.4)
        servers=(a,b)
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in servers]
        for thread in threads: thread.start()
        ports=[s.server_address[1] for s in servers]
        try:
            checks['both_replicas_live']=all(
                json.loads(urlopen(f'http://127.0.0.1:{port}/api/health',timeout=3).read())['status']=='ok'
                for port in ports)
            pre=b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n'
            complete=b'{"uid":"alice"}'
            resp=raw_http(ports[0],pre+b'Content-Length: '+str(len(complete)+4).encode()+b'\r\n\r\n'+complete)
            checks['valid_json_truncated_by_cl_rejected']=status(resp)==400 and b'access_token' not in resp
            resp=raw_http(ports[1],pre+b'Content-Length: 32\r\n\r\n'+complete,False)
            checks['slow_body_times_out_408']=status(resp)==408 and b'access_token' not in resp
            resp=raw_http(ports[0],pre+b'Content-Length: 32769\r\n\r\n')
            checks['oversize_declared_rejected']=status(resp)==413
            ctx=a.RequestHandlerClass.context
            token=ctx.tokens.issue('alice','instructor')
            before=ctx.store.list_courses()
            events=ctx.store.list_events(Principal('admin','admin'))
            item=b'{"title":"No phantom changes"}'
            raw=(b'POST /api/courses HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n'
                 b'Authorization: Bearer '+token.encode('ascii')+b'\r\nContent-Length: '
                 +str(len(item)+3).encode()+b'\r\n\r\n'+item)
            checks['truncated_authenticated_write_rejected']=status(raw_http(ports[1],raw))==400
            checks['no_mutation_or_success_audit']=ctx.store.list_courses()==before and ctx.store.list_events(Principal('admin','admin'))==events
            resp=raw_http(ports[0],pre+b'Content-Length: '+str(len(complete)).encode()+b'\r\n\r\n'+complete)
            checks['valid_request_still_accepted']=status(resp)==200 and b'access_token' in resp
            checks['readiness_after_timeout']=all(
                json.loads(urlopen(f'http://127.0.0.1:{port}/api/ready',timeout=3).read())['status']=='ok'
                for port in ports)
            # A third, intentionally one-slot server demonstrates actual bounded
            # concurrency and recovery without exposing a port beyond loopback.
            limited=make_server('127.0.0.1',0,db,secret=secret,instance='transport-limited',
                                read_timeout=0.6,max_active_clients=1)
            limited_thread=threading.Thread(target=limited.serve_forever,daemon=True)
            limited_thread.start()
            try:
                limited_port=limited.server_address[1]
                with socket.create_connection(('127.0.0.1',limited_port),timeout=3) as idle:
                    idle.settimeout(3)
                    idle.sendall(b'GET /api/health HTTP/1.1\r\nHost: ')
                    deadline=time.monotonic()+1.5
                    while limited._handler_slots._value!=0 and time.monotonic()<deadline:
                        time.sleep(.005)
                    occupied=limited._handler_slots._value==0
                    with socket.create_connection(('127.0.0.1',limited_port),timeout=3) as excess:
                        excess.settimeout(3)
                        excess.sendall(b'GET /api/health HTTP/1.1\r\nHost: localhost\r\n\r\n')
                        try: response=excess.recv(8192)
                        except ConnectionResetError: response=b''
                    checks['bounded_active_handlers']=occupied and b' 200 ' not in response
                    try: idle.recv(8192)
                    except (ConnectionResetError,TimeoutError): pass
                deadline=time.monotonic()+2
                while limited._handler_slots._value!=1 and time.monotonic()<deadline:
                    time.sleep(.01)
                checks['capacity_recovers_after_idle_disconnect']=(limited._handler_slots._value==1
                    and json.loads(urlopen(f'http://127.0.0.1:{limited_port}/api/health',timeout=3).read())['status']=='ok')
            finally:
                limited.shutdown();limited.server_close();limited_thread.join(timeout=3)
        finally:
            for s in servers: s.shutdown();s.server_close()
            for t in threads: t.join(timeout=3)
    return {
        'validated':bool(checks) and all(checks.values()),
        'version':'R9-derived-V19.9',
        'scope':'2 real loopback Python HTTP servers, shared temporary SQLite; NOT Flask/Firebase/Docker',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'checks':checks,
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        'additional_acceptance_points':0,
    }

if __name__=='__main__':
    report=run()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'validated':report['validated'],'checks':report['checks']},indent=2))
    raise SystemExit(0 if report['validated'] else 1)
