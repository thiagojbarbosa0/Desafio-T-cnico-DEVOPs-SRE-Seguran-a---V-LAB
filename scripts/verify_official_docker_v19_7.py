#!/usr/bin/env python3
"""Runtime evidence for ORIGINAL CourseSphere Docker stack, not the synthetic lab.

Fail closed when Docker is absent, replicas do not both handle requests, backend
restart fails, or old logs are inadvertently reused. No user credentials needed.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'evidence/runtime/OFFICIAL_DOCKER_V19_7.json'
FILES = ('compose.official.yaml', 'backend/Dockerfile.official',
         'frontend/Dockerfile.official', 'ops/nginx/gateway.official.conf',
         'ops/nginx/frontend.official.conf', 'ops/nginx/nginx.conf',
         'backend/endpoints.py', 'scripts/verify_official_docker_v19_7.py')
BASE = 'http://127.0.0.1:8081'


def compose(*args: str) -> str:
    p = subprocess.run(['docker', 'compose', '-f', 'compose.official.yaml', *args],
                       cwd=ROOT, capture_output=True, text=True, timeout=75)
    if p.returncode:
        raise RuntimeError(f'Docker Compose {args[0]} failed ({p.returncode}): {(p.stderr or p.stdout)[-250:]}')
    return p.stdout


def call(path: str) -> tuple[int, str, str]:
    request = Request(BASE + path)
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read(100000).decode('utf-8', errors='replace')
        return response.status, response.headers.get('Content-Type', ''), body


def until(fn, seconds=60):
    deadline = time.monotonic() + seconds
    last = 'not ready'
    while time.monotonic() < deadline:
        try:
            result = fn()
            if result:
                return result
        except (OSError, URLError, ValueError, AssertionError, RuntimeError) as exc:
            last = type(exc).__name__
        time.sleep(.6)
    raise RuntimeError('Readiness was not demonstrated: ' + last)


def access_upstreams(since: str, *, marker: str = '') -> list[str]:
    """Parse only edge JSON logs generated after this probe started."""
    raw = compose('logs', '--no-color', '--no-log-prefix', '--since', since,
                  'official_gateway')
    if marker and marker in raw:
        raise AssertionError('Marker from a rejected query appeared in gateway logs')
    endpoints = []
    for line in raw.splitlines():
        idx = line.find('{"event":"edge_http"')
        if idx < 0:
            continue
        try:
            item = json.loads(line[idx:])
        except ValueError:
            continue
        if item.get('path') != '/health' or item.get('status') != 200:
            continue
        for endpoint in re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}:8091\b', item.get('upstream') or ''):
            endpoints.append(endpoint)
    return endpoints


def execute(*, failover: bool) -> dict:
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    report = {
        'version': 'V19.7', 'scope': 'Original patched Flask + original React Docker containers, native Nginx image; no Firebase emulators or Grafana',
        'validated': False, 'started_utc': stamp, 'tests': {},
        'source_sha256': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES},
    }
    stopped = False
    try:
        compose('config', '--quiet')
        report['tests']['compose_config'] = 'pass'
        until(lambda: call('/health')[0] == 200)
        status, content_type, body = call('/health')
        assert status == 200 and json.loads(body).get('status') == 'ok'
        report['tests']['original_flask_health'] = 'pass'
        assert call('/users/info')[0] == 401
        report['tests']['anonymous_profile_denied'] = 'pass'
        status, content_type, body = call('/')
        assert status == 200 and 'text/html' in content_type
        report['tests']['original_react_served'] = 'pass'
        assert call('/dashboard')[0] == 200
        report['tests']['spa_fallback'] = 'pass'
        assert call('/metrics')[0] == 403
        report['tests']['public_metrics_denied'] = 'pass'
        marker = 'NEVER_LOG_THIS_SYNTHETIC_MARKER_197'
        assert call('/users/info?id_token=' + marker)[0] == 401
        assert call('/dashboard?id%5Ftoken=' + marker)[0] == 401
        assert call('/users/info?non_sensitive=1')[0] == 400
        report['tests']['api_query_rejected'] = 'pass'
        for _ in range(40):
            assert call('/health')[0] == 200
        endpoints = access_upstreams(stamp, marker=marker)
        distribution = Counter(endpoints)
        # Upstream addresses are intentionally not exported to the evidence.
        if len(distribution) < 2:
            raise AssertionError('Only one original Flask replica served the requests')
        report['tests']['two_original_flask_replicas'] = {
            'result': 'pass', 'replicas': len(distribution), 'total_upstream_attempts': len(endpoints),
            'distribution': sorted(distribution.values()),
        }
        report['tests']['query_marker_not_logged'] = 'pass'
        if failover:
            compose('stop', 'official_api_a')
            stopped = True
            until(lambda: call('/health')[0] == 200, seconds=25)
            for _ in range(8):
                assert call('/health')[0] == 200
            report['tests']['original_failover'] = {'result': 'pass', 'responses': 8}
        report['validated'] = True
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)[:250]
        report['validated'] = False
    finally:
        if stopped:
            try:
                compose('start', 'official_api_a')
                # Do not count successful start of a container as HTTP readiness.
                def restored():
                    response = compose('exec', '-T', 'official_api_a', 'python', '-c',
                                       'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:8091/health",timeout=3); assert r.status==200')
                    return True
                until(restored, seconds=65)
                report['tests']['stopped_replica_restored'] = 'pass'
            except Exception as exc:
                report['tests']['stopped_replica_restored'] = 'FAILED'
                report['validated'] = False
                report['recovery_error'] = type(exc).__name__
        OUTPUT.parent.mkdir(exist_ok=True, parents=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--failover', action='store_true')
    opts = parser.parse_args()
    result = execute(failover=opts.failover)
    print(json.dumps({'validated': result['validated'], 'tests': result['tests'],
                      'error': result.get('error')}, indent=2, ensure_ascii=False))
    return 0 if result['validated'] else 1


if __name__ == '__main__':
    sys.exit(main())
