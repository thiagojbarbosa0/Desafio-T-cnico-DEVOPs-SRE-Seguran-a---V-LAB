#!/usr/bin/env python3
"""Read-only localhost diagnostic for the ORIGINAL CourseSphere gateway.

Checks liveness, readiness, private metrics, and token-in-URL rejection. This
is NOT a Docker attestation, quota test, or Firebase Emulator authorization
proof; never award acceptance points solely from this JSON report.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
SOURCE_FILES=('backend/endpoints.py','backend/readiness.py','backend/firebase.py',
              'ops/nginx/gateway.official.conf','scripts/probe_official_local_runtime_r4.py')


def get_local(port: int, path: str) -> tuple[int,bytes]:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('port must be 1024..65535')
    if path not in ('/health','/ready','/metrics','/ready?id_token=SYNTHETIC_ONLY'):
        raise ValueError('probe path not allowlisted')
    # Fixed loopback address, fixed path; never forward hostnames, tokens or
    # user-provided URL strings. Exceptions are sanitized before reporting.
    req=Request(f'http://127.0.0.1:{port}{path}',headers={'Accept':'application/json'})
    try:
        with urlopen(req,timeout=3) as response:
            return response.status,response.read(8193)
    except HTTPError as response:
        with response:
            return response.code,response.read(8193)


def inspect(*,port: int=8081, fetch=get_local) -> dict:
    checks={}
    state='unknown'
    def request_status(path):
        try:
            return fetch(port,path)
        except (HTTPError,URLError,OSError,TimeoutError,ValueError) as exc:
            checks['transport']='unavailable'
            return None,b''

    health_status, health_body=request_status('/health')
    try:
        body=json.loads(health_body) if len(health_body)<=8192 else None
    except (ValueError,UnicodeError):
        body=None
    checks['gateway_liveness']='pass' if (health_status==200 and isinstance(body,dict) and
        body.get('status')=='ok' and body.get('service')=='coursesphere-api') else 'fail'
    ready_status, ready_body=request_status('/ready')
    try:
        ready_json=json.loads(ready_body) if len(ready_body)<=8192 else None
    except (ValueError,UnicodeError):
        ready_json=None
    if isinstance(ready_json,dict) and ready_json.get('service')=='coursesphere-api':
        if ready_status==200 and ready_json.get('status')=='ready':
            state='ready'
        elif ready_status==503 and ready_json.get('status')=='unavailable':
            state='degraded'
    checks['dependency_readiness_contract']='pass' if state in ('ready','degraded') else 'fail'
    metrics_status,_=request_status('/metrics')
    checks['private_metrics_at_gateway']='pass' if metrics_status==403 else 'fail'
    token_status,body=request_status('/ready?id_token=SYNTHETIC_ONLY')
    checks['reject_query_token']='pass' if token_status==401 and b'SYNTHETIC_ONLY' not in body else 'fail'
    report={
        'version':'R4-on-V19.9-derived','generated_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Read-only localhost gateway smoke test: no Docker source attestation, Firebase/RTDB proofs, or acceptance points',
        'runtime_attestation':False,'acceptance_credit':0,'readiness':state,
        'checks':checks,'checks_passed':all(x=='pass' for x in checks.values()),
        'source_sha256':{source:hashlib.sha256((ROOT/source).read_bytes()).hexdigest() for source in SOURCE_FILES},
    }
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8081)
    p.add_argument('--output',type=Path,default=ROOT/'evidence/runtime/OFFICIAL_LOCAL_PROBE_R4.json')
    p.add_argument('--require-ready',action='store_true',help='also fail when Firebase-backed readiness reports unavailable')
    a=p.parse_args(argv)
    try:
        report=inspect(port=a.port)
    except (OSError,ValueError) as exc:
        report={'checks_passed':False,'runtime_attestation':False,'acceptance_credit':0,
                'error_type':type(exc).__name__}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if (report['checks_passed'] and (not a.require_ready or report['readiness']=='ready')) else 1

if __name__=='__main__':sys.exit(main())
