"""Run official Firebase emulator HTTP tests and report truthful pass/fail evidence."""
import json
import hashlib
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/FLASK_FIREBASE_EMULATORS_V12.json'


def main():
    begin=time.monotonic()
    suite=unittest.defaultTestLoader.loadTestsFromName('integration.test_official_emulators')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    try:
        from integration.test_official_emulators import OfficialFlaskFirebaseEmulatorIntegration as Tests
        cases=Tests.results if hasattr(Tests,'results') else {}
    except Exception:
        cases={}
    artifact={
        'scope':'Original CourseSphere Flask HTTP + Firebase Auth/RTDB local emulators',
        'project':'demo-coursesphere-vlab',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'validated':result.wasSuccessful() and result.testsRun == 23 and not result.skipped and len(cases) == 23,
        'source_sha256': {name: hashlib.sha256((ROOT / location).read_bytes()).hexdigest()
            for name, location in {
                'endpoints': 'backend/endpoints.py',
                'firebase': 'backend/firebase.py',
                'firebase_configuration': 'backend/firebase_configuration.py',
                'security_core': 'backend/security_core.py',
                'shared_quota': 'backend/shared_quota.py',
                'cors_policy': 'backend/cors_policy.py',
                'rules': 'ops/firebase/database.rules.json',
                'emulator_harness': 'integration/test_official_emulators.py',
                'emulator_runner': 'integration/run_official_emulator_tests.py',
            }.items()},
        'tests_run':result.testsRun,
        'expected_tests':23,
        'failures':len(result.failures),
        'errors':len(result.errors),
        'skipped':len(result.skipped),
        'duration_seconds':round(time.monotonic()-begin,3),
        'cases':cases,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+'\n')
    print(f'Integration evidence: {OUT} / validated={artifact["validated"]}')
    return 0 if artifact['validated'] else 1

if __name__=='__main__':
    sys.exit(main())
