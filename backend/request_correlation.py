"""Bounded, privacy-safe gateway-to-Flask request correlation.

The gateway overwrites X-Request-ID before forwarding. Only a private backend
with COURSESPHERE_TRUST_GATEWAY_REQUEST_ID=1 should trust the forwarded value.
Unknown/invalid identifiers are always replaced with fresh random identifiers.
No token, URL, address or user identifier is embedded.
"""
from __future__ import annotations
import re
import uuid

_NGINX_REQUEST_ID = re.compile(r"^[0-9a-fA-F]{32}$")
_REPLICA_IDS = frozenset({"official_api_a", "official_api_b"})


def correlation_id(incoming: object, *, trust_gateway: bool = False) -> str:
    if (trust_gateway and isinstance(incoming, str)
            and _NGINX_REQUEST_ID.fullmatch(incoming)):
        return incoming.lower()
    return uuid.uuid4().hex


def replica_label(value: object) -> str:
    """A fixed allowlist keeps telemetry labels bounded and non-user-controlled."""
    return value if isinstance(value, str) and value in _REPLICA_IDS else 'unknown'
