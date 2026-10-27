"""Fail-closed V19.4 Flask WSGI integration runner with hashed source evidence."""
from __future__ import annotations
import hashlib
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/FLASK_AUTH_QUOTAS_V19_4.json'
SOURCES=[
    'backend/endpoints.py',
    'backend/cors_policy.py',
    'backend/observability.py',
    'backend/security_core.py',
    'backend/shared_quota.py',
    'integration/test_original_http_stubbed.py',
    'integration/test_v19_4_http_auth_and_quotas.py',
]


def run():
    suite=unittest.defaultTestLoader.loadTestsFromName('integration.test_v19_4_http_auth_and_quotas')
    sink=io.StringIO()
    result=unittest.TextTestRunner(stream=sink,verbosity=2).run(suite)
    print(sink.getvalue())
    validated=bool(result.wasSuccessful() and result.testsRun==7 and not result.skipped)
    hashes={str(path):hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCES}
    doc={
        'version':'V19.4', 'scope':'Flask WSGI requests with synthetic Firebase, not Firebase Emulator',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'validated':validated,
        'tests_run':result.testsRun,
        'failures':len(result.failures), 'errors':len(result.errors),
        'skipped':len(result.skipped),
        'source_sha256':hashes,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    print(f"Flask WSGI V19.4 validated={validated}, evidence={OUT.relative_to(ROOT)}")
    return 0 if validated else 1


if __name__=='__main__':
    raise SystemExit(run())
