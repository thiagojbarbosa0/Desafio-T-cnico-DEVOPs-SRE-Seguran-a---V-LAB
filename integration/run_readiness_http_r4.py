"""Exact-source provenance for a real Flask HTTP readiness proof.

Intentionally refuses to claim PASS when Flask is missing or any test is skipped.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
from integration.test_readiness_http_r4 import ReadinessHTTPR4

ROOT=Path(__file__).resolve().parents[1]
SOURCES=('backend/endpoints.py','backend/firebase.py','backend/readiness.py',
         'backend/observability.py','backend/metrics_access.py',
         'ops/nginx/gateway.official.conf','integration/test_readiness_http_r4.py',
         'integration/test_original_http_stubbed.py','integration/run_readiness_http_r4.py')

def main():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReadinessHTTPR4)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    validated=(result.wasSuccessful() and result.testsRun==9 and
               not result.skipped and not result.errors and not result.failures)
    proof={'version':'R5-on-V19.9-derived','validated':validated,
           'generated_utc':datetime.now(timezone.utc).isoformat(),
           'scope':'Real Flask HTTP/Werkzeug over loopback with Firebase synthetic adapter; no Docker, external Auth or RTDB',
           'source_sha256':{rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in SOURCES},
           'tests_run':result.testsRun,'skipped':len(result.skipped),
           'errors':len(result.errors),'failures':len(result.failures),
           'tests':{'flask_readiness_http':'pass' if validated else 'fail'}}
    out=ROOT/'evidence/generated/FLASK_READINESS_HTTP_R4.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'validated':validated,'tests_run':result.testsRun,'skipped':len(result.skipped)}))
    return 0 if validated else 1

if __name__=='__main__':sys.exit(main())
