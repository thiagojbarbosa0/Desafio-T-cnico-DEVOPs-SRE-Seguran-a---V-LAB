#!/usr/bin/env python3
"""Fail-closed HTTP proof of the ORIGINAL Flask profile quota across replicas.

ONLY a local Firebase Emulator with a synthetic user. Never authenticate to a
live Firebase project. Tokens stay in process memory, never in argv/reports.

Two distinct loopback sockets and two distinct server-generated replica labels
are required; a single proxy port returning round-robin responses is NOT proof.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import re
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
from backend.firebase_configuration import emulator_host, validate_emulators

ROOT = Path(__file__).resolve().parents[1]
OUT = 'evidence/generated/R11_OFFICIAL_FLASK_TWO_REPLICA_QUOTA.json'
SOURCES = (
    'backend/endpoints.py', 'backend/request_correlation.py',
    'backend/shared_quota.py', 'backend/firebase.py',
    'backend/firebase_configuration.py', 'backend/strict_request_json.py',
    'scripts/verify_official_replica_quota_r11.py',
    'scripts/release_gate_r11.py',
    'tests/test_r11_official_quota_proof.py',
    'tests/test_r11_release_gate.py',
    'integration/test_r11_flask_replica_header.py',
    'integration/run_r11_flask_replica_header.py',
    'integration/run_r13_two_replica_quota.py',
    'integration/emulator_fixture_cleanup_r14.py',
    'integration/test_official_emulators.py',
    'tests/test_r13_emulator_orchestrator.py',
    'tests/test_r14_scoped_fixture_cleanup.py',
    'tests/test_r14_proof_fail_closed.py',
    'tests/test_r14_official_emulator_fixture_scope.py',
    'scripts/release_gate_r14.py',
    'tests/test_r14_release_gate.py',
    'scripts/verify_official_emulators.sh',
    '.github/workflows/ci.yml',
)
EXPECTED = frozenset({'official_api_a', 'official_api_b'})
CHECKS = (
    'two_distinct_loopback_sockets',
    'two_distinct_identified_flask_replicas',
    'authenticated_reads_before_writes',
    'twenty_writes_alternating_replicas',
    'state_identical_on_both_replicas',
    'twenty_first_write_denied_on_both',
    'denials_preserve_persisted_data',
    'same_60_second_window',
)

class VerificationFailure(RuntimeError):
    pass


def parse_target(value: str):
    """Never let the attestation client send credentials to DNS or a redirect."""
    if not isinstance(value, str):
        raise VerificationFailure('Target must be an explicit local HTTP origin')
    try:
        u = urlsplit(value)
        if (u.scheme != 'http' or not u.hostname or not u.port
                or u.username is not None or u.password is not None
                or u.path not in ('', '/') or u.query or u.fragment):
            raise ValueError('unsafe origin')
        ip = ipaddress.ip_address(u.hostname)
        if not ip.is_loopback:
            raise ValueError('not loopback')
    except (ValueError, TypeError) as exc:
        raise VerificationFailure('Target must be a loopback IP with explicit port') from None
    return u.hostname, u.port


def validate_emulator_environment(env):
    if env.get('COURSESPHERE_USE_FIREBASE_EMULATORS') != '1':
        raise VerificationFailure('Firebase Emulator mode is required')
    project = env.get('GCLOUD_PROJECT', '')
    if not isinstance(project, str):
        raise VerificationFailure('A synthetic demo-* project is required')
    for key in ('FIREBASE_AUTH_EMULATOR_HOST', 'FIREBASE_DATABASE_EMULATOR_HOST'):
        try:
            emulator_host(env.get(key, ''), key)
        except RuntimeError:
            raise VerificationFailure('Both Firebase emulator hosts must be explicit loopback addresses') from None
    try:
        validate_emulators(project, env['FIREBASE_AUTH_EMULATOR_HOST'],
                           env['FIREBASE_DATABASE_EMULATOR_HOST'], '')
    except (RuntimeError, KeyError):
        raise VerificationFailure('Firebase Emulator project and hosts must pass strict configuration checks') from None
    token = env.get('COURSESPHERE_R11_FIREBASE_ID_TOKEN')
    if not isinstance(token, str) or not 30 <= len(token) <= 8192 or any(c.isspace() for c in token):
        raise VerificationFailure('Synthetic emulator token missing or invalid')
    try:
        pieces = token.split('.')
        if len(pieces) != 3 or any(not re.fullmatch(r'[A-Za-z0-9_-]+', p) for p in pieces[:2]):
            raise ValueError('bad token layout')
        payload_raw = base64.urlsafe_b64decode(pieces[1] + '=' * (-len(pieces[1]) % 4))
        if len(payload_raw) > 4096:
            raise ValueError('token payload oversized')
        def unique_claims(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate claim')
                result[key] = value
            return result
        claims = json.loads(payload_raw, object_pairs_hook=unique_claims)
        if (not isinstance(claims, dict) or claims.get('aud') != project
                or claims.get('iss') != 'https://securetoken.google.com/' + project
                or not isinstance(claims.get('sub'), str) or not claims['sub']):
            raise ValueError('token not scoped to synthetic emulator project')
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise VerificationFailure('Token claims do not match the expected demo-* emulator project') from None
    # This is a scope sanity check, NOT signature validation. Signature and
    # expiry are verified by the actual Flask/Firebase Admin backend.
    return token


def request(origin, method, path, token, payload=None):
    host, port = origin
    conn = http.client.HTTPConnection(host, port, timeout=4)
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json',
               'Connection': 'close'}
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True, separators=(',', ':')).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        replica = resp.getheader('X-CourseSphere-Replica', '')
        # Read boundedly. Never preserve response contents in the proof artifact.
        data = resp.read(65537)
        if len(data) > 65536:
            raise VerificationFailure('Unexpected oversized API response')
        if resp.status in (301, 302, 303, 307, 308):
            raise VerificationFailure('Redirects are forbidden for authenticated proofs')
        try:
            obj = json.loads(data)
        except (ValueError, UnicodeError):
            obj = None
        return resp.status, replica, obj
    except (OSError, http.client.HTTPException) as exc:
        # Never quote network/SDK exceptions: they may contain URL or headers.
        raise VerificationFailure('Local Flask replica unreachable or invalid HTTP') from None
    finally:
        conn.close()


def run(a_url, b_url, *, env=None, root=ROOT, client=request, clock=time.time):
    env = os.environ if env is None else env
    token = validate_emulator_environment(env)
    a, b = parse_target(a_url), parse_target(b_url)
    if a == b:
        raise VerificationFailure('The replica endpoints must be distinct')
    checks = {key: False for key in CHECKS}
    checks['two_distinct_loopback_sockets'] = True
    started = int(clock())
    # End the attempt before the minute rolls over; a boundary can hide a
    # broken limiter by granting a fresh 20-write window to both instances.
    if started % 60 >= 45:
        raise VerificationFailure('Start early in a UTC quota minute; window too close to ending')

    origin_label = {}

    def call(replica, method, payload=None):
        status, label, data = client(replica, method, '/users/info', token, payload)
        if label not in EXPECTED:
            raise VerificationFailure('Missing or invalid server-generated replica identity')
        if replica in origin_label and label != origin_label[replica]:
            raise VerificationFailure('Origin switched replica identity during quota proof')
        origin_label[replica] = label
        return status, label, data

    initial = [call(origin, 'GET') for origin in (a, b)]
    labels = {response[1] for response in initial}
    if labels != EXPECTED:
        raise VerificationFailure('The two origins did not identify two distinct Flask replicas')
    checks['two_distinct_identified_flask_replicas'] = True
    if any(status != 200 or (data is not None and not isinstance(data, dict))
           for status, _, data in initial):
        raise VerificationFailure('Both authenticated profile reads must succeed before writes')
    checks['authenticated_reads_before_writes'] = True
    nonce = 'r11-emulator-' + secrets.token_hex(12)
    for index in range(20):
        status, label, data = call((a, b)[index % 2], 'POST', {'about': nonce})
        if status != 200:
            raise VerificationFailure('Profile write failed before the documented limit of 20')
    checks['twenty_writes_alternating_replicas'] = True
    reads = [call(origin, 'GET') for origin in (a, b)]
    if any(status != 200 or not isinstance(data, dict) or data.get('about') != nonce
           for status, _, data in reads):
        raise VerificationFailure('Authenticated reads do not agree after allowed writes')
    checks['state_identical_on_both_replicas'] = True
    rejected = [call(origin, 'POST', {'about': nonce + '-denied'}) for origin in (a, b)]
    if any(status != 429 for status, _, _ in rejected):
        raise VerificationFailure('Shared quota failed: the 21st write was not denied on both replicas')
    checks['twenty_first_write_denied_on_both'] = True
    unchanged = [call(origin, 'GET') for origin in (a, b)]
    if any(status != 200 or not isinstance(data, dict) or data.get('about') != nonce
           for status, _, data in unchanged):
        raise VerificationFailure('Rejected writes changed the persisted user profile')
    checks['denials_preserve_persisted_data'] = True
    ended = int(clock())
    if started // 60 != ended // 60:
        raise VerificationFailure('Quota proof crossed a minute boundary; rerun with a fresh emulator user')
    checks['same_60_second_window'] = True
    return {
        'version': 'R11-derived-V19.9',
        'scope': 'two original Flask replicas + local Firebase Auth/RTDB emulators only',
        'validated': all(checks.values()), 'checks': checks,
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
                          for rel in SOURCES},
        'additional_acceptance_points': 0,
        'user_data_in_report': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replica-a', required=True, help='Direct loopback URL for official Flask replica A')
    p.add_argument('--replica-b', required=True, help='Direct loopback URL for official Flask replica B')
    p.add_argument('--out', default=OUT)
    args = p.parse_args(argv)
    output = ROOT / args.out
    try:
        proof = run(args.replica_a, args.replica_b)
        if not output.resolve().is_relative_to((ROOT / 'evidence/generated').resolve()):
            raise VerificationFailure('Report must remain within evidence/generated')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + '\n')
        print(json.dumps({'validated': proof['validated'], 'checks': proof['checks']}, indent=2))
        return 0
    except VerificationFailure as exc:
        # A failed run must not leave an old PASS behind.
        try:
            if output.resolve().is_relative_to((ROOT / 'evidence/generated').resolve()):
                output.unlink(missing_ok=True)
        except OSError:
            pass
        print(json.dumps({'validated': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
