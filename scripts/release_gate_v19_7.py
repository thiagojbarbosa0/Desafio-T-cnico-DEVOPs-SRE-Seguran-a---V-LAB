#!/usr/bin/env python3
"""V19.7 supplemental original Flask/React stack proofs; conservative score."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from scripts.release_gate_v19_6 import evaluate as previous

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'evidence/generated/RELEASE_GATE_V19_7.json'
NATIVE = ROOT / 'evidence/generated/NGINX_OFFICIAL_ROUTING_V19_7.json'
DOCKER = ROOT / 'evidence/runtime/OFFICIAL_DOCKER_V19_7.json'
NATIVE_FILES = ('ops/nginx/gateway.official.conf', 'ops/nginx/nginx.conf',
                'scripts/prove_official_nginx_contract_v19_7.py')
DOCKER_FILES = ('compose.official.yaml', 'backend/Dockerfile.official',
                'frontend/Dockerfile.official', 'ops/nginx/gateway.official.conf',
                'ops/nginx/frontend.official.conf', 'ops/nginx/nginx.conf',
                'backend/endpoints.py', 'scripts/verify_official_docker_v19_7.py')


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _hash_match(report, sources):
    if not isinstance(report, dict) or report.get('validated') is not True:
        return False
    hashes = report.get('source_sha256')
    if not isinstance(hashes,dict):
        return False
    try:
        return all(hashes.get(path)==hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                   for path in sources)
    except (OSError, ValueError):
        return False


def valid_native(report):
    if not _hash_match(report,NATIVE_FILES) or report.get('version') != 'V19.7':
        return False
    if 'Upstream Flask and React mocked' not in report.get('scope',''):
        return False
    tests = report.get('tests',{})
    if not isinstance(tests,dict):
        return False
    must = ('nginx_config','api_route_original_prefix','react_spa_gateway',
            'metrics_denied','query_blocking','no_token_query_in_edge_logs')
    spread = tests.get('backend_distribution',{})
    return (all(tests.get(t)=='pass' for t in must)
            and tests.get('survivor_after_backend_stop')=='8/8 pass'
            and isinstance(spread,dict)
            and set(spread)=={'a','b'}
            and all(type(spread[x]) is int and spread[x]>0 for x in ('a','b')))


def valid_official_docker(report):
    if not _hash_match(report,DOCKER_FILES) or report.get('version') != 'V19.7':
        return False
    tests=report.get('tests',{})
    spread=tests.get('two_original_flask_replicas',{})
    return (all(tests.get(t)=='pass' for t in
                ('compose_config','original_flask_health','anonymous_profile_denied',
                 'original_react_served','spa_fallback','public_metrics_denied',
                 'api_query_rejected','query_marker_not_logged',
                 'stopped_replica_restored'))
            and spread.get('result')=='pass'
            and spread.get('replicas')==2
            and len(spread.get('distribution',[]))==2
            and all(type(x) is int and x>0 for x in spread['distribution'])
            and tests.get('original_failover')=={'result':'pass','responses':8})


def evaluate():
    result=previous()
    result['version']='V19.7'
    result['generated_utc']=datetime.now(timezone.utc).isoformat()
    result['supplemental_official_docker_stack']={
        'native_nginx_original_routing_validated':valid_native(_read(NATIVE)),
        'original_flask_react_containers_validated':valid_official_docker(_read(DOCKER)),
        'native_scope':'Nginx real, upsteam Flask/React synthetic; not Docker',
        'docker_scope':'original Flask + React containers behind Nginx; no Firebase emulators or Grafana',
        'native_evidence':NATIVE.relative_to(ROOT).as_posix(),
        'docker_evidence':DOCKER.relative_to(ROOT).as_posix(),
        'counts_in_weighted_acceptance':False,
    }
    result['implementation_readiness_estimate_percent']=71
    result['implementation_readiness_note']=(
        'Qualitative estimate for implemented code/configuration, not acceptance. '
        'Original Flask/React Compose stack and native gateway contract added; '
        'real original Docker test, Firebase and Grafana integration pending if not executed.')
    result['ready_for_submission']=False
    return result


def save():
    report=evaluate()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    doc=save()
    print(json.dumps({'version':doc['version'],
                      'implementation_estimate_percent':doc['implementation_readiness_estimate_percent'],
                      'verified_acceptance_percent':doc['weighted_acceptance_verified_percent'],
                      'original_gateway_nginx_tested':doc['supplemental_official_docker_stack']['native_nginx_original_routing_validated'],
                      'original_docker_tested':doc['supplemental_official_docker_stack']['original_flask_react_containers_validated'],
                      'ready_for_submission':False},indent=2))
