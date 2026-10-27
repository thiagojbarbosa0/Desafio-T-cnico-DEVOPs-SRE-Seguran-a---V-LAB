#!/usr/bin/env python3
"""V13 evidence gate: conservative proof, weighted by actual edital priorities.

Status is based on *validated artifacts*, not existence of config/test files.
No numeric score here is a candidate grade or an approval probability.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.release_gate_v12 import validate_http_evidence, validate_emulator_evidence
from scripts.source_fingerprint import docker_fingerprint, frontend_fingerprint, nginx_fingerprint, fingerprint

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_V13.json'


def read_json(relative):
    try:
        item=json.loads((ROOT/relative).read_text(encoding='utf-8'))
        return item if isinstance(item,dict) else {}
    except (OSError,ValueError):
        return {}


def offline_fingerprint():
    paths=['backend/'+p.relative_to(ROOT/'backend').as_posix() for p in (ROOT/'backend').rglob('*.py')]
    paths+=['tests/'+p.relative_to(ROOT/'tests').as_posix() for p in (ROOT/'tests').rglob('*.py')]
    paths+=['integration/'+p.relative_to(ROOT/'integration').as_posix() for p in (ROOT/'integration').rglob('*.py')]
    paths+=['scripts/'+p.relative_to(ROOT/'scripts').as_posix() for p in (ROOT/'scripts').glob('*.py')]
    return fingerprint(paths)


def valid_offline(value):
    return (value.get('validated') is True
            and isinstance(value.get('tests_run'),int) and value['tests_run']>=134
            and value.get('failures')==0 and value.get('errors')==0
            and value.get('source_fingerprint')==offline_fingerprint())


def valid_nginx(value):
    checks=value.get('cases',{})
    counts=checks.get('request_distribution',{}).get('counts',{})
    return (value.get('result')=='PASSED'
            and value.get('source_fingerprint')==nginx_fingerprint()
            and all(counts.get(name,0)>0 for name in ('api-a','api-b'))
            and checks.get('failover_after_process_crash',{}).get('result')=='passed'
            and checks.get('metrics_not_public',{}).get('result')=='passed')


def valid_frontend(value):
    return (value.get('validated') is True and value.get('source_fingerprint')==frontend_fingerprint())


def valid_docker(value):
    tests=value.get('tests',{})
    essential=('compose_config','dashboard','metrics_not_public',
               'prometheus_scrapes_two','grafana_database_health',
               'grafana_provisioned_dashboard','api_a_restarted')
    return (value.get('validated') is True
            and value.get('source_fingerprint')==docker_fingerprint()
            and all(tests.get(key)=='pass' for key in essential)
            and tests.get('nginx_failover_after_api_a_stop',{}).get('result')=='pass'
            and set(tests.get('replica_distribution',{}))=={'api-a','api-b'})


def evaluate():
    offline=read_json('evidence/generated/TESTES_OFFLINE_V13.json')
    nginx=read_json('evidence/generated/NGINX_LIVE_V9.json')
    flask=read_json('evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json')
    firebase=read_json('evidence/generated/FLASK_FIREBASE_EMULATORS_V12.json')
    react=read_json('evidence/generated/FRONTEND_BUILD_V13.json')
    docker=read_json('evidence/runtime/DOCKER_STACK_V13.json')
    candidates={
        'offline_regressions': (7,valid_offline(offline), 'Suíte local, incluindo segurança e métricas originais'),
        'nginx_real_failover': (8,valid_nginx(nginx), 'Nginx real, duas réplicas sintéticas'),
        'original_flask_http_before_after': (20,validate_http_evidence(flask), '15 casos HTTP antes/depois com Firebase simulado'),
        'firebase_auth_database_emulators': (18,validate_emulator_evidence(firebase), '23 casos com emuladores oficiais'),
        'original_react_production_build': (7,valid_frontend(react), 'npm ci e build TS/React, hash de fontes'),
        'docker_observability_failover': (15,valid_docker(docker), 'Compose, Nginx, Prometheus, Grafana, failover e restart'),
        'five_findings_three_root_cause_fixes': (20,False, 'Revisão técnica dos 5 achados ativos e 3 correções'),
        'redistribution_and_upstream_rotation': (5,False, 'Licença/publicação e rotação: terceiros devem confirmar'),
    }
    gates={key:{'weight':weight,'passed':passed,'reason':reason}
           for key,(weight,passed,reason) in candidates.items()}
    assert sum(item['weight'] for item in gates.values())==100
    verified=sum(item['weight'] for item in gates.values() if item['passed'])
    return {
        'version':'V13', 'generated_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Percentual ponderado de aceite COMPROVADO; não é nota nem probabilidade de aprovação.',
        'weighted_acceptance_verified_percent':verified,
        'gates_passed':sum(int(g['passed']) for g in gates.values()),
        'gates_total':len(gates),'ready_for_submission':verified==100,
        'gates':gates,
    }

if __name__=='__main__':
    value=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(value,indent=2,ensure_ascii=False))
