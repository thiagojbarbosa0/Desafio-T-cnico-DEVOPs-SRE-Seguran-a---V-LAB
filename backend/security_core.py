"""Dependency-free security primitives used by the local CourseSphere lab.

The demo is NOT a substitute for production Firebase security rules.
"""
from __future__ import annotations
import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass

class SecurityError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def require_json_object(value):
    if not isinstance(value, dict):
        raise SecurityError("A JSON object is required")
    return value


def bounded_text(value, label: str, max_length: int = 3000, min_length: int = 0) -> str:
    if not isinstance(value, str):
        raise SecurityError(f"{label} must be text")
    result = value.strip()
    if not min_length <= len(result) <= max_length:
        raise SecurityError(f"{label} length is invalid")
    if any((ord(char) < 32 and char not in '\n\r\t')
           or 0xD800 <= ord(char) <= 0xDFFF for char in result):
        # Unpaired Unicode surrogates are not representable in UTF-8 and
        # would otherwise turn a valid request into a 500 during JSON output.
        raise SecurityError(f"{label} contains forbidden characters")
    return result


def safe_identifier(value, label="identifier") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise SecurityError(f"Invalid {label}")
    return value


def validate_profile(data: dict) -> dict:
    data = require_json_object(data)
    result = {}
    for name in ("majors", "minors", "courses"):
        items = data.get(name, [])
        if not isinstance(items, list) or len(items) > 40:
            raise SecurityError(f"{name} must be an array of at most 40 items")
        result[name] = [bounded_text(x, name, 100) for x in items]
    for name, limit in (("year", 30), ("college", 150), ("about", 1200)):
        result[name] = bounded_text(data.get(name, ""), name, limit)
    return result


def validate_messages(data):
    data = require_json_object(data)
    items = data.get("messages")
    if not isinstance(items, list) or len(items) > 100:
        raise SecurityError("messages must be an array of at most 100 entries")
    validated=[]
    seen_ids = set()
    for message in items:
        message = require_json_object(message)
        sender = bounded_text(message.get("sender", ""), "sender", 32, 1)
        if sender not in {"user", "bot", "human"}:
            raise SecurityError("Unknown message sender")
        message_id = safe_identifier(message.get("messageID", ""), "messageID")
        if message_id in seen_ids:
            raise SecurityError("Duplicate messageID in batch")
        seen_ids.add(message_id)
        validated.append({
            "sender": sender,
            "content": bounded_text(message.get("content", ""), "content", 4000, 1),
            "messageID": message_id,
            "timestamp": bounded_text(message.get("timestamp", ""), "timestamp", 64),
        })
    return validated


def validate_course(data):
    data=require_json_object(data)
    return {
        "title": bounded_text(data.get("title", ""), "title", 160, 3),
        "description": bounded_text(data.get("description", ""), "description", 2000),
    }


def validate_lesson(data):
    data=require_json_object(data)
    return {
        "title": bounded_text(data.get("title", ""), "title", 160, 3),
        "content": bounded_text(data.get("content", ""), "content", 5000),
    }


def extract_bearer(value: str | None) -> str:
    if not isinstance(value, str) or not value.startswith("Bearer "):
        raise SecurityError("Authentication required", 401)
    token = value[7:]
    if not token or len(token) > 4096 or any(c.isspace() for c in token):
        raise SecurityError("Invalid authorization header", 401)
    return token


def strict_json_loads(data: bytes):
    """Parse JSON objects without duplicate keys or non-JSON NaN/Infinity.

    Inconsistent parsers/proxies may otherwise interpret duplicate identity or
    permission fields differently. Return all remaining validation to the
    existing endpoint-specific validators.
    """
    def no_duplicate_keys(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise SecurityError("Duplicate JSON key")
            obj[key] = value
        return obj

    def reject_constant(value):
        raise SecurityError("Non-finite JSON constant")

    try:
        return json.loads(data, object_pairs_hook=no_duplicate_keys,
                          parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, SecurityError):
            raise
        raise SecurityError("Malformed JSON") from None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))

@dataclass(frozen=True)
class Principal:
    uid: str
    role: str


class DemoTokens:
    """Local-only HMAC tokens with expiry; never use with external network exposure."""
    def __init__(self, secret: str):
        if not isinstance(secret, str) or len(secret) < 32:
            raise ValueError("DEMO_SIGNING_KEY needs 32+ characters")
        self.secret = secret.encode()

    def issue(self, uid: str, role: str, ttl_seconds: int = 1800) -> str:
        if role not in {"student", "instructor", "admin"}:
            raise ValueError("Unknown role")
        if type(ttl_seconds) is not int or not -86400 <= ttl_seconds <= 86400:
            raise ValueError("Invalid demo token TTL")
        payload = {"uid": safe_identifier(uid), "role": role, "exp": int(time.time()) + ttl_seconds,
                   "nonce": secrets.token_hex(8)}
        body=_b64(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode())
        signature=_b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return body + '.' + signature

    def verify(self, token: str) -> Principal:
        """Verify canonical bounded demo JWT-like token, never Firebase tokens.

        Keep parsing size bounded before Base64/HMAC or JSON work; reject
        noncanonical encodings and duplicate JSON keys. HMAC is always checked
        before deserializing the untrusted payload.
        """
        def no_duplicates(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate token claim')
                result[key] = value
            return result

        try:
            if not isinstance(token, str) or not 1 <= len(token) <= 4096:
                raise ValueError('Invalid token length')
            body, signature = token.split('.')
            if (not 1 <= len(body) <= 3072 or len(signature) != 43
                    or not re.fullmatch(r'[A-Za-z0-9_-]+', body)
                    or not re.fullmatch(r'[A-Za-z0-9_-]{43}', signature)):
                raise ValueError('Noncanonical token')
            supplied = _unb64(signature)
            if len(supplied) != 32 or _b64(supplied) != signature:
                raise ValueError('Noncanonical signature')
            expected = hmac.new(self.secret, body.encode('ascii'), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, supplied):
                raise ValueError('Bad signature')
            raw = _unb64(body)
            if len(raw) > 2048 or _b64(raw) != body:
                raise ValueError('Noncanonical payload')
            payload = json.loads(raw, object_pairs_hook=no_duplicates)
            if not isinstance(payload, dict) or set(payload) != {'uid', 'role', 'exp', 'nonce'}:
                raise ValueError('Invalid token claims')
            if type(payload['exp']) is not int or payload['exp'] <= int(time.time()):
                raise ValueError('Expired')
            if payload['exp'] > int(time.time()) + 86400:
                raise ValueError('Unbounded expiration')
            if (not isinstance(payload['nonce'], str)
                    or not re.fullmatch(r'[a-f0-9]{16}', payload['nonce'])):
                raise ValueError('Invalid nonce')
            if payload['role'] not in {'student', 'instructor', 'admin'}:
                raise ValueError('Bad role')
            return Principal(uid=safe_identifier(payload['uid']), role=payload['role'])
        except (ValueError, TypeError, KeyError, UnicodeDecodeError,
                json.JSONDecodeError, binascii.Error, OverflowError):
            raise SecurityError('Invalid or expired token', 401) from None


def redact(text: str) -> str:
    """Redact common credential formats before emitting any user-controlled text."""
    text = re.sub(r"(?i)Bearer\s+[^\s\"']+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)(password|id_token|access_token|api_key)([\"']?\s*[:=]\s*[\"']?)[^\s,\"'}]+", r"\1\2[REDACTED]", text)
    return text[:800]
