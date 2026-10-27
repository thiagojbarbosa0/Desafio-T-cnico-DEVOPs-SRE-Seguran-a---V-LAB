#!/usr/bin/env python3
"""Real loopback HTTP proof of *synthetic demo* two-replica auth/quota.

No Docker, Flask, Firebase, internet, or production credentials are used.
The process starts two Python HTTP servers, each with its own SQLite connection
but the SAME private temporary file and signing key, then shuts them down.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.local_server import make_server

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/R7_SYNTHETIC_REPLICA_HTTP.json'
SOURCE_FILES = ['backend/demo_store.py', 'backend/security_core.py',
                'backend/local_server.py', 'scripts/prove_r7_dual_replica_auth.py']


def request(base: str, method: str, path: str, body: dict | None = None,
            token: str | None = None) -> tuple[int, object]:
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base + path, method=method, data=data, headers=headers)
    try:
        response = urlopen(req, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read().decode('utf-8')
        if response.headers.get('Content-Type', '').startswith('application/json'):
            return response.status, json.loads(raw)
        return response.status, raw


def run() -> dict:
    checks = {}
    with tempfile.TemporaryDirectory(prefix='coursesphere-r7-synthetic-') as directory:
        path = str(Path(directory) / 'shared.sqlite3')
        key = 'synthetic-and-local-only-signing-key-R7-' + 'X' * 32
        a = make_server('127.0.0.1', 0, path, secret=key, instance='synthetic-a')
        b = make_server('127.0.0.1', 0, path, secret=key, instance='synthetic-b')
        servers = (a, b)
        threads = [threading.Thread(target=x.serve_forever, daemon=True) for x in servers]
        for thread in threads:
            thread.start()
        bases = [f'http://127.0.0.1:{server.server_address[1]}' for server in servers]
        try:
            checks['two_liveness_checks'] = all(request(base, 'GET', '/api/health')[0] == 200 for base in bases)
            checks['two_readiness_checks'] = all(request(base, 'GET', '/api/ready')[0] == 200 for base in bases)
            code, result = request(bases[0], 'POST', '/api/demo/session', {'uid':'alice'})
            token = result.get('access_token') if code == 200 and isinstance(result, dict) else None
            checks['cross_replica_signed_token'] = bool(token and request(bases[1], 'GET', '/api/courses', token=token)[0] == 200)
            checks['cross_user_access_blocked'] = bool(token and request(bases[1], 'PUT', '/api/courses/2',
                                                      {'title':'Unauthorised','description':''}, token=token)[0] == 403)
            # Use the same synthetic client identity (loopback) across both
            # instances. One token has already debited the shared 30/min bucket.
            def issue(i: int):
                return request(bases[i % 2], 'POST', '/api/demo/session', {'uid':'alice'})[0]
            with ThreadPoolExecutor(max_workers=10) as pool:
                responses = list(pool.map(issue, range(40)))
            checks['shared_quota_across_both_replicas'] = responses.count(200) == 29 and responses.count(429) == 11
            with a.RequestHandlerClass.context.store.connect() as db:
                record = db.execute("SELECT hits FROM rate_limits WHERE bucket='session:127.0.0.1'").fetchone()
                checks['no_increment_after_429'] = record is not None and record['hits'] == 30
            checks['no_private_metrics_via_gateway'] = 'not-tested-no-nginx'
            # A real Nginx boundary is independently verified by existing tools.
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=3)
    validated = all(value is True for key, value in checks.items() if key != 'no_private_metrics_via_gateway')
    return {
        'validated': validated,
        'scope': 'Two real loopback Python demo HTTP servers and SQLite; NOT Flask/Firebase/Docker',
        'version': 'R7-derived-V19.9',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'checks': checks,
        'source_sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SOURCE_FILES},
        'counts': {'successful_login_requests': responses.count(200) + 1,
                   'rate_limited_login_requests': responses.count(429)}
    }


if __name__ == '__main__':
    report = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report['validated'] else 1)
