"""Scoped, fail-closed cleanup of the *temporary* R14 Firebase Emulator user.

Only the hard-coded loopback Auth/RTDB emulators of demo-coursesphere-vlab
are contacted. Never delete RTDB roots or other test users. Tokens and emails
are never logged or included in evidence artifacts.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import http.client
import json
import re

from backend.firebase_configuration import validate_emulators
from scripts.verify_official_replica_quota_r11 import VerificationFailure

PROJECT = 'demo-coursesphere-vlab'
UID_RE = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')


@dataclass(frozen=True)
class SyntheticAccount:
    uid: str
    token: str


def validate_account(account: SyntheticAccount) -> None:
    if not isinstance(account, SyntheticAccount) or not isinstance(account.uid, str) or not UID_RE.fullmatch(account.uid):
        raise VerificationFailure('Invalid synthetic Firebase UID')
    token = account.token
    if not isinstance(token, str) or not 30 <= len(token) <= 8192:
        raise VerificationFailure('Invalid synthetic Firebase token')
    try:
        parts = token.split('.')
        if len(parts) != 3 or not all(re.fullmatch('[A-Za-z0-9_-]+', p) for p in parts[:2]):
            raise ValueError('invalid JWT')
        raw = base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4))
        if len(raw) > 4096:
            raise ValueError('oversized JWT')
        def unique(pairs):
            result = {}
            for k, v in pairs:
                if k in result:
                    raise ValueError('duplicate JWT claim')
                result[k] = v
            return result
        claims = json.loads(raw, object_pairs_hook=unique)
        if (not isinstance(claims, dict) or claims.get('sub') != account.uid
                or claims.get('aud') != PROJECT
                or claims.get('iss') != 'https://securetoken.google.com/' + PROJECT):
            raise ValueError('claims not scoped to test user and project')
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise VerificationFailure('Synthetic token is not scoped to its emulator UID') from None


def _local_request(port: int, method: str, path: str, *, body: bytes | None = None,
                   token: str | None = None, timeout: float = 5.0) -> bytes:
    # All requests are built internally: no arbitrary URL/host/redirect follows.
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    headers = {'Connection': 'close'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        # Avoid persisting any error body, which could contain credentials.
        data = response.read(1025)
        if response.status not in (200, 204) or len(data) > 1024:
            raise VerificationFailure('Local Firebase Emulator fixture cleanup failed')
        return data
    except (OSError, http.client.HTTPException):
        raise VerificationFailure('Local Firebase Emulator fixture cleanup is unreachable') from None
    finally:
        conn.close()


def cleanup(account: SyntheticAccount, env: dict[str, str]) -> None:
    """Remove only one created UID's profile, quota and Auth account.

    A cleanup error invalidates the proof and is never reported as success.
    Auth deletion is last, allowing a retry while the temporary ID token exists.
    """
    required = {
        'COURSESPHERE_USE_FIREBASE_EMULATORS': '1',
        'GCLOUD_PROJECT': PROJECT,
        'FIREBASE_AUTH_EMULATOR_HOST': '127.0.0.1:9099',
        'FIREBASE_DATABASE_EMULATOR_HOST': '127.0.0.1:9000',
    }
    if any(env.get(k) != v for k, v in required.items()) or any(
        env.get(k) for k in ('FIREBASE_CREDENTIALS_FILE', 'FIREBASE_DATABASE_URL',
                             'GOOGLE_APPLICATION_CREDENTIALS')
    ):
        raise VerificationFailure('Fixture cleanup requires isolated loopback demo emulators')
    validate_emulators(PROJECT, required['FIREBASE_AUTH_EMULATOR_HOST'],
                       required['FIREBASE_DATABASE_EMULATOR_HOST'], '')
    validate_account(account)
    namespace = PROJECT + '-default-rtdb'
    key = hashlib.sha256(account.uid.encode('utf-8')).hexdigest()
    # Admin-only test owner token, over loopback; never in a URL, log or report.
    profile = f'/users/{account.uid}.json?ns={namespace}'
    quota = f'/server_security/rate_limits/{key}.json?ns={namespace}'
    _local_request(9000, 'DELETE', profile, token='owner')
    _local_request(9000, 'DELETE', quota, token='owner')
    # Deletion success codes alone are insufficient: prove both nodes are null.
    if (_local_request(9000, 'GET', profile, token='owner').strip() != b'null'
            or _local_request(9000, 'GET', quota, token='owner').strip() != b'null'):
        raise VerificationFailure('Scoped emulator data was not fully removed')
    body = json.dumps({'idToken': account.token}, separators=(',', ':')).encode('utf-8')
    _local_request(9099, 'POST', '/identitytoolkit.googleapis.com/v1/accounts:delete?key=demo-key',
                   body=body)
