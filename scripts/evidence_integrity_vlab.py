#!/usr/bin/env python3
"""Defensive, read-only verifier for CourseSphere evidence artifacts.

This verifies reported source hashes against an actual checkout. It DOES NOT
attest to a Docker image, establish the identity of an executor, or award points.
A generated JSON report must never be promoted solely because it says validated.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

SHA256 = re.compile(r'^[0-9a-f]{64}$')
MAX_JSON_BYTES = 3_000_000

class EvidenceError(ValueError):
    pass


def _unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise EvidenceError('duplicate JSON key rejected: '+k)
        obj[k] = v
    return obj


def load_json(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise EvidenceError('missing, symlinked, or oversized JSON artifact')
    try:
        data = json.loads(path.read_text('utf-8'), object_pairs_hook=_unique,
                          parse_constant=lambda x: (_ for _ in ()).throw(EvidenceError('nonfinite JSON number')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError('malformed JSON artifact') from exc
    if not isinstance(data, dict):
        raise EvidenceError('root JSON must be an object')
    return data


def safe_relative(root: Path, rel: str) -> Path:
    """Reject all forms of traversal and symlink hops; avoid untrusted evidence paths."""
    if not isinstance(rel, str) or '\\' in rel or rel.startswith('/') or '\x00' in rel:
        raise EvidenceError('unsafe source path')
    parts = PurePosixPath(rel).parts
    if not parts or any(x in {'.', '..'} for x in rel.split('/')) or ':' in parts[0]:
        raise EvidenceError('unsafe source path')
    root = root.resolve(strict=True)
    path = root
    for segment in parts:
        path = path / segment
        if path.is_symlink():
            raise EvidenceError('symlink found along evidence source path')
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise EvidenceError('source file missing or escapes checkout')
    return path


def verify(root: Path, evidence: dict, *, version: str,
           required_sources: tuple[str, ...], required_tests: tuple[str, ...] = (),
           runtime: bool = False, max_age_hours: int | None = None) -> dict:
    failures = []
    if not required_sources or len(set(required_sources)) != len(required_sources):
        failures.append('invalid_expected_sources')
    if evidence.get('version') != version:
        failures.append('wrong_version')
    if evidence.get('validated') is not True:
        failures.append('not_validated')
    source_hashes = evidence.get('source_sha256')
    if not isinstance(source_hashes, dict) or not source_hashes:
        failures.append('missing_source_hashes')
        source_hashes = {}
    # No arbitrary paths supplied by evidence: only compare the caller's allowlisted files.
    for rel in required_sources:
        try:
            expected = source_hashes.get(rel)
            if not isinstance(expected, str) or not SHA256.fullmatch(expected):
                failures.append('bad_hash:'+rel)
                continue
            actual = hashlib.sha256(safe_relative(root, rel).read_bytes()).hexdigest()
            if actual != expected:
                failures.append('stale_source:'+rel)
        except (EvidenceError, OSError):
            failures.append('source_unavailable:'+rel)
    tests = evidence.get('tests')
    if required_tests and not isinstance(tests, dict):
        failures.append('missing_test_results')
    elif required_tests:
        for item in required_tests:
            if tests.get(item) != 'pass':
                failures.append('required_test_not_passed:'+item)
    if runtime:
        # Requires an explicit container freshness proof from the modern 19.14+
        # verifier. A host source digest or a test count is NOT a replacement.
        if not isinstance(tests, dict) or tests.get('deployed_source_freshness') != 'pass':
            failures.append('no_container_source_attestation')
    if max_age_hours is not None:
        try:
            stamp = datetime.fromisoformat(evidence['generated_utc'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('naive timestamp')
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            if age < -300 or age > max_age_hours * 3600:
                failures.append('evidence_outside_time_window')
        except (KeyError, ValueError, TypeError, AttributeError):
            failures.append('bad_timestamp')
    return {'validated': not failures, 'failures': failures,
            'source_files_compared': len(required_sources),
            'runtime_claim_checked': runtime,
            'scope': 'Evidence consistency only; no Docker, browser or Firebase execution implied.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--evidence', required=True, help='path relative to root')
    p.add_argument('--version', required=True)
    p.add_argument('--source', action='append', required=True, help='expected relative source file; repeatable')
    p.add_argument('--test', action='append', default=[], help='required test key with value pass')
    p.add_argument('--require-runtime-attestation', action='store_true')
    p.add_argument('--max-age-hours', type=int)
    p.add_argument('--output', type=Path, help='optional sanitized JSON output')
    args = p.parse_args(argv)
    try:
        evidence_path = safe_relative(args.root, args.evidence)
        report = verify(args.root, load_json(evidence_path), version=args.version,
                        required_sources=tuple(args.source), required_tests=tuple(args.test),
                        runtime=args.require_runtime_attestation,
                        max_age_hours=args.max_age_hours)
    except (EvidenceError, OSError) as exc:
        report = {'validated':False, 'failures':['preflight:'+type(exc).__name__],
                  'scope':'Evidence consistency only'}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['validated'] else 1

if __name__ == '__main__':
    sys.exit(main())
