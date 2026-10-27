#!/usr/bin/env python3
"""V19: conservative gate plus a separate original-Flask/Nginx evidence track."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v18 import evaluate as previous

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_V19.json'
OPTIONAL=ROOT/'evidence/generated/NGINX_ORIGINAL_FLASK_STUBBED_V19.json'

SOURCES={
    'endpoints':'backend/endpoints.py',
    'cors_policy':'backend/cors_policy.py',
    'harness':'integration/test_original_http_stubbed.py',
    'worker':'scripts/flask_replica_stub_worker.py',
    'nginx':'ops/nginx/gateway.conf',
    'nginx_main':'ops/nginx/nginx.conf',
    'proof':'scripts/prove_original_flask_nginx.py',
}


def valid_replica_proof():
    try:
        data=json.loads(OPTIONAL.read_text())
        correct_hashes=all(data.get('source_sha256', {}).get(key)==hashlib.sha256(
            (ROOT/path).read_bytes()).hexdigest() for key,path in SOURCES.items())
        checks=data.get('tests',{})
        counts=checks.get('original_flask_replicas',{})
        auth=checks.get('original_flask_authorization',{})
        failover=checks.get('survivor_after_flask_a_crash',{})
        return (data.get('validated') is True and correct_hashes
                and set(counts)=={'flask-a','flask-b'} and all(isinstance(v,int) and v>0 for v in counts.values())
                and sum(counts.values())==40 and auth=={'anonymous':401,'bearer_valid':200,'query_token':401}
                and failover=={'instance':'flask-b','successes':8}
                and checks.get('metrics_private')==403
                and checks.get('edge_rejects_token_query')==401
                and checks.get('encoded_query_blocked')==400
                and checks.get('edge_access_log_redacted') is True)
    except (OSError, ValueError, TypeError):
        return False


def evaluate():
    report=previous()
    report['version']='V19'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['implementation_readiness_estimate_percent']=69
    report['implementation_readiness_note']=(
        'Estimativa qualitativa, não nota: V19 fecha a escrita direta do Firebase '
        'e prepara prova de réplicas Flask originais via Nginx; só código comprovado '
        'localmente conta como executado.')
    report['new_security_boundary']={
        'client_rtdb_write':'denied by Firebase rules; live Emulator verification pending',
        'server_writes':'via validated Flask API and privileged Firebase Admin only',
        'emulator_expected_tests':23,
    }
    report['supplemental_original_flask_nginx']={
        'validated':valid_replica_proof(),
        'evidence':'evidence/generated/NGINX_ORIGINAL_FLASK_STUBBED_V19.json',
        'scope':'real Flask and Nginx, Firebase synthetic (not original Firebase integration)',
        'counts_in_weighted_acceptance':False,
    }
    report['evidence_notice']=(
        'V19 alters Firebase rules and emulator suite: Firebase evidence from older '
        'versions is invalid. Original Flask HTTP requires its own new execution. '
        'Independent lab-native Nginx success remains distinct from real Flask replica proof.')
    report['next_user_action']['single_command_when_ready']='bash scripts/fedora_validation_v16.sh --install-deps --with-docker'
    return report


def save():
    value=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    return value


if __name__=='__main__':
    value=save()
    print(json.dumps({'version':value['version'],
                      'implementation_estimate_percent':value['implementation_readiness_estimate_percent'],
                      'verified_acceptance_percent':value['weighted_acceptance_verified_percent'],
                      'gates_passed':value['gates_passed'],
                      'gates_total':value['gates_total'],
                      'original_flask_nginx_proved':value['supplemental_original_flask_nginx']['validated'],
                      'ready_for_submission':value['ready_for_submission']},indent=2))
