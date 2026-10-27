#!/usr/bin/env python3
"""Controlled localhost replica-loss experiment. NOT an Nginx/Docker test.

Uses no third-party modules, external network, live accounts or services.
"""
from __future__ import annotations
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.local_server import make_server


def call(port, path, method='GET', body=None, token=None):
    headers={}
    if body is not None:
        headers['Content-Type']='application/json'
    if token:
        headers['Authorization']='Bearer '+token
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=3) as response:
        payload=json.loads(response.read())
        return response.status,payload,response.headers.get('X-CourseSphere-Instance')


def run_experiment():
    with tempfile.TemporaryDirectory(prefix='coursesphere-resilience-') as tmp:
        db=Path(tmp)/'shared.sqlite3'
        secret='SYNTHETIC_TEST_SECRET_'*3
        a=make_server('127.0.0.1',0,db_path=str(db),secret=secret,instance='replica-a')
        b=make_server('127.0.0.1',0,db_path=str(db),secret=secret,instance='replica-b')
        ths=[threading.Thread(target=s.serve_forever,daemon=True) for s in (a,b)]
        for thread in ths:thread.start()
        pa,pb=a.server_port,b.server_port
        try:
            sa,ja,ia=call(pa,'/api/ready')
            sb,jb,ib=call(pb,'/api/ready')
            status,session,issuer=call(pa,'/api/demo/session','POST',{'uid':'alice'})
            assert status==200 and issuer=='replica-a'
            token=session['access_token']
            cross_status,courses,receiver=call(pb,'/api/courses',token=token)
            assert sa==200 and sb==200 and ia!=ib and cross_status==200
            assert isinstance(courses['courses'],list) and receiver=='replica-b'
            a.shutdown(); a.server_close(); ths[0].join(timeout=4)
            survivor_status,_,survivor=call(pb,'/api/ready')
            assert survivor_status==200 and survivor=='replica-b'
            loss_confirmed=False
            try:
                call(pa,'/api/ready')
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                loss_confirmed=True
            assert loss_confirmed
            result={'scope':'isolated stdlib HTTP servers on loopback, NOT nginx failover',
                    'time_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'replicas_pre_failure':[{'instance':ia,'ready_status':sa},{'instance':ib,'ready_status':sb}],
                    'shared_authentication':{'token_issued_by':'replica-a','validated_by':receiver,'status':cross_status},
                    'failure':{'stopped':'replica-a','confirmed_unreachable':loss_confirmed,
                               'survivor':'replica-b','survivor_ready_status':survivor_status},
                    'result':'PASS','caveat':'No automatic traffic rerouting demonstrated; Nginx + Docker verification pending.'}
        finally:
            for srv,thr in [(a,ths[0]),(b,ths[1])]:
                try: srv.shutdown();srv.server_close()
                except Exception: pass
                thr.join(timeout=4)
    return result

if __name__=='__main__':
    result=run_experiment()
    output=ROOT/'evidence/generated/LOCAL_REPLICA_FAILURE.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Resilience experiment: two distinct replicas ready, cross-replica auth accepted, surviving replica healthy after peer stop. PASS')
