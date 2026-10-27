"""Dependency-free, low-cardinality Prometheus instrumentation for the ORIGINAL Flask app.

No IDs, user queries, tokens or raw URLs become metric labels. Metrics are
per-process. Production deployments must scrape each replica independently.
"""
from __future__ import annotations
from collections import Counter
import math
import threading

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


def _escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


class HTTPMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counts = Counter()
        self._bucket_counts = Counter()
        self._sums = Counter()
        self._observations = Counter()
        self._auth_attempts = Counter()
        # None = never probed; zero is an observed dependency failure.
        self._firebase_ready: int | None = None

    def observe(self, method: str, route: str, status: int, duration_seconds: float) -> None:
        """Use Flask URL RULE (not actual URL) to prevent unbounded labels."""
        if not isinstance(route, str) or len(route) > 120 or not route.startswith('/'):
            route = 'unmatched'
        method = method.upper() if isinstance(method, str) else 'OTHER'
        if method not in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT'}:
            method = 'OTHER'
        status_class = f'{status // 100}xx' if 100 <= status <= 599 else 'other'
        # Never render NaN/Inf into Prometheus; invalid timing must not cause
        # after_request logging itself to turn an otherwise valid HTTP result
        # into an internal error. Normal monotonic timers always stay finite.
        try:
            duration_seconds = float(duration_seconds)
        except (TypeError, ValueError, OverflowError):
            duration_seconds = 0.0
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            duration_seconds = 0.0
        key = (route, method, status_class)
        with self._lock:
            self._counts[key] += 1
            self._sums[key] += duration_seconds
            self._observations[key] += 1
            for boundary in BUCKETS:
                if duration_seconds <= boundary:
                    self._bucket_counts[(key, boundary)] += 1

    def observe_auth(self, result: str, route: str) -> None:
        """Record only bounded authentication outcomes, never UIDs or tokens."""
        if result not in {"accepted", "denied"}:
            raise ValueError("Invalid authentication result")
        if not isinstance(route, str) or len(route) > 120 or not route.startswith("/") or "?" in route:
            route = "unmatched"
        with self._lock:
            self._auth_attempts[(result, route)] += 1

    def set_firebase_readiness(self, ready: bool) -> None:
        """Record the outcome of a private dependency probe without labels.

        Scrapes must be authorized before calling the probe. A failed Firebase
        check does not make /metrics fail; Prometheus needs a valid 0 gauge in
        order to distinguish a failed dependency from an unreachable replica.
        """
        if type(ready) is not bool:
            raise ValueError('Readiness observation must be a boolean')
        with self._lock:
            self._firebase_ready = int(ready)

    def render(self) -> str:
        with self._lock:
            counts = dict(self._counts)
            buckets = dict(self._bucket_counts)
            sums = dict(self._sums)
            observed = dict(self._observations)
            auth_attempts = dict(self._auth_attempts)
            firebase_ready = self._firebase_ready
        result = [
            '# HELP coursesphere_original_http_requests_total Total original Flask HTTP requests.',
            '# TYPE coursesphere_original_http_requests_total counter',
        ]
        for key in sorted(counts):
            labels = _labels(key)
            result.append(f'coursesphere_original_http_requests_total{{{labels}}} {counts[key]}')
        result += [
            '# HELP coursesphere_original_http_duration_seconds Original Flask route latency.',
            '# TYPE coursesphere_original_http_duration_seconds histogram',
        ]
        for key in sorted(observed):
            labels = _labels(key)
            for boundary in BUCKETS:
                result.append(f'coursesphere_original_http_duration_seconds_bucket{{{labels},le="{boundary}"}} {buckets.get((key, boundary), 0)}')
            result.append(f'coursesphere_original_http_duration_seconds_bucket{{{labels},le="+Inf"}} {observed[key]}')
            result.append(f'coursesphere_original_http_duration_seconds_sum{{{labels}}} {sums[key]:.9f}')
            result.append(f'coursesphere_original_http_duration_seconds_count{{{labels}}} {observed[key]}')
        result += [
            '# HELP coursesphere_original_auth_attempts_total Firebase token verification outcomes.',
            '# TYPE coursesphere_original_auth_attempts_total counter',
        ]
        for (outcome, route), count in sorted(auth_attempts.items()):
            result.append(f'coursesphere_original_auth_attempts_total{{result="{_escape(outcome)}",route="{_escape(route)}"}} {count}')
        # No UID, URL, token or Firebase error is ever emitted as a label.
        # Absence means the first authorized scrape has not happened yet.
        result.extend([
            '# HELP coursesphere_original_firebase_ready Firebase Auth and RTDB last probe (1=ready, 0=degraded).',
            '# TYPE coursesphere_original_firebase_ready gauge',
        ])
        if firebase_ready is not None:
            result.append(f'coursesphere_original_firebase_ready {firebase_ready}')
        return '\n'.join(result) + '\n'


def _labels(key: tuple[str, str, str]) -> str:
    route, method, status_class = key
    return f'route="{_escape(route)}",method="{_escape(method)}",status_class="{_escape(status_class)}"'
