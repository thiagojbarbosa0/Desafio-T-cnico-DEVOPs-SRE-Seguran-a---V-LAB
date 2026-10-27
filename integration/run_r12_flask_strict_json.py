"""R12 proof: original Flask HTTP JSON semantics, synthetically mocked Firebase.

Must execute with real Flask/Flask-Cors. A skipped test suite is NOT a pass.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/R12_ORIGINAL_FLASK_STRICT_JSON_HTTP.json'
SOURCES=(
    'backend/endpoints.py','backend/strict_request_json.py',
    'integration/test_r12_flask_strict_json.py',
    'integration/run_r12_flask_strict_json.py',
)
EXPECTED=8


def run():
    suite=unittest.defaultTestLoader.loadTestsFromName('integration.test_r12_flask_strict_json')
    buffer=io.StringIO()
    results=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
    print(buffer.getvalue())
    valid=results.wasSuccessful() and results.testsRun==EXPECTED and not results.skipped
    record={
        'version':'R12-derived-V19.9','validated':valid,
        'scope':'original Flask HTTP + synthetic Firebase; NOT real emulators',
        'tests_run':results.testsRun,'skipped':len(results.skipped),
        'failures':len(results.failures),'errors':len(results.errors),
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES},
        'additional_acceptance_points':0,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(record,indent=2)+'\n')
    return 0 if valid else 1


if __name__ == '__main__':raise SystemExit(run())
