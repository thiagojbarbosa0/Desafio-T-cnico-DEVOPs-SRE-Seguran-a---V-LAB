"""Strict JSON ingress for the ORIGINAL Flask API.

This module is deliberately standard-library-only and can be tested without
Flask or Firebase. Flask MAX_CONTENT_LENGTH remains the transport size limit;
we also reject oversized byte strings if this parser is called independently.
"""
from __future__ import annotations

import json
import math
from security_core import SecurityError

MAX_JSON_BYTES = 32 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 4096


def parse_object(raw: bytes, mimetype: str | None) -> dict:
    """Decode exactly one JSON object, rejecting ambiguity and Unicode hazards.

    No request identifiers, raw payload fragments, or parser exceptions are
    returned to clients or logs. Errors are suitable for SecurityError handlers.
    """
    if mimetype != 'application/json':
        raise SecurityError('Content-Type application/json required', 415)
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_JSON_BYTES:
        raise SecurityError('Malformed or oversized JSON', 400 if not raw else 413)

    def unique_keys(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise SecurityError('Duplicate JSON key')
            obj[key] = value
        return obj

    def no_constants(_value):
        raise SecurityError('Non-finite JSON constant')

    try:
        obj = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_keys,
                         parse_constant=no_constants)
    except SecurityError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise SecurityError('Malformed JSON') from None
    if not isinstance(obj, dict):
        raise SecurityError('JSON object required')

    # This also detects 1e9999 (Python float infinity), unpaired Unicode
    # surrogates in nested values/keys, and deeply nested JSON structures.
    nodes = 0
    stack = [(obj, 0)]
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            raise SecurityError('JSON structure exceeds limits')
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for key, child in value.items()
                         for item in (key, child))
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
        elif isinstance(value, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
                raise SecurityError('Invalid Unicode in JSON')
        elif isinstance(value, float) and not math.isfinite(value):
            raise SecurityError('Non-finite JSON number')
    return obj
