#!/usr/bin/env python3
"""Syntax-check the Docker Nginx main config using the native Nginx binary.

Only temporary loopback paths and hostnames are adjusted; no Docker/container
health is inferred from this static parser check. Does not contact any service.
"""
from __future__ import annotations
import subprocess
import os
import tempfile
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]

def verify() -> tuple[bool,str]:
    if not which('nginx'):
        return False, 'Nginx binary unavailable — NOT TESTED'
    with tempfile.TemporaryDirectory(prefix='coursesphere-nginx-main-check-') as tmp:
        tmp=Path(tmp)
        (tmp/'logs').mkdir()
        main=(ROOT/'ops/nginx/nginx.conf').read_text()
        gateway=(ROOT/'ops/nginx/gateway.conf').read_text()
        # Keep the actual directives including log_format, access_log,
        # hardening and all server blocks, but use harmless local references.
        main=main.replace('user nginx;', 'user root;' if os.geteuid() == 0 else '# user omitted for unprivileged syntax check')
        main=main.replace('pid /tmp/nginx.pid;',f'pid {tmp}/nginx.pid;')
        main=main.replace('include /etc/nginx/conf.d/*.conf;',f'include {tmp}/gateway.conf;')
        main=main.replace('access_log /dev/stdout coursesphere_json;',
                          f'access_log {tmp}/logs/access.log coursesphere_json;')
        main=main.replace('error_log /dev/stderr warn;',f'error_log {tmp}/logs/error.log warn;')
        main=main.replace('client_body_temp_path /tmp/client_temp;',f'client_body_temp_path {tmp}/client_temp;')
        main=main.replace('proxy_temp_path /tmp/proxy_temp;',f'proxy_temp_path {tmp}/proxy_temp;')
        main=main.replace('fastcgi_temp_path /tmp/fastcgi_temp;',f'fastcgi_temp_path {tmp}/fastcgi_temp;')
        main=main.replace('uwsgi_temp_path /tmp/uwsgi_temp;',f'uwsgi_temp_path {tmp}/uwsgi_temp;')
        main=main.replace('scgi_temp_path /tmp/scgi_temp;',f'scgi_temp_path {tmp}/scgi_temp;')
        # Minimal host installations may lack the distribution MIME include.
        # Substitute an empty type map for syntax only; no MIME behavior claim.
        if not Path('/etc/nginx/mime.types').is_file():
            (tmp/'mime.types').write_text('types {}\n')
            main=main.replace('/etc/nginx/mime.types', str(tmp/'mime.types'))
        gateway=(gateway.replace('api_a:8091','127.0.0.1:18091')
                        .replace('api_b:8091','127.0.0.1:18092')
                        .replace('listen 8080;', 'listen 127.0.0.1:18080;')
                        .replace('/usr/share/nginx/html/lab/',str(ROOT/'dashboard')+'/'))
        (tmp/'nginx.conf').write_text(main)
        (tmp/'gateway.conf').write_text(gateway)
        result=subprocess.run(['nginx','-t','-p',str(tmp)+'/','-c',str(tmp/'nginx.conf')],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,timeout=8)
        if result.returncode:
            return False,'Docker-derived config invalid: '+result.stderr[-900:]
        return True,'Nginx main + gateway config parsed successfully (native host, no Docker runtime)'

if __name__=='__main__':
    passed,message=verify()
    print(message)
    raise SystemExit(0 if passed else 1)
