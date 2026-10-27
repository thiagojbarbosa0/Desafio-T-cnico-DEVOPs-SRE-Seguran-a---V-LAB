"""Fail-closed eight-case real Flask WSGI metrics evidence with source hashes."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/FLASK_METRICS_AUTH_V19_8.json'
SOURCES=(
    'backend/endpoints.py','backend/metrics_access.py','backend/observability.py',
    'backend/firebase.py','backend/firebase_configuration.py','backend/readiness.py',
    'integration/test_original_http_stubbed.py','integration/test_v19_8_metrics_runtime.py',
    'integration/run_v19_8_metrics_runtime.py',
)
EXPECTED=8


def run():
    suite=unittest.defaultTestLoader.loadTestsFromName('integration.test_v19_8_metrics_runtime')
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    print(output.getvalue())
    good=result.wasSuccessful() and result.testsRun==EXPECTED and len(result.skipped)==0
    evidence={
        'version':'V19.8','scope':'Real Flask WSGI metrics authentication with synthetic Firebase; no Docker',
        'validated':bool(good),'tests_run':result.testsRun,'skipped':len(result.skipped),
        'errors':len(result.errors),'failures':len(result.failures),
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in SOURCES},
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(evidence,indent=2)+'\n')
    return 0 if good else 1


if __name__=='__main__': raise SystemExit(run())
