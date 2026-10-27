"""Replicated-safe request quotas for authenticated CourseSphere endpoints.

Firebase Realtime Database transactions ensure that all Flask replicas debit the
same counter. Only Firebase Admin may write ``server_security``: client RTDB rules
must deny this path. Each user/action has ONE replaceable window record rather
than an unbounded collection of time buckets.

This is per-authenticated-UID abuse prevention, NOT an anonymous login brute-force
limiter or a substitute for edge protection against distributed DoS.
"""
from __future__ import annotations

import hashlib
import math
import time


class QuotaExceeded(Exception):
    """The caller exhausted its quota in the current fixed time window."""


class QuotaUnavailable(Exception):
    """Shared quota storage failed; fail closed rather than disable the limit."""


# Do not allow user-controlled path segments from a request or arbitrary routes.
LIMITS = {
    "recommendation": (30, 60),
    "message_id": (120, 60),
    "chat_write": (60, 60),
    "profile_write": (20, 60),
    "chat_delete": (30, 60),
}


def debit(reference_factory, uid: str, action: str, *, now: float | None = None) -> bool:
    """Atomically consume one quota unit and return True if accepted.

    ``reference_factory`` is called with a known server-owned database path and
    must return an object implementing Firebase RTDB ``transaction``.  Rejected
    requests also commit unchanged state; there is no TOCTOU get+write window.
    """
    if action not in LIMITS:
        raise ValueError("Unknown quota action")
    if not isinstance(uid, str) or not uid or len(uid) > 512:
        raise ValueError("Invalid UID")
    limit, period = LIMITS[action]
    # Explicit test clocks are inputs, not an opportunity to bypass the
    # shared limiter with NaN, infinity, booleans or absurdly large integers.
    clock = time.time() if now is None else now
    if type(clock) not in (float, int) or not math.isfinite(clock) or clock < 0 or clock > 253402300799:
        if now is None:
            raise QuotaUnavailable("Quota clock unavailable")
        raise ValueError('Invalid quota clock')
    stamp = int(clock)
    window = stamp // period
    key = hashlib.sha256(uid.encode('utf-8')).hexdigest()
    path = f"server_security/rate_limits/{key}/{action}"
    rejected = False

    def update(current):
        nonlocal rejected
        if current is None:
            current_count = 0
        elif not isinstance(current, dict):
            # Corrupted RTDB state is not a reason to re-open a full quota.
            rejected = True
            return current
        else:
            previous_window = current.get('window')
            if type(previous_window) is not int or previous_window < 0:
                rejected = True
                return current
            if previous_window > window:
                # Another replica with a clock ahead has already established a
                # newer window. Do not roll it backwards and reset the counter.
                rejected = True
                return current
            count = current.get('count')
            if type(count) is not int or count < 0 or count > limit:
                # Do not silently heal corrupted state by rolling the window.
                # Operators must repair bad data through a controlled process.
                rejected = True
                return current
            if previous_window < window:
                current_count = 0
            else:
                current_count = count
        # Firebase may replay this callback if the transaction conflicts; only
        # the final committed result decides whether the request is permitted.
        rejected = current_count >= limit
        return {'window': window, 'count': current_count if rejected else current_count + 1}

    try:
        final = reference_factory(path).transaction(update)
    except Exception as exc:
        raise QuotaUnavailable("Shared rate limiter unavailable") from exc
    return (not rejected and isinstance(final, dict)
            and final.get('window') == window
            and type(final.get('count')) is int and 1 <= final['count'] <= limit)
