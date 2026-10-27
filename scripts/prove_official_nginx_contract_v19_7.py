#!/usr/bin/env python3
"""Native Nginx proof for the NEW original-stack proxy contract.

Original routing/security config is exercised through Nginx; upstreams are
synthetic Python HTTP servers. This does not validate real Flask nor Docker.
"""
from __future__ import annotations
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/NGINX_OFFICIAL_ROUTING_V19_7.json'


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@contextmanager
def server(replica, port_number):
    stats = Counter()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            stats['all'] += 1
            if replica == 'web':
                body = b'<!doctype html><html><title>CourseSphere local test</title></html>'
                status = 200
                ctype = 'text/html'
            elif self.path == '/health':
                stats['health'] += 1
                body = b'{"status":"ok","service":"coursesphere-api"}'
                status = 200
                ctype = 'application/json'
            elif self.path == '/ready':
                stats['ready'] += 1
                body = b'{"status":"ready","service":"coursesphere-api"}'
                status, ctype = 200, 'application/json'
            elif self.path == '/users/info':
                status, body, ctype = 401, b'{"error":"Authentication required"}', 'application/json'
            else:
                status, body, ctype = 404, b'{}', 'application/json'
            self.send_response(status)
            self.send_header('Content-Type',ctype)
            self.send_header('X-Test-Replica',replica)
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, fmt, *args):
            pass
    httpd = ThreadingHTTPServer(('127.0.0.1', port_number), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield stats
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def get(port_number, path):
    try:
        result = urlopen(f'http://127.0.0.1:{port_number}{path}', timeout=3)
    except HTTPError as exc:
        result = exc
    with result:
        return result.status, result.headers.get('X-Test-Replica',''), result.read(1500)


def wait(port_number, process):
    until = time.monotonic() + 9
    while time.monotonic() < until:
        if process.poll() is not None:
            raise AssertionError('Native Nginx exited before readiness')
        try:
            if get(port_number,'/health')[0]==200:
                return
        except (OSError, URLError):
            pass
        time.sleep(.12)
    raise AssertionError('Nginx did not serve the official health route')


def run():
    report = {
        'version': 'V19.7', 'validated': False,
        'scope': 'REAL native Nginx with original-stack gateway. Upstream Flask and React mocked by stdlib Python HTTP servers; NOT Docker, real Flask, Firebase or React.',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                          ('ops/nginx/gateway.official.conf','ops/nginx/nginx.conf','scripts/prove_official_nginx_contract_v19_7.py')},
        'tests': {},
    }
    if not shutil.which('nginx'):
        report['error'] = 'Nginx is not installed'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2)+'\n')
        return report
    a,b,web,gateway = (port() for _ in range(4))
    with tempfile.TemporaryDirectory(prefix='coursesphere-official-nginx-') as temp:
        home = Path(temp)
        (home/'logs').mkdir()
        config = (ROOT/'ops/nginx/gateway.official.conf').read_text()
        config = (config.replace('official_api_a:8091',f'127.0.0.1:{a}')
                        .replace('official_api_b:8091',f'127.0.0.1:{b}')
                        .replace('official_frontend:8082',f'127.0.0.1:{web}')
                        .replace('listen 8081;',f'listen 127.0.0.1:{gateway};'))
        (home/'gateway.conf').write_text(config)
        main_conf = f'''{'user root;' if os.geteuid() == 0 else ''}
worker_processes 1; pid {home}/nginx.pid;
error_log {home}/logs/error.log warn;
events {{ worker_connections 128; }}
http {{
  client_body_temp_path {home}/client_body;
  proxy_temp_path {home}/proxy;
  fastcgi_temp_path {home}/fastcgi;
  uwsgi_temp_path {home}/uwsgi;
  scgi_temp_path {home}/scgi;
  log_format coursesphere_json escape=json
    '{{"event":"edge_http","path":"$uri","status":$status,"upstream":"$upstream_addr"}}';
  access_log {home}/logs/access.log coursesphere_json;
  include {home}/gateway.conf;
}}
'''
        (home/'nginx.conf').write_text(main_conf)
        process = None
        try:
            check = subprocess.run(['nginx','-p',str(home)+'/','-c',str(home/'nginx.conf'),'-t'],
                                   capture_output=True,text=True,timeout=6)
            if check.returncode:
                raise AssertionError('Nginx syntax validation failed: '+check.stderr[-200:])
            report['tests']['nginx_config'] = 'pass'
            # Stop/start a backend by leaving/entering its context explicitly.
            with server('api-a',a) as count_a, server('web',web):
                with server('api-b',b) as count_b:
                    with (home/'logs/stderr.log').open('w') as nginx_err:
                        process = subprocess.Popen(['nginx','-p',str(home)+'/','-c',str(home/'nginx.conf'),
                                                    '-g','daemon off;'], stdout=subprocess.DEVNULL,
                                                   stderr=nginx_err)
                        wait(gateway,process)
                        assert get(gateway,'/users/info')[0] == 401
                        report['tests']['api_route_original_prefix'] = 'pass'
                        ready_status,ready_replica,ready_body = get(gateway,'/ready')
                        assert ready_status==200 and ready_replica in ('api-a','api-b')
                        assert json.loads(ready_body).get('status')=='ready'
                        report['tests']['readiness_route_to_flask_upstream'] = 'pass'
                        status,replica,html = get(gateway,'/')
                        assert status==200 and replica=='web' and b'CourseSphere' in html
                        assert get(gateway,'/dashboard')[0] == 200
                        report['tests']['react_spa_gateway'] = 'pass'
                        assert get(gateway,'/metrics')[0]==403
                        report['tests']['metrics_denied'] = 'pass'
                        marker='SYNTHETIC_TOKEN_MARKER_79F4_NOT_A_CREDENTIAL'
                        assert get(gateway,'/users/info?id_token='+marker)[0]==401
                        assert get(gateway,'/dashboard?id%5Ftoken='+marker)[0]==401
                        assert get(gateway,'/users/info?name=safe')[0]==400
                        report['tests']['query_blocking'] = 'pass'
                        for _ in range(40):
                            assert get(gateway,'/health')[0] == 200
                        report['tests']['backend_distribution'] = {'a':count_a['health'],'b':count_b['health']}
                        if min(count_a['health'],count_b['health']) == 0:
                            raise AssertionError('Nginx did not distribute health requests to both backends')
                        # Native backend B still runs when A has gone away.
                        # A was created first, so next proof uses a separate context below.
                    # Nginx is still running, but a backend context remains active.
                # B has stopped, A stays online, forcing a real proxy failover.
                for _ in range(8):
                    assert get(gateway,'/health')[0]==200
                report['tests']['survivor_after_backend_stop']='8/8 pass'
            # Every runtime service now stopped; read protected structured logs.
            logfile = (home/'logs/access.log').read_text()
            assert marker not in logfile
            assert 'id_token=' not in logfile
            report['tests']['no_token_query_in_edge_logs']='pass'
            report['validated']=True
        except Exception as exc:
            report['error_type']=type(exc).__name__
            report['error']=str(exc)[:230]
        finally:
            if process:
                process.terminate()
                try: process.wait(timeout=6)
                except subprocess.TimeoutExpired: process.kill();process.wait(timeout=3)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report

if __name__ == '__main__':
    report=run()
    print(json.dumps(report,indent=2,ensure_ascii=False))
    raise SystemExit(0 if report['validated'] else 1)
