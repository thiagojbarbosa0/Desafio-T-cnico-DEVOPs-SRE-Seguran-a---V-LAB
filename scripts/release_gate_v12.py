#!/usr/bin/env python3
"""V12: conservative checks of independently generated release evidence.

This is NOT a security certification: it checks local artifacts and their origin.
Manual licensing, business context and production assumptions cannot be automated.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/RELEASE_GATE_V12.json'
EXPECTED_HTTP = 15
EXPECTED_EMULATOR = 23
MIN_OFFLINE = 124


def read_json(path):
    try:
        value = json.loads((ROOT / path).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_http_evidence(value):
    expected = {
        'original': ROOT / 'audit/baseline/endpoints_original.txt',
        'corrected': ROOT / 'backend/endpoints.py',
        'test_harness': ROOT / 'integration/test_original_http_stubbed.py',
        'security_core': ROOT / 'backend/security_core.py',
        'shared_quota': ROOT / 'backend/shared_quota.py',
        'cors_policy': ROOT / 'backend/cors_policy.py',
        'observability': ROOT / 'backend/observability.py',
    }
    digest = value.get('source_sha256', {})
    try:
        source_matches = all(digest.get(key) == sha256(path) for key, path in expected.items())
    except OSError:
        source_matches = False
    cases = value.get('cases', {})
    return (value.get('validated') is True and value.get('tests_run') == EXPECTED_HTTP
            and value.get('failures') == 0 and value.get('errors') == 0
            and value.get('skipped') == 0 and isinstance(cases, dict)
            and len(cases) == EXPECTED_HTTP and source_matches)


def validate_emulator_evidence(value):
    expected = {
        'endpoints': 'backend/endpoints.py',
        'firebase': 'backend/firebase.py',
        'firebase_configuration': 'backend/firebase_configuration.py',
        'security_core': 'backend/security_core.py',
        'shared_quota': 'backend/shared_quota.py',
        'cors_policy': 'backend/cors_policy.py',
        'rules': 'ops/firebase/database.rules.json',
        'emulator_harness': 'integration/test_official_emulators.py',
        'emulator_runner': 'integration/run_official_emulator_tests.py',
    }
    source_hashes = value.get('source_sha256', {})
    try:
        current_sources = all(source_hashes.get(name) == sha256(ROOT / path)
                              for name, path in expected.items())
    except OSError:
        current_sources = False
    return (current_sources and value.get('validated') is True
            and value.get('tests_run') == EXPECTED_EMULATOR
            and value.get('skipped') == 0 and value.get('failures') == 0
            and value.get('errors') == 0 and len(value.get('cases', {})) == EXPECTED_EMULATOR
            and value.get('project') == 'demo-coursesphere-vlab')


def evaluate():
    nginx = read_json('evidence/generated/NGINX_LIVE_V9.json')
    docker = read_json('evidence/runtime/DOCKER_STACK_V9.json')
    firebase = read_json('evidence/generated/FLASK_FIREBASE_EMULATORS_V12.json')
    flask = read_json('evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json')
    react = read_json('evidence/generated/FRONTEND_BUILD_V10.json')
    try:
        transcript = (ROOT / 'evidence/generated/RESULTADO_TESTES_V12.txt').read_text(encoding='utf-8')
    except OSError:
        transcript = ''
    matches = re.findall(r'Ran (\d+) tests.*?\n\nOK\b', transcript, re.S)
    count = int(matches[-1]) if matches else 0
    checks = docker.get('tests', {})
    gates = {
      'offline_python_regressions': {
        'passed': count >= MIN_OFFLINE,
        'evidence': 'evidence/generated/RESULTADO_TESTES_V12.txt',
        'note': f'{count} Python tests completed (threshold {MIN_OFFLINE})'},
      'nginx_actual_config_and_failover': {
        'passed': nginx.get('result') == 'PASSED'
                  and nginx.get('cases', {}).get('metrics_not_public', {}).get('result') == 'passed',
        'evidence': 'evidence/generated/NGINX_LIVE_V9.json',
        'note': 'Native Nginx + two synthetic Python instances, not Docker'},
      'original_flask_http_with_stubbed_firebase': {
        'passed': validate_http_evidence(flask),
        'evidence': 'evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json',
        'note': 'Real Flask HTTP only; Firebase and query manager synthetic; requires source SHA matches'},
      'original_flask_and_local_firebase_emulators': {
        'passed': validate_emulator_evidence(firebase),
        'evidence': 'evidence/generated/FLASK_FIREBASE_EMULATORS_V12.json',
        'note': 'Flask + Firebase Auth/Database local emulators, never production'},
      'react_production_build': {
        'passed': react.get('validated') is True,
        'evidence': 'evidence/generated/FRONTEND_BUILD_V10.json',
        'note': 'npm ci and React production build'},
      'docker_prometheus_grafana_failover': {
        'passed': docker.get('validated') is True
                  and checks.get('grafana_provisioned_dashboard') == 'pass'
                  and checks.get('nginx_failover_after_api_a_stop', {}).get('result') == 'pass',
        'evidence': 'evidence/runtime/DOCKER_STACK_V9.json',
        'note': 'Real Docker Compose, metrics, Grafana and failover'},
      'five_upstream_findings_and_three_root_cause_fixes': {
        'passed': False,
        'evidence': 'docs/RELATORIO_PENTEST_V12.md',
        'note': 'Manual sign-off on active app scope, independent reproduction, business impact and CVSS'},
      'redistribution_rights_and_upstream_secret_rotation': {
        'passed': False,
        'evidence': 'docs/HANDOFF_MESTRE_V12.md',
        'note': 'Requires consent/license verification and upstream credential-owner action'},
    }
    return {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'V12 acceptance evidence, NOT an approval prediction',
        'ready_for_submission': all(item['passed'] for item in gates.values()),
        'passing_gates': sum(item['passed'] for item in gates.values()),
        'total_gates': len(gates), 'gates': gates,
    }


if __name__ == '__main__':
    value = evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(value, indent=2, ensure_ascii=False))
