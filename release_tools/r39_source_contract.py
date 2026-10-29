#!/usr/bin/env python3
"""R39: safe entrypoint for the actual R16 Docker pilot; no parallel stack.

Default is READ-ONLY. Explicit --run delegates to the existing R16 pilot,
without altering old Docker projects, after checking emulator ownership and
that *all* published emulator ports are loopback-only.
"""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EMULATOR = 'coursesphere-official-local-official_firebase_emulators-1'
EXPECTED_PROJECT = 'coursesphere-official-local'
EXPECTED_PORTS = {'9000/tcp': '9000', '9099/tcp': '9099'}
REQUIRED = (
    'backend/endpoints.py', 'backend/firebase.py',
    'backend/firebase_configuration.py', 'backend/shared_quota.py',
    'backend/Dockerfile.official', 'frontend/Dockerfile.official',
    'frontend/package-lock.json', 'frontend/src/api.ts',
    'frontend/src/firebaseConfig.ts', 'frontend/src/firebaseClient.ts',
    'compose.r16.existing-emulator.yaml',
    'scripts/deploy_r16_docker_pilot.py',
    'ops/nginx/gateway.official.conf',
    'ops/prometheus/prometheus.official.yml',
)

class Refusal(RuntimeError):
    pass


def check_original_source(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise Refusal('Checkout must be a real directory')
    manifest = root / 'RELEASE_MANIFEST.json'
    if manifest.is_symlink() or not manifest.is_file():
        raise Refusal('R16 release manifest missing')
    try:
        obj = json.loads(manifest.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        raise Refusal('Invalid release manifest') from None
    if obj.get('release') != 'R16_DOCKER_PILOT':
        raise Refusal('Not the R16 Docker pilot release')
    declared = obj.get('files', {})
    if not isinstance(declared, dict):
        raise Refusal('Invalid release source manifest')
    missing, altered = [], []
    for rel in REQUIRED:
        target = root / rel
        expected = declared.get(rel)
        if target.is_symlink() or not target.is_file() or not isinstance(expected, str):
            missing.append(rel)
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            altered.append(rel)
    return {'release': obj['release'], 'expected_files': len(REQUIRED),
            'matching': len(REQUIRED)-len(missing)-len(altered),
            'missing': missing, 'modified': altered,
            'ready': not (missing or altered)}


def _is_loopback(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_loopback
    except (ValueError, TypeError):
        return False


def validate_emulator_ports(info: dict) -> dict:
    """Inspect actual HostConfig *and* NetworkSettings mappings, fail closed."""
    labels = (info.get('Config') or {}).get('Labels') or {}
    if labels.get('com.docker.compose.project') != EXPECTED_PROJECT or labels.get('com.docker.compose.service') != 'official_firebase_emulators':
        raise Refusal('Emulator container is not owned by the expected demo project')
    state = info.get('State') or {}
    if state.get('Running') is not True or (state.get('Health') or {}).get('Status') != 'healthy':
        raise Refusal('Owned emulator must be running and healthy')
    for kind, entries in (
        ('configured', (info.get('HostConfig') or {}).get('PortBindings') or {}),
        ('effective', (info.get('NetworkSettings') or {}).get('Ports') or {}),
    ):
        if not isinstance(entries, dict):
            raise Refusal('Malformed emulator port map')
        for key, bindings in entries.items():
            if bindings is None:
                continue
            if not isinstance(bindings, list):
                raise Refusal('Malformed emulator port bindings')
            for entry in bindings:
                if (not isinstance(entry, dict)
                    or not _is_loopback(entry.get('HostIp', ''))):
                    raise Refusal('Public or ambiguous emulator port exposure')
                if key in EXPECTED_PORTS and entry.get('HostPort') != EXPECTED_PORTS[key]:
                    raise Refusal('Emulator port does not match the local contract')
        for key, host_port in EXPECTED_PORTS.items():
            bindings = entries.get(key)
            if not bindings or not any(b.get('HostPort') == host_port for b in bindings):
                raise Refusal('Expected local emulator port is not published')
    return {'emulator_running_healthy': True, 'ports_loopback_only': True,
            'auth_port': 9099, 'database_port': 9000}


def docker_json(*args: str):
    try:
        p = subprocess.run(['docker', *args], cwd=ROOT, capture_output=True,
                           text=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Refusal('Docker engine not accessible') from None
    if p.returncode != 0:
        raise Refusal('Docker inspect or daemon unavailable')
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise Refusal('Docker returned invalid inspection data') from None


def verify_runtime() -> dict:
    details = docker_json('inspect', EMULATOR)
    if not isinstance(details, list) or len(details) != 1:
        raise Refusal('Expected exactly one emulator container')
    ports = validate_emulator_ports(details[0])
    # The original pilot checks the actual network ownership and DNS alias.
    return ports


def safe_child_environment() -> dict:
    env = dict(os.environ)
    for name in ('GOOGLE_APPLICATION_CREDENTIALS', 'FIREBASE_CREDENTIALS_FILE',
                 'FIREBASE_DATABASE_URL', 'FIREBASE_AUTH_EMULATOR_HOST',
                 'FIREBASE_DATABASE_EMULATOR_HOST', 'GCLOUD_PROJECT',
                 'OPENAI_API_KEY', 'R16_FIREBASE_NETWORK',
                 'OFFICIAL_GRAFANA_ADMIN_PASSWORD'):
        env.pop(name, None)
    return env


def run():
    parser = argparse.ArgumentParser(description='Read-only R16 Docker preflight by default')
    parser.add_argument('--run', action='store_true', help='Explicitly start isolated R16 pilot')
    options = parser.parse_args()
    report = {'schema': 'coursesphere.r39.r16-docker.v1', 'mode': 'run' if options.run else 'inspect',
              'docker_started': False, 'validated': False, 'preflight_passed': False, 'source': {}, 'runtime': {}}
    try:
        report['source'] = check_original_source(ROOT)
        if not report['source']['ready']:
            raise Refusal('R16 source incomplete or modified; see missing/modified file names')
        report['runtime'] = verify_runtime()
        # Also validate external network ownership + local sockets before startup.
        # Import only after verifying the source contract.
        from scripts import deploy_r16_docker_pilot as pilot
        pilot.check_emulator()
        report['preflight_passed'] = True
        if options.run:
            # Delegate to R16's existing isolated project runner. No down/rm/prune.
            result = subprocess.run([sys.executable, '-m', 'scripts.deploy_r16_docker_pilot'],
                                    cwd=ROOT, env=safe_child_environment(), check=False)
            report['docker_started'] = result.returncode == 0  # Confirmed only if complete pilot passed.
            report['validated'] = result.returncode == 0
            report['pilot_exit_code'] = result.returncode
        else:
            report['validated'] = False  # Preflight alone NEVER qualifies as Docker proof.
    except Refusal as exc:
        report['refusal'] = str(exc)
    except Exception as exc:
        # Never include user-supplied URLs, secrets, or Docker inspection payloads.
        report['refusal'] = 'R16 preflight rejected: '+type(exc).__name__
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if report['preflight_passed'] and (not options.run or report['validated']) else 1

if __name__ == '__main__':
    sys.exit(run())
