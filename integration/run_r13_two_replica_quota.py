"""R13: zero-secret real Flask/Firebase Emulator cross-replica quota proof.

Runs only with an explicitly configured loopback Firebase Emulator. Creates a
fresh synthetic account, launches two *separate* Flask processes, and delegates
the assertions to the R11 direct-replica proof. It cannot connect to production
or claim acceptance when dependencies/emulators are unavailable.
"""
from __future__ import annotations

import http.client
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from integration.emulator_fixture_cleanup_r14 import SyntheticAccount, validate_account, cleanup as cleanup_fixture

from backend.firebase_configuration import validate_emulators
from scripts.verify_official_replica_quota_r11 import (
    VerificationFailure, run as verify_quota, validate_emulator_environment,
    OUT as QUOTA_PROOF,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'demo-coursesphere-vlab'
AUTH_HOST = '127.0.0.1:9099'
DATABASE_HOST = '127.0.0.1:9000'
REQUIRED_ENV = {
    'COURSESPHERE_USE_FIREBASE_EMULATORS': '1',
    'GCLOUD_PROJECT': PROJECT,
    'FIREBASE_AUTH_EMULATOR_HOST': AUTH_HOST,
    'FIREBASE_DATABASE_EMULATOR_HOST': DATABASE_HOST,
}
FORBIDDEN_ENV = (
    'FIREBASE_CREDENTIALS_FILE', 'FIREBASE_DATABASE_URL',
    'GOOGLE_APPLICATION_CREDENTIALS',
)


def check_environment(env: dict[str, str]) -> None:
    """Reject even subtly mismatched configuration before opening a socket."""
    if any(env.get(key) != val for key, val in REQUIRED_ENV.items()):
        raise VerificationFailure('Dedicated loopback Firebase demo emulators are required')
    if any(env.get(key) for key in FORBIDDEN_ENV):
        raise VerificationFailure('Live Firebase credential configuration is forbidden')
    validate_emulators(PROJECT, AUTH_HOST, DATABASE_HOST, '')


def synthetic_signup(*, timeout: float = 5.0) -> SyntheticAccount:
    """Return a token in RAM only. No HTTPS, DNS, redirects, or user data in logs."""
    address = '/identitytoolkit.googleapis.com/v1/accounts:signUp?key=demo-key'
    content = json.dumps({
        'email': 'quota-' + secrets.token_hex(12) + '@synthetic.example.invalid',
        'password': secrets.token_urlsafe(30),
        'returnSecureToken': True,
    }, separators=(',', ':')).encode('utf-8')
    conn = http.client.HTTPConnection('127.0.0.1', 9099, timeout=timeout)
    try:
        conn.request('POST', address, body=content,
                     headers={'Content-Type': 'application/json', 'Connection': 'close'})
        response = conn.getresponse()
        raw = response.read(16385)
        if response.status != 200 or len(raw) > 16384:
            raise VerificationFailure('Local Auth Emulator synthetic signup failed')
        try:
            doc = json.loads(raw)
        except (ValueError, UnicodeError):
            raise VerificationFailure('Invalid local Auth Emulator signup response') from None
        if not isinstance(doc, dict) or not isinstance(doc.get('idToken'), str):
            raise VerificationFailure('Local Auth Emulator returned no synthetic ID token')
        account = SyntheticAccount(uid=doc.get('localId'), token=doc['idToken'])
        validate_account(account)
        return account
    except (OSError, http.client.HTTPException):
        raise VerificationFailure('Local Auth Emulator is not reachable') from None
    finally:
        conn.close()


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def start_replica(label: str, port: int, env: dict[str, str]) -> subprocess.Popen:
    if label not in ('official_api_a', 'official_api_b') or not (1024 <= port <= 65535):
        raise VerificationFailure('Invalid local replica label or port')
    child = dict(env)
    child['COURSESPHERE_REPLICA_NAME'] = label
    child['COURSESPHERE_TRUST_GATEWAY_REQUEST_ID'] = '0'
    child['ALLOWED_ORIGINS'] = 'http://127.0.0.1:5173'
    for key in (*FORBIDDEN_ENV, 'COURSESPHERE_R11_FIREBASE_ID_TOKEN'):
        child.pop(key, None)
    # No shell or token in argv. Stdout/stderr could accidentally reveal sensitive
    # debug data, so neither is copied into CI output or persisted to artifacts.
    return subprocess.Popen(
        [sys.executable, '-m', 'flask', '--app', 'endpoints:app', 'run',
         '--no-reload', '--no-debugger', '--host', '127.0.0.1', '--port', str(port)],
        cwd=str(ROOT / 'backend'), env=child,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def wait_health(port: int, proc: subprocess.Popen, *, deadline_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise VerificationFailure('Original Flask replica terminated before healthcheck')
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
        try:
            conn.request('GET', '/health')
            response = conn.getresponse()
            content = response.read(1025)
            if response.status == 200 and len(content) <= 1024:
                return
        except (OSError, http.client.HTTPException):
            pass
        finally:
            conn.close()
        time.sleep(0.15)
    raise VerificationFailure('Original Flask replica did not become healthy')


def stop_all(processes: list[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=4)


def execute(env: dict[str, str] | None = None) -> dict:
    """Return sanitized proof. A failed run removes any previous PASS artifact."""
    env = dict(os.environ if env is None else env)
    path = ROOT / QUOTA_PROOF
    path.unlink(missing_ok=True)
    check_environment(env)
    processes: list[subprocess.Popen] = []
    account: SyntheticAccount | None = None
    result: dict | None = None
    try:
        account = synthetic_signup()
        validate_account(account)
        scoped = dict(env, COURSESPHERE_R11_FIREBASE_ID_TOKEN=account.token)
        # Validate token scope in RAM; never pass this token to Flask subprocesses.
        validate_emulator_environment(scoped)
        a_port = free_loopback_port()
        b_port = free_loopback_port()
        while b_port == a_port:
            b_port = free_loopback_port()
        processes.append(start_replica('official_api_a', a_port, env))
        processes.append(start_replica('official_api_b', b_port, env))
        wait_health(a_port, processes[0])
        wait_health(b_port, processes[1])
        if int(time.time()) % 60 >= 43:
            time.sleep(61 - int(time.time()) % 60)
        candidate = verify_quota(f'http://127.0.0.1:{a_port}',
                                 f'http://127.0.0.1:{b_port}', env=scoped)
        validate_proof(candidate)
        result = candidate
    finally:
        try:
            stop_all(processes)
        finally:
            if account is not None:
                # A failed teardown cannot leave behind a PASS attestation.
                cleanup_fixture(account, env)
    if result is None:
        raise VerificationFailure('No verified Flask/Firebase evidence was produced')
    # This marker is set ONLY after scoped Auth+RTDB fixture cleanup succeeded.
    result = dict(result, fixture_cleanup_verified=True,
                  proof_origin='r14_scoped_emulator_coordinator')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def validate_proof(proof: dict) -> None:
    """Do not persist a self-contradictory, incomplete or stale PASS report."""
    from scripts.verify_official_replica_quota_r11 import CHECKS, SOURCES
    if not isinstance(proof, dict) or proof.get('validated') is not True:
        raise VerificationFailure('Cross-replica quota proof did not validate')
    expected_keys = {'version', 'scope', 'validated', 'checks', 'generated_utc',
                     'source_sha256', 'additional_acceptance_points', 'user_data_in_report'}
    if set(proof) != expected_keys:
        raise VerificationFailure('Cross-replica proof shape is incomplete')
    if (proof['version'] != 'R11-derived-V19.9'
            or proof['scope'] != 'two original Flask replicas + local Firebase Auth/RTDB emulators only'
            or type(proof['additional_acceptance_points']) is not int
            or proof['additional_acceptance_points'] != 0
            or proof['user_data_in_report'] is not False):
        raise VerificationFailure('Cross-replica proof scope or scoring invalid')
    if (not isinstance(proof['checks'], dict)
            or set(proof['checks']) != set(CHECKS)
            or any(proof['checks'][key] is not True for key in CHECKS)):
        raise VerificationFailure('Some required cross-replica checks are missing or false')
    hashes = proof['source_sha256']
    if not isinstance(hashes, dict) or set(hashes) != set(SOURCES):
        raise VerificationFailure('Cross-replica proof has incomplete source hashes')
    for rel in SOURCES:
        path = ROOT / rel
        if not path.is_file() or path.is_symlink():
            raise VerificationFailure('Required proof source not a regular file')
        if hashes[rel] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise VerificationFailure('Cross-replica evidence hashes are stale')


def main() -> int:
    try:
        report = execute()
        print(json.dumps({'validated': True, 'checks': report['checks'],
                          'scope': report['scope']}, indent=2))
        return 0
    except (VerificationFailure, OSError, ValueError) as exc:
        # Never print exception string from SDK, HTTP or file system.
        print(json.dumps({'validated': False,
                          'reason': 'Demo Flask/Firebase proof could not be completed',
                          'error_category': type(exc).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
