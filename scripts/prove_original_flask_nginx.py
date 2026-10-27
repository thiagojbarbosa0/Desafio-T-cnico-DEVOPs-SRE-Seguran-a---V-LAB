#!/usr/bin/env python3
"""Nginx/Flask integration: original patched routes behind two LOCAL replicas.

Unlike the independent demo proof, this exercises the actual patched Flask
endpoints. Firebase and recommendation services remain mocked, as explicitly
recorded in the generated artifact. No external service calls, public bind or
upstream credentials are permitted. Requires Flask, Flask-Cors and native nginx.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/NGINX_ORIGINAL_FLASK_STUBBED_V19.json'


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def http(url, token=None):
    hdr={'Authorization': 'Bearer '+token} if token else {}
    req=urllib.request.Request(url,headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, dict(response.headers), response.read(256)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read(256)


def wait_ready(url, proc, duration=12):
    deadline=time.monotonic()+duration
    while time.monotonic()<deadline:
        if proc.poll() is not None:
            raise RuntimeError('Service exited before readiness')
        try:
            if http(url)[0]==200:
                return
        except OSError:
            pass
        time.sleep(.12)
    raise RuntimeError('Service not ready in time')


def main():
    result={
        'scope':'real patched Flask routes + real native Nginx, fake Firebase/QueryManager adapters',
        'validated':False,
        'tests':{},
        'source_sha256':{name:sha(location) for name,location in {
            'endpoints':'backend/endpoints.py',
            'cors_policy':'backend/cors_policy.py',
            'harness':'integration/test_original_http_stubbed.py',
            'worker':'scripts/flask_replica_stub_worker.py',
            'nginx':'ops/nginx/gateway.conf',
            'nginx_main':'ops/nginx/nginx.conf',
            'proof':'scripts/prove_original_flask_nginx.py',
        }.items()},
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if not which('nginx'):
        result['error']='Native Nginx is unavailable (not tested)'
        OUT.write_text(json.dumps(result,indent=2)+'\n')
        return 2
    try:
        import flask, flask_cors  # noqa: F401
    except ImportError:
        result['error']='Flask/Flask-Cors unavailable (not tested)'
        OUT.write_text(json.dumps(result,indent=2)+'\n')
        return 2
    ports=[free_port() for _ in range(3)]
    workers=[]
    with tempfile.TemporaryDirectory(prefix='coursesphere-original-flask-nginx-') as tmp:
        tmp=Path(tmp)
        (tmp/'logs').mkdir()
        for i, name in enumerate(('flask-a','flask-b')):
            env={**os.environ, 'COURSESPHERE_TEST_PORT':str(ports[i]),
                 'COURSESPHERE_TEST_INSTANCE':name,
                 'COURSESPHERE_USE_FIREBASE_EMULATORS':'0'}
            env.pop('OPENAI_API_KEY', None)
            env.pop('FIREBASE_CREDENTIALS_FILE', None)
            env.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
            log=(tmp/f'{name}.log').open('w')
            proc=subprocess.Popen([sys.executable,'-m','scripts.flask_replica_stub_worker'],
                                  cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            workers.append(proc)
            log.close()
        conf=(ROOT/'ops/nginx/gateway.conf').read_text(encoding='utf-8')
        conf=(conf.replace('api_a:8091', f'127.0.0.1:{ports[0]}')
                  .replace('api_b:8091', f'127.0.0.1:{ports[1]}')
                  .replace('listen 8080;',f'listen 127.0.0.1:{ports[2]};')
                  .replace('/usr/share/nginx/html/lab/',str(ROOT/'dashboard')+'/')
                  # Original Flask exposes /health, /users/info, not /api/health.
                  .replace('proxy_pass http://coursesphere_api;',
                           'proxy_pass http://coursesphere_api/;'))
        (tmp/'gateway.conf').write_text(conf)
        nginx_conf=f'''{'user root;' if os.geteuid() == 0 else ''}
worker_processes 1;
pid {tmp}/nginx.pid;
error_log {tmp}/logs/error.log notice;
events {{ worker_connections 128; }}
http {{
  client_body_temp_path {tmp}/body;
  proxy_temp_path {tmp}/proxy;
  fastcgi_temp_path {tmp}/fastcgi;
  uwsgi_temp_path {tmp}/uwsgi;
  scgi_temp_path {tmp}/scgi;
  types {{ text/html html; text/css css; application/javascript js; application/json json; }}
  log_format coursesphere_json escape=json
    '{{"event":"edge_http","path":"$uri","method":"$request_method","status":$status,"request_id":"$request_id"}}';
  access_log {tmp}/logs/access.log coursesphere_json;
  include {tmp}/gateway.conf;
}}
'''
        (tmp/'nginx.conf').write_text(nginx_conf)
        try:
            for i, worker in enumerate(workers):
                wait_ready(f'http://127.0.0.1:{ports[i]}/health',worker)
            check=subprocess.run(['nginx','-p',str(tmp)+'/','-c',str(tmp/'nginx.conf'),'-t'],
                                 capture_output=True,text=True)
            if check.returncode:
                raise RuntimeError('Nginx configuration invalid: '+check.stderr[-250:])
            nginx=subprocess.Popen(['nginx','-p',str(tmp)+'/','-c',str(tmp/'nginx.conf'),
                                   '-g','daemon off;'],stdout=subprocess.DEVNULL,
                                  stderr=(tmp/'nginx.log').open('w'))
            workers.append(nginx)
            base=f'http://127.0.0.1:{ports[2]}'
            wait_ready(base+'/api/health',nginx)
            counts={}
            for _ in range(40):
                status,headers,payload=http(base+'/api/health')
                assert status==200 and json.loads(payload).get('status')=='ok'
                instance=headers.get('X-CourseSphere-Test-Instance')
                assert instance in ('flask-a','flask-b'),instance
                counts[instance]=counts.get(instance,0)+1
            assert set(counts)=={'flask-a','flask-b'},counts
            result['tests']['original_flask_replicas']=counts
            status,_,_=http(base+'/api/users/info')
            assert status==401, status
            status,_,_=http(base+'/api/users/info',token='SYNTHETIC_TOKEN')
            assert status==200,status
            status,_,_=http(base+'/api/users/info?id_token=SYNTHETIC_TOKEN')
            assert status==401,status
            result['tests']['original_flask_authorization']={
                'anonymous':401,'bearer_valid':200,'query_token':401}
            # Failover while the formerly backed-up instance remains available.
            workers[0].terminate(); workers[0].wait(timeout=5)
            for _ in range(8):
                status,headers,_=http(base+'/api/health')
                assert status==200 and headers.get('X-CourseSphere-Test-Instance')=='flask-b'
            result['tests']['survivor_after_flask_a_crash']={'instance':'flask-b','successes':8}
            status,_,_=http(base+'/metrics')
            assert status==403,status
            result['tests']['metrics_private']=403
            canary='SYNTHETIC_NON_SECRET_TOKEN_V19_3'
            status,_,_=http(base+'/api/users/info?id_token='+canary)
            assert status==401,status
            http(base+'/api/health')
            logfile=tmp/'logs/access.log'
            entries=[json.loads(line) for line in logfile.read_text().splitlines() if line.strip()]
            assert entries and canary not in logfile.read_text()
            assert all('?' not in entry['path'] for entry in entries)
            assert any(entry['status']==401 for entry in entries)
            status,_,_=http(base+'/api/users/info?id%5Ftoken='+canary)
            assert status==400,status
            result['tests']['encoded_query_blocked']=400
            result['tests']['edge_rejects_token_query']=401
            result['tests']['edge_access_log_redacted']=True

            result['validated']=True
        except Exception as exc:
            result['error']=f'{type(exc).__name__}: {str(exc)[:240]}'
        finally:
            for proc in reversed(workers):
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=4)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['validated'] else 1


if __name__=='__main__':
    raise SystemExit(main())
