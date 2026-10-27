"""Evidence runner: requires real Flask, strictly fails if tests are skipped."""
from __future__ import annotations
import json
import hashlib
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from integration.test_original_http_stubbed import OriginalHTTPBeforeAfter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json'


def main():
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(OriginalHTTPBeforeAfter)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    valid = result.wasSuccessful() and result.testsRun == 15 and not result.skipped
    evidence = {
        'scope': 'Original and corrected Flask HTTP routes, synthetic Firebase adapter',
        'not_tested': ['real Firebase Emulator', 'live original deployment', 'production credentials'],
        'http_transport': 'real Werkzeug server over 127.0.0.1',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'validated': valid,
        'source_sha256': {
            label: hashlib.sha256(path.read_bytes()).hexdigest()
            for label, path in {
                'original': ROOT / 'audit/baseline/endpoints_original.txt',
                'corrected': ROOT / 'backend/endpoints.py',
                'test_harness': ROOT / 'integration/test_original_http_stubbed.py',
                'security_core': ROOT / 'backend/security_core.py',
                'shared_quota': ROOT / 'backend/shared_quota.py',
                'cors_policy': ROOT / 'backend/cors_policy.py',
                'observability': ROOT / 'backend/observability.py',
            }.items()
        },
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'duration_seconds': round(time.monotonic()-started,2),
        'cases': OriginalHTTPBeforeAfter.results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'Original Flask before/after HTTP validated={valid}; evidence={OUT}')
    return 0 if valid else 1

if __name__=='__main__':
    sys.exit(main())
