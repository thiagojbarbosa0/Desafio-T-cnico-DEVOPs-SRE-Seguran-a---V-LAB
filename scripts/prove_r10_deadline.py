#!/usr/bin/env python3
"""Independent loopback TCP slow-trickle proof, zero acceptance points."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
from urllib.request import urlopen

from backend.local_server import make_server
from backend.security_core import Principal

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/R10_SYNTHETIC_ABSOLUTE_DEADLINE.json'
SOURCES=(
    'backend/local_server.py','backend/security_core.py',
    'backend/demo_store.py',
    'scripts/prove_r10_deadline.py','scripts/release_gate_r10.py',
    'tests/test_r10_absolute_deadline.py','tests/test_r10_release_gate.py',
    '.github/workflows/ci.yml',
)


def drip_tcp(port, prefix, step=.075):
    start=time.monotonic()
    with socket.create_connection(('127.0.0.1',port),timeout=3) as sock:
        sock.settimeout(2)
        sock.sendall(prefix)
        while time.monotonic()-start<1.5:
            time.sleep(step)
            try: sock.sendall(b' ')
            except OSError: break
        response=b''
        while True:
            try: part=sock.recv(65536)
            except OSError: break
            if not part: break
            response+=part
            if len(response)>65536: raise ValueError('Unexpected response size')
    elapsed=time.monotonic()-start
    if b'\r\n' not in response: status=None
    else:
        try: status=int(response.split(b'\r\n',1)[0].split()[1])
        except (IndexError,ValueError): status=None
    return elapsed,status,response


def run():
    checks={}
    with tempfile.TemporaryDirectory(prefix='coursesphere-r10-local-') as tmp:
        shared=str(Path(tmp)/'db.sqlite3')
        secret='synthetic-r10-proof-'+'X'*44
        a=make_server('127.0.0.1',0,shared,secret=secret,instance='absolute-a',
                      read_timeout=.25,request_read_budget=.49,max_active_clients=2)
        b=make_server('127.0.0.1',0,shared,secret=secret,instance='absolute-b',
                      read_timeout=.25,request_read_budget=.49,max_active_clients=2)
        servers=(a,b)
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in servers]
        for t in threads:t.start()
        try:
            ports=[s.server_address[1] for s in servers]
            checks['two_replicas_alive']=all(
                json.loads(urlopen(f'http://127.0.0.1:{port}/api/health',timeout=2).read())['status']=='ok'
                for port in ports)
            started=time.monotonic()
            elapsed,code,response=drip_tcp(ports[0],b'GET /api/health HTTP/1.1\r\nHost: lo')
            checks['trickling_headers_terminated']=elapsed<1.3 and code!=200
            pre=(b'POST /api/demo/session HTTP/1.1\r\nHost: localhost\r\n'
                 b'Content-Type: application/json\r\nContent-Length: 200\r\n\r\n{')
            elapsed,code,response=drip_tcp(ports[1],pre)
            checks['trickling_body_returns_408']=elapsed<1.3 and code==408 and b'access_token' not in response
            ctx=a.RequestHandlerClass.context
            token=ctx.tokens.issue('alice','instructor')
            before_courses=ctx.store.list_courses()
            before_events=ctx.store.list_events(Principal('admin','admin'))
            pre=(b'POST /api/courses HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n'
                 b'Authorization: Bearer '+token.encode()+b'\r\nContent-Length: 200\r\n\r\n{')
            elapsed,code,response=drip_tcp(ports[0],pre)
            checks['authenticated_slow_write_denied']=elapsed<1.3 and code==408
            checks['no_orphan_mutation_or_audit']=(ctx.store.list_courses()==before_courses
                and ctx.store.list_events(Principal('admin','admin'))==before_events)
            checks['both_replicas_recovered']=all(
                json.loads(urlopen(f'http://127.0.0.1:{port}/api/ready',timeout=2).read())['status']=='ok'
                for port in ports)
            checks['shared_store_unchanged']=b.RequestHandlerClass.context.store.list_courses()==before_courses
        finally:
            for server in servers: server.shutdown();server.server_close()
            for t in threads:t.join(timeout=3)
    return {'validated':bool(checks) and all(checks.values()),
            'version':'R10-derived-V19.9',
            'scope':'two real loopback Python HTTP servers + shared SQLite; not Flask/Firebase/Docker',
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'checks':checks,
            'source_sha256':{rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in SOURCES},
            'additional_acceptance_points':0}

if __name__=='__main__':
    result=run()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'validated':result['validated'],'checks':result['checks']},indent=2))
    raise SystemExit(0 if result['validated'] else 1)
