"""Source-bound four-case R11 proof using REAL Flask and fake Firebase adapter."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'evidence/generated/FLASK_REPLICA_HEADERS_R11.json'
SOURCES=(
    'backend/endpoints.py','backend/request_correlation.py',
    'integration/test_r11_flask_replica_header.py',
    'integration/test_original_http_stubbed.py',
    'integration/run_r11_flask_replica_header.py',
)

def run():
    suite=unittest.defaultTestLoader.loadTestsFromName('integration.test_r11_flask_replica_header')
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    print(stream.getvalue())
    valid=result.wasSuccessful() and result.testsRun==4 and not result.skipped
    proof={
        'version':'R11-derived-V19.9',
        'validated':valid,
        'scope':'real Flask HTTP, Firebase mocked; NO distributed Firebase evidence',
        'tests_run':result.testsRun,'skipped':len(result.skipped),
        'failures':len(result.failures),'errors':len(result.errors),
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':{src:hashlib.sha256((ROOT/src).read_bytes()).hexdigest() for src in SOURCES},
        'additional_acceptance_points':0,
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
    return 0 if valid else 1

if __name__=='__main__': raise SystemExit(run())
