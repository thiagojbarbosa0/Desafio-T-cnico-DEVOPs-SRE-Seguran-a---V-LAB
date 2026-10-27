#!/usr/bin/env python3
"""Evidence of the R12 parser's OFFLINE tests (NOT Firebase/Flask runtime)."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
OUT='evidence/generated/R12_ORIGINAL_FLASK_STRICT_JSON_OFFLINE.json'
SOURCES=(
    'backend/endpoints.py','backend/security_core.py','backend/strict_request_json.py',
    'tests/test_r12_official_strict_json.py', 'tests/test_r12_release_gate.py',
    'tests/origin_harness.py',
    'integration/test_r12_flask_strict_json.py','integration/run_r12_flask_strict_json.py',
    'scripts/prove_r12_strict_json.py','scripts/release_gate_r12.py',
    '.github/workflows/ci.yml',
)
EXPECTED=22


def run(root:Path=ROOT):
    # Running the tests instead of inspecting a committed JSON proof prevents
    # stale metadata from being mistaken for a fresh execution.
    suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_r12_official_strict_json')
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    print(stream.getvalue())
    valid=result.wasSuccessful() and result.testsRun==EXPECTED and len(result.skipped)==0
    record={
        'version':'R12-derived-V19.9','validated':bool(valid),
        'scope':'standard-library strict JSON parser, offline only; no Flask/Firebase/Docker claims',
        'tests_run':result.testsRun,'skipped':len(result.skipped),
        'failures':len(result.failures),'errors':len(result.errors),
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':{src:hashlib.sha256((root/src).read_bytes()).hexdigest() for src in SOURCES},
        'additional_acceptance_points':0,
    }
    target=root/OUT
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'validated':valid,'tests_run':result.testsRun,'scope':'offline-only'}))
    return 0 if valid else 1


if __name__=='__main__':raise SystemExit(run())
