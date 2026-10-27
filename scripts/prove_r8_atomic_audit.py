#!/usr/bin/env python3
"""Independent R8 synthetic HTTP + SQLite atomic audit / rollback proof.

Only two loopback Python demo HTTP servers; NOT Flask/Firebase/production.
No real secrets, no internet, no root; all servers and SQLite files temporary.
"""
from __future__ import annotations
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.local_server import make_server
from backend.security_core import Principal

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/R8_SYNTHETIC_ATOMIC_AUDIT.json'
SOURCES=(
    'backend/demo_store.py', 'backend/local_server.py',
    'backend/security_core.py', 'scripts/prove_r8_atomic_audit.py',
    'tests/test_r8_atomic_audit.py', 'tests/test_r8_http_transactional_integrity.py',
)

def request(base, method, path, payload=None, token=None):
    headers={}
    data=None
    if payload is not None:
        headers['Content-Type']='application/json'
        data=json.dumps(payload).encode('utf-8')
    if token is not None:
        headers['Authorization']='Bearer '+token
    req=Request(base+path,method=method,data=data,headers=headers)
    try:
        res=urlopen(req,timeout=6)
    except HTTPError as err:
        res=err
    with res:
        raw=res.read()
        return res.status, (json.loads(raw) if raw and
            res.headers.get('Content-Type','').startswith('application/json') else raw.decode('utf-8'))

def run():
    checks={}
    with tempfile.TemporaryDirectory(prefix='coursesphere-r8-synthetic-') as tmp:
        path=str(Path(tmp)/'shared.db')
        key='r8-local-synthetic-only-'+'x'*40
        a=make_server('127.0.0.1',0,path,secret=key,instance='audit-a')
        b=make_server('127.0.0.1',0,path,secret=key,instance='audit-b')
        servers=(a,b)
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in servers]
        for t in threads: t.start()
        urls=[f'http://127.0.0.1:{s.server_address[1]}' for s in servers]
        store=a.RequestHandlerClass.context.store
        try:
            checks['two_live_replicas']=all(request(base,'GET','/api/health')[0]==200 for base in urls)
            code,login=request(urls[0],'POST','/api/demo/session',{'uid':'alice'})
            token=login.get('access_token') if code==200 and isinstance(login,dict) else None
            checks['token_works_across_replicas']=bool(token and request(urls[1],'GET','/api/courses',token=token)[0]==200)
            before=len(store.list_courses())
            status,item=request(urls[1],'POST','/api/courses',{'title':'Audit success'},token=token)
            events=store.list_events(Principal('admin','admin'))
            checks['successful_write_audited_exactly_once']=(status==201 and isinstance(item,dict)
                and len(store.list_courses())==before+1 and len(events)==1
                and events[0]['action']=='course.create' and events[0]['target']==str(item.get('id')))
            with store.connect() as db:
                db.execute("""CREATE TRIGGER injected_audit_error BEFORE INSERT ON audit_events
                           BEGIN SELECT RAISE(ABORT, 'private synthetic failure marker'); END""")
            before=store.list_courses()
            try:
                status,body=request(urls[0],'POST','/api/courses',{'title':'Must rollback'},token=token)
                checks['audit_failure_causes_http_500_without_detail']=status==500 and (
                    'private synthetic failure marker' not in json.dumps(body))
                checks['rollback_prevents_orphaned_write']=store.list_courses()==before
                checks['event_count_unchanged_on_failed_write']=len(store.list_events(Principal('admin','admin')))==1
            finally:
                with store.connect() as db: db.execute('DROP TRIGGER injected_audit_error')
            # Still healthy and writes succeed after simulated failure.
            status,_=request(urls[1],'POST','/api/courses',{'title':'Recovered'},token=token)
            checks['recovery_after_audit_failure']=status==201 and len(store.list_courses())==len(before)+1
            with store.connect() as db:
                try:
                    db.execute('DELETE FROM audit_events')
                except sqlite3.IntegrityError:
                    checks['append_only_trigger_rejects_delete']=True
                else:
                    checks['append_only_trigger_rejects_delete']=False
        finally:
            for server in servers: server.shutdown();server.server_close()
            for thread in threads: thread.join(timeout=3)
    return {
        'validated':bool(checks) and all(v is True for v in checks.values()),
        'scope':'synthetic demo: two real local Python HTTP servers and one SQLite; NOT Flask/Firebase/Docker',
        'version':'R8-derived-V19.9',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'checks':checks,
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SOURCES},
        'additional_acceptance_points':0,
    }

if __name__=='__main__':
    report=run()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))
    raise SystemExit(0 if report['validated'] else 1)
