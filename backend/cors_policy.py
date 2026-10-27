"""Strict, explicit browser-origin policy for the official CourseSphere Flask API.

CORS is a browser access control, NOT authentication or authorization.  These
checks prevent accidental wildcard/invalid origins from being silently enabled
through deployment configuration.  HTTP is allowed only for loopback development.
"""
from __future__ import annotations

from urllib.parse import urlsplit

LOOPBACK_HOSTS = frozenset({'localhost', '127.0.0.1', '::1'})
DEFAULT_ORIGIN = 'http://localhost:5173'


def parse_allowed_origins(raw: str | None) -> tuple[str, ...]:
    """Validate a comma-separated list of absolute, path-free web origins.

    Refuse to start under ambiguous/insecure settings rather than turn a
    configuration typo into cross-site exposure.  Does not interpret wildcards,
    regexes, credentials, opaque origins, query strings or path prefixes.
    """
    if raw is None:
        raw = DEFAULT_ORIGIN
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('ALLOWED_ORIGINS requires at least one explicit origin')
    entries = [item.strip() for item in raw.split(',')]
    if not 1 <= len(entries) <= 16 or any(not item for item in entries):
        raise ValueError('ALLOWED_ORIGINS must have 1-16 nonempty origins')
    validated = []
    for item in entries:
        if len(item) > 256 or any(ch.isspace() for ch in item) or '*' in item:
            raise ValueError('Invalid or wildcard CORS origin')
        try:
            parsed = urlsplit(item)
            port = parsed.port  # Forces malformed ports to raise ValueError.
            host = parsed.hostname
        except ValueError as exc:
            raise ValueError('Invalid CORS origin') from exc
        if (parsed.scheme not in {'http', 'https'} or not host
                or parsed.username is not None or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment
                or (parsed.netloc.endswith(':') and port is None)):
            raise ValueError('CORS origin must be scheme + host + optional port only')
        if parsed.scheme == 'http' and host.lower() not in LOOPBACK_HOSTS:
            raise ValueError('Non-loopback CORS origins must use HTTPS')
        # Reject confusing case-folding, port-0 and trailing dots.  CORS
        # compares serialized origin strings, so keep one canonical spelling.
        if (host != host.lower() or host.endswith('.') or port == 0
                or (parsed.scheme == 'https' and port == 443)
                or (parsed.scheme == 'http' and port == 80)):
            raise ValueError('CORS origin hostname/port must be canonical')
        canonical_host = f'[{host}]' if ':' in host else host
        canonical = f'{parsed.scheme}://{canonical_host}'
        if port is not None:
            canonical += f':{port}'
        if canonical != item:
            raise ValueError('CORS origin must be canonical')
        if item not in validated:
            validated.append(item)
    return tuple(validated)
