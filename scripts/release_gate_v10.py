#!/usr/bin/env python3
"""Evidence-driven release gate for the CourseSphere V-Lab challenge.

A feature is never marked complete based solely on a config file or a script.
Production and original-app pentest readiness require separate real evidence.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_V10.json'

def read_json(rel):
    try: return json.loads((ROOT/rel).read_text())
    except (OSError,ValueError): return {}

def evaluate():
    nginx=read_json('evidence/generated/NGINX_LIVE_V9.json')
    docker=read_json('evidence/runtime/DOCKER_STACK_V9.json')
    emulator=read_json('evidence/generated/FLASK_FIREBASE_EMULATORS_V10.json')
    frontend=read_json('evidence/generated/FRONTEND_BUILD_V10.json')
    try: tests=(ROOT/'evidence/generated/RESULTADO_TESTES_V10.txt').read_text()
    except OSError: tests=''
    matches=re.findall(r'Ran (\d+) tests.*?\n\nOK\b',tests,re.S)
    count=int(matches[-1]) if matches else 0
    gates={
        'offline_python_tests':{'passed':count>=103,'details':f'{count} tests recorded'},
        'native_nginx_load_and_failover':{'passed':nginx.get('result')=='PASSED',
                                          'details':'local synthetic gateway, not Docker'},
        'original_flask_firebase_emulator_http':{'passed':emulator.get('validated') is True,
                                                 'details':f"{emulator.get('tests_run',0)} emulator HTTP tests"},
        'react_production_build':{'passed':frontend.get('validated') is True,
                                  'details':'npm ci + npm run build must succeed'},
        'docker_observability_and_failover':{'passed':docker.get('validated') is True and
          docker.get('tests',{}).get('grafana_provisioned_dashboard')=='pass' and
          docker.get('tests',{}).get('nginx_failover_after_api_a_stop',{}).get('result')=='pass',
          'details':'real Docker + Grafana provisioned + failover evidence'},
        'original_five_finding_http_before_after':{'passed':False,
            'details':'5 original-app findings across 2+ categories with before/after HTTP proofs not yet collected'},
        'license_and_credential_owner_clearance':{'passed':False,
            'details':'requires human verification of source redistribution permission and secret revocation'},
    }
    return {'scope':'CourseSphere V-Lab acceptance gate; no approval probability implied',
       'created_utc':datetime.now(timezone.utc).isoformat(), 'ready_for_final_submission':all(v['passed'] for v in gates.values()),
       'passing_gates':sum(v['passed'] for v in gates.values()),'total_gates':len(gates),'gates':gates}

if __name__=='__main__':
    artifact=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(artifact,indent=2,ensure_ascii=False))
