#!/usr/bin/env python3
"""V19.3: strengthen the native-Nginx gate with privacy proofs.

Preserve V19's historic 100-point weighted model, but require the CURRENT
Nginx evidence to demonstrate token-query rejection, no forwarded query
strings, and structured query-free access logs. No score is inferred from
source-code presence alone. This is NOT a selection probability.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v19 import evaluate as previous
from scripts.release_gate_v13 import valid_nginx, read_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_V19_3.json'


def valid_edge_privacy(value):
    if not valid_nginx(value):
        return False
    tests=value.get('cases',{})
    redaction=tests.get('query_free_structured_edge_logs',{})
    return (tests.get('query_token_blocked_at_edge',{}).get('status')==401
            and tests.get('query_token_blocked_at_edge',{}).get('result')=='passed'
            and tests.get('all_api_query_strings_blocked',{}).get('status')==400
            and tests.get('all_api_query_strings_blocked',{}).get('result')=='passed'
            and redaction.get('result')=='passed'
            and type(redaction.get('entries_checked')) is int
            and redaction['entries_checked']>=1)


def evaluate():
    report=previous()
    report['version']='V19.3'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    native=read_json('evidence/generated/NGINX_LIVE_V9.json')
    privacy_ok=valid_edge_privacy(native)
    nginx_gate=report['gates']['nginx_real_failover']
    nginx_gate['passed']=privacy_ok
    nginx_gate['reason']=('Nginx real com duas réplicas, failover, métricas privadas e '
                           'bloqueio de query com logs sem parâmetros')
    report['weighted_acceptance_verified_percent']=sum(
        item['weight'] for item in report['gates'].values() if item['passed'])
    report['gates_passed']=sum(int(item['passed']) for item in report['gates'].values())
    report['ready_for_submission']=report['weighted_acceptance_verified_percent']==100
    report['new_privacy_boundary']={
        'native_nginx_synthetic_token_and_log_redaction_passed':privacy_ok,
        'original_flask_nginx_stubbed':report['supplemental_original_flask_nginx']['validated'],
        'scope':'Only native Nginx demonstrator executed locally; Docker and Firebase not inferred',
    }
    report['emulator_suite_expected_tests']=23
    report['implementation_readiness_estimate_percent']=69
    report['implementation_readiness_note']=(
        'Estimativa qualitativa anterior mantida; V19.3 reforça a fronteira de '
        'logs/tokens e prepara duas novas provas de emulador. Sem aprovação '
        'integrada de Firebase ou Docker nesta sessão.')
    return report


def save():
    artifact=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
    return artifact

if __name__=='__main__':
    artifact=save()
    print(json.dumps({
        'version':artifact['version'],
        'implementation_estimate_percent':artifact['implementation_readiness_estimate_percent'],
        'verified_acceptance_percent':artifact['weighted_acceptance_verified_percent'],
        'passed_gates':artifact['gates_passed'],
        'total_gates':artifact['gates_total'],
        'edge_privacy':artifact['new_privacy_boundary'],
        'ready_for_submission':artifact['ready_for_submission'],
    },ensure_ascii=False,indent=2))
