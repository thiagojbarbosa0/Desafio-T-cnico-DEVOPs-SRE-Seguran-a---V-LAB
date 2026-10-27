"""Private scrape authorization for the original CourseSphere Flask service.

The gateway MUST continue to deny /metrics. Inside the official Docker stack
Prometheus uses a per-installation bearer secret mounted as a Docker secret.
Never log the header or the secret, and never enable collection by default.
"""
from __future__ import annotations

import hmac
import ipaddress
import os
from pathlib import Path
from collections.abc import Mapping


def metrics_authorized(remote_addr: str | None, authorization: str | None,
                       *, env: Mapping[str, str] | None = None) -> bool:
    settings = os.environ if env is None else env
    if settings.get('COURSESPHERE_METRICS_ENABLED') != '1':
        return False
    # Existing localhost-only diagnostics remain possible without a secret.
    # Ignore X-Forwarded-For: proxies and clients can forge it.
    try:
        if remote_addr is not None and ipaddress.ip_address(remote_addr).is_loopback:
            return True
    except ValueError:
        pass
    secret_file = settings.get('COURSESPHERE_METRICS_TOKEN_FILE', '')
    if not secret_file or not authorization or not authorization.startswith('Bearer '):
        return False
    supplied = authorization[len('Bearer '):]
    if len(supplied) < 32 or len(supplied) > 1024 or any(c.isspace() for c in supplied):
        return False
    try:
        path = Path(secret_file)
        if not path.is_file() or path.stat().st_size > 4096:
            return False
        expected = path.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError, ValueError):
        return False
    if len(expected) < 32 or len(expected) > 1024 or any(c.isspace() for c in expected):
        return False
    return hmac.compare_digest(supplied.encode('utf-8'), expected.encode('utf-8'))
