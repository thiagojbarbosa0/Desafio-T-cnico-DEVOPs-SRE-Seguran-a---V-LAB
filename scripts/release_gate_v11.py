#!/usr/bin/env python3
"""Conservative, evidence-based V11 acceptance gates.

An HTTP test with synthetic Firebase may validate real Flask routing, but it
never establishes production Firebase behavior or complete pentest coverage.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_V11.json'


def read_json(path):
    try:
        data=json.loads((ROOT/path).read_text())
        return data if isinstance(data,dict) else {}
    except (OSError, ValueError):
        return {}


def evaluate():
    nginx=read_json('evidence/generated/NGINX_LIVE_V9.json')
    docker=read_json('evidence/runtime/DOCKER_STACK_V9.json')
    emulator=read_json('evidence/generated/FLASK_FIREBASE_EMULATORS_V10.json')
    http=read_json('evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V11.json')
    react=read_json('evidence/generated/FRONTEND_BUILD_V10.json')
    try:
        transcript=(ROOT/'evidence/generated/RESULTADO_TESTES_V11.txt').read_text()
    except OSError:
        transcript=''
    matches=re.findall(r'Ran (\d+) tests.*?\n\nOK\b',transcript,re.S)
    count=int(matches[-1]) if matches else 0
    passed_http=(http.get('validated') is True and http.get('tests_run') == 9
                 and http.get('failures') == 0 and http.get('errors') == 0
                 and http.get('skipped') == 0 and len(http.get('cases',{})) == 9)
    docker_checks=docker.get('tests',{})
    gates={
        'offline_python_regressions': {'passed':count>=121,
              'evidence':'evidence/generated/RESULTADO_TESTES_V11.txt',
              'note':f'{count} local unittest runs'},
        'nginx_actual_config_and_failover': {'passed':nginx.get('result')=='PASSED',
              'evidence':'evidence/generated/NGINX_LIVE_V9.json',
              'note':'Real Nginx with synthetic local APIs; not Docker'},
        'original_flask_http_with_stubbed_firebase': {'passed':passed_http,
              'evidence':'evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V11.json',
              'note':'Real Flask HTTP, intentionally synthetic Firebase: NOT production pentest'},
        'original_flask_and_local_firebase_emulators': {
              'passed':emulator.get('validated') is True and emulator.get('tests_run',0)>=15,
              'evidence':'evidence/generated/FLASK_FIREBASE_EMULATORS_V10.json',
              'note':'Actual Firebase Auth/RTDB Emulator HTTP suite'},
        'react_production_build': {'passed':react.get('validated') is True,
              'evidence':'evidence/generated/FRONTEND_BUILD_V10.json',
              'note':'Requires real npm ci && npm run build'},
        'docker_prometheus_grafana_failover': {
              'passed':docker.get('validated') is True
                and docker_checks.get('grafana_provisioned_dashboard')=='pass'
                and docker_checks.get('nginx_failover_after_api_a_stop',{}).get('result')=='pass',
              'evidence':'evidence/runtime/DOCKER_STACK_V9.json',
              'note':'Docker Compose two instances, real monitoring and failover'},
        'five_upstream_findings_two_categories_three_root_cause_fixes': {
              'passed':False,
              'evidence':'docs/RELATORIO_PENTEST_V11.md',
              'note':'Manual approval after correlating HTTP-before/after, impacts, categories, active original scope'},
        'upstream_redistribution_rights_and_secret_rotation': {
              'passed':False,
              'evidence':'docs/HANDOFF_MESTRE_V11.md',
              'note':'Human confirmation needed; never assume upstream license or rotation'},
    }
    return {'created_utc':datetime.now(timezone.utc).isoformat(),
      'method':'Binary evidence gates, not approval probability or completeness percent',
      'ready_for_submission':all(v['passed'] for v in gates.values()),
      'passing_gates':sum(x['passed'] for x in gates.values()),
      'total_gates':len(gates), 'gates':gates}


if __name__=='__main__':
    evidence=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(evidence,indent=2,ensure_ascii=False))
