#!/usr/bin/env python3
"""CourseSphere R40 -- safe read-only inspection of an EXISTING R16 Docker pilot.

No Compose commands, no writes to Firebase, no Docker mutation, no credentials.
The only network calls are fixed 127.0.0.1 endpoints.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlencode

PROJECT = 'coursesphere-r16-pilot'
EMULATOR_PROJECT = 'coursesphere-official-local'
EMULATOR_SERVICE = 'official_firebase_emulators'
EMULATOR_NAME = 'coursesphere-official-local-official_firebase_emulators-1'
REQUIRED = {
    'official_api_a': {'8091/tcp': '18091'},
    'official_api_b': {'8091/tcp': '18092'},
    'official_frontend': {},
    'official_gateway': {'8081/tcp': '18081'},
    'official_prometheus': {'9090/tcp': '19092'},
    'official_grafana': {'3000/tcp': '13001'},
}
EMULATOR_PORTS = {'9000/tcp': '9000', '9099/tcp': '9099'}
LOOPBACK = '127.0.0.1'


def docker_json(*args: str):
    try:
        p = subprocess.run(['docker', *args], text=True, capture_output=True,
                           timeout=20, check=False, env={**os.environ, 'DOCKER_CLI_HINTS': 'false'})
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('docker_unavailable') from None
    if p.returncode:
        raise RuntimeError('docker_inspect_failed')
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        raise RuntimeError('docker_invalid_json') from None


def docker_lines(*args: str):
    try:
        p = subprocess.run(['docker', *args], text=True, capture_output=True,
                           timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('docker_unavailable') from None
    if p.returncode:
        raise RuntimeError('docker_ps_failed')
    return [line for line in p.stdout.splitlines() if line.strip()]


def valid_bindings(container: dict, expected: dict[str, str]) -> list[str]:
    issues = []
    for field, ports in (
        ('configured', (container.get('HostConfig') or {}).get('PortBindings') or {}),
        ('effective', (container.get('NetworkSettings') or {}).get('Ports') or {}),
    ):
        if not isinstance(ports, dict):
            issues.append(f'{field}_ports_invalid')
            continue
        present = {}
        for key, entries in ports.items():
            if entries is None:
                continue
            if not isinstance(entries, list):
                issues.append(f'{field}_bindings_invalid')
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    issues.append(f'{field}_binding_invalid')
                    continue
                host = entry.get('HostIp', '')
                port = str(entry.get('HostPort', ''))
                try:
                    loopback = ipaddress.ip_address(host).is_loopback
                except ValueError:
                    loopback = False
                if not loopback:
                    issues.append(f'{field}_nonloopback')
                if key not in expected:
                    issues.append(f'{field}_unexpected_published_port')
                elif port != expected[key]:
                    issues.append(f'{field}_incorrect_port')
                present.setdefault(key, []).append(port)
        for key, port in expected.items():
            if port not in present.get(key, []):
                issues.append(f'{field}_missing_port')
    return sorted(set(issues))


def inspect_container(item: dict, project: str, service: str, expected_ports: dict) -> dict:
    labels = (item.get('Config') or {}).get('Labels') or {}
    state = item.get('State') or {}
    result = {
        'service': service,
        'running': state.get('Running') is True,
        'health': (state.get('Health') or {}).get('Status', 'not_configured'),
        'owner_ok': labels.get('com.docker.compose.project') == project
                    and labels.get('com.docker.compose.service') == service,
        'port_issues': valid_bindings(item, expected_ports),
    }
    return result


def check_local(port: int, path: str, expected: set[int], method: str = 'GET') -> dict:
    try:
        conn = http.client.HTTPConnection(LOOPBACK, port, timeout=3)
        try:
            conn.request(method, path, headers={'Host': '127.0.0.1', 'Connection': 'close'})
            response = conn.getresponse()
            status = response.status
            response.read(32768)
        finally:
            conn.close()
        return {'status': status, 'pass': status in expected}
    except (OSError, http.client.HTTPException):
        return {'status': None, 'pass': False}


def check_prometheus() -> dict:
    query = 'up{job="coursesphere-original"}'
    path = '/api/v1/query?' + urlencode({'query': query})
    try:
        conn = http.client.HTTPConnection(LOOPBACK, 19092, timeout=4)
        try:
            conn.request('GET', path)
            r = conn.getresponse()
            body = r.read(32768)
        finally:
            conn.close()
        data = json.loads(body)
        values = {x.get('metric', {}).get('instance'): str(x.get('value', [None, None])[1])
                  for x in data.get('data', {}).get('result', [])}
        expected = {'official_api_a:8091', 'official_api_b:8091'}
        ok = r.status == 200 and data.get('status') == 'success' and set(values) == expected and all(values[x] == '1' for x in expected)
        return {'pass': ok, 'instances': {k: v for k, v in values.items() if k in expected}, 'instance_count': len(values)}
    except (OSError, ValueError, TypeError, IndexError, KeyError, http.client.HTTPException):
        return {'pass': False, 'instances': {}, 'instance_count': 0}


def inspect() -> dict:
    result = {
        'schema': 'coursesphere.r40.existing-pilot-inspection.v1',
        'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'docker_mutated': False, 'firebase_mutated': False,
        'pilot_project': PROJECT, 'status': 'NOT_CHECKED',
        'services': {}, 'emulator': {}, 'probes': {}, 'issues': [],
        'scope': 'read_only_existing_docker_pilot_not_full_acceptance',
    }
    ids = docker_lines('ps', '-a', '-q', '--filter', f'label=com.docker.compose.project={PROJECT}')
    if not ids:
        result['status'] = 'NO_EXISTING_PILOT'
        return result
    infos = docker_json('inspect', *ids)
    grouped = {service: [] for service in REQUIRED}
    for item in infos:
        labels = (item.get('Config') or {}).get('Labels') or {}
        service = labels.get('com.docker.compose.service')
        if service not in grouped:
            result['issues'].append('unexpected_pilot_service')
        else:
            grouped[service].append(item)
    for service, expected in REQUIRED.items():
        if len(grouped[service]) != 1:
            result['issues'].append(f'{service}_count_{len(grouped[service])}')
            continue
        service_result = inspect_container(grouped[service][0], PROJECT, service, expected)
        result['services'][service] = service_result
        if not service_result['owner_ok'] or service_result['port_issues']:
            result['issues'].append(f'{service}_ownership_or_ports')
    try:
        em = docker_json('inspect', EMULATOR_NAME)
        if len(em) != 1:
            raise RuntimeError('emulator_count_invalid')
        result['emulator'] = inspect_container(em[0], EMULATOR_PROJECT, EMULATOR_SERVICE, EMULATOR_PORTS)
        if not result['emulator']['running'] or result['emulator']['health'] != 'healthy' or not result['emulator']['owner_ok'] or result['emulator']['port_issues']:
            result['issues'].append('emulator_not_safe_healthy')
    except RuntimeError:
        result['issues'].append('emulator_inspection_unavailable')
    # Never probe any port if there is unsafe or ambiguous ownership/exposure.
    if result['issues']:
        result['status'] = 'PILOT_UNSAFE_OR_INCOMPLETE'
        return result
    if not all(x['running'] and x['health'] in ('healthy', 'not_configured') for x in result['services'].values()):
        result['status'] = 'PILOT_STOPPED_OR_UNHEALTHY'
        return result
    result['probes'] = {
        'gateway_health': check_local(18081, '/health', {200}),
        'api_a_health': check_local(18091, '/health', {200}),
        'api_b_health': check_local(18092, '/health', {200}),
        'api_a_ready': check_local(18091, '/ready', {200}),
        'api_b_ready': check_local(18092, '/ready', {200}),
        'gateway_metrics_denied': check_local(18081, '/metrics', {403}),
        'gateway_anonymous_profile_denied': check_local(18081, '/users/info', {401}),
        'grafana_health': check_local(13001, '/api/health', {200}),
        'prometheus_two_replicas_up': check_prometheus(),
    }
    result['status'] = 'EXISTING_PILOT_READONLY_CHECKS_PASS' if all(v['pass'] for v in result['probes'].values()) else 'EXISTING_PILOT_NEEDS_REVIEW'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--save', type=Path, default=None, help='Optional report JSON; no secrets')
    args = parser.parse_args()
    try:
        result = inspect()
    except (RuntimeError, ValueError, TypeError):
        result = {'schema': 'coursesphere.r40.existing-pilot-inspection.v1',
                  'status': 'DOCKER_INSPECTION_FAILED', 'docker_mutated': False, 'firebase_mutated': False}
    if args.save:
        dest = args.save.expanduser()
        if not dest.is_absolute() or dest.is_symlink() or dest.exists():
            print('REPORT_DESTINATION_UNSAFE', file=sys.stderr)
            return 2
        dest.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(dest, flags, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write('\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Inspections are diagnostic; no mutation, no deployment success asserted.
    return 0

if __name__ == '__main__':
    sys.exit(main())
