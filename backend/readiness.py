"""Cached dependency-readiness decision; never reveal backend errors in HTTP output.

Liveness belongs to /health. Readiness is an explicit Auth + RTDB probe and
must fail closed. A short cache prevents a flood of expensive dependency RPCs
when multiple health checkers poll the same Flask worker simultaneously.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Callable


class DependencyReadiness:
    def __init__(self, ttl_seconds: float = 5.0):
        if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or not math.isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise ValueError('Readiness cache TTL must be positive and finite')
        self._ttl = float(ttl_seconds)
        self._lock = threading.Lock()
        self._checked_at: float | None = None
        self._healthy = False

    def ready(self, probe: Callable[[], object], *, now: float | None = None) -> bool:
        if not callable(probe):
            raise ValueError('Readiness probe must be callable')
        stamp = time.monotonic() if now is None else now
        if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
            raise ValueError('Invalid monotonic readiness clock')
        with self._lock:
            if self._checked_at is not None and 0 <= stamp - self._checked_at < self._ttl:
                return self._healthy
            try:
                # The probe MUST explicitly return True. Truthy strings, error
                # dictionaries, and incomplete results are not proof of health.
                healthy = probe() is True
            except Exception:
                healthy = False
            self._healthy = healthy
            self._checked_at = stamp
            return healthy
