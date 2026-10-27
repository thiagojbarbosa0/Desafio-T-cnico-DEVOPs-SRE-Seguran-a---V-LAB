"""Fail-closed Flask+CORS WSGI runner with source-bound evidence."""
from __future__ import annotations
import hashlib
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/FLASK_CORS_RUNTIME_V19_6.json'
SOURCES = (
    'backend/endpoints.py',
    'backend/cors_policy.py',
    'integration/test_original_http_stubbed.py',
    'integration/test_v19_6_cors_runtime.py',
    'integration/run_v19_6_cors_runtime.py',
)
EXPECTED = 5


def run():
    suite = unittest.defaultTestLoader.loadTestsFromName('integration.test_v19_6_cors_runtime')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue())
    valid = bool(result.wasSuccessful() and result.testsRun == EXPECTED and not result.skipped)
    report = {
        'version': 'V19.6',
        'scope': 'real Flask/flask-cors WSGI; Firebase and QueryManager synthetic',
        'executed_utc': datetime.now(timezone.utc).isoformat(),
        'validated': valid,
        'tests_run': result.testsRun,
        'skipped': len(result.skipped),
        'errors': len(result.errors),
        'failures': len(result.failures),
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in SOURCES},
    }
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Flask CORS runtime validated=', valid)
    return 0 if valid else 1


if __name__ == '__main__':
    raise SystemExit(run())
