#!/usr/bin/env python3
"""V19.8 supplemental gates: private original Flask metrics and monitoring.

Do not fabricate weighted acceptance: these are supplementary traceable
capabilities on top of the eight existing requirements.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from scripts.release_gate_v19_7 import evaluate as previous
from integration.run_v19_8_metrics_runtime import OUT as WSGI, SOURCES as WSGI_FILES, EXPECTED
from scripts.verify_official_observability_v19_8 import OUT as RUNTIME, FILES as RUNTIME_FILES

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_V19_8.json'


def read(path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError): return None


def correct_hashes(report,paths):
    if not isinstance(report,dict) or report.get('validated') is not True or report.get('version')!='V19.8':
        return False
    hashes=report.get('source_sha256')
    if not isinstance(hashes,dict):
        return False
    try:
        return all(hashes.get(path)==hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                   for path in paths)
    except (OSError, ValueError):
        return False


def metrics_wsgi_valid(report):
    return (correct_hashes(report,WSGI_FILES) and report.get('tests_run')==EXPECTED
            and all(report.get(x)==0 for x in ('skipped','errors','failures'))
            and 'Real Flask WSGI' in report.get('scope',''))


def observability_valid(report):
    if not correct_hashes(report,RUNTIME_FILES):return False
    tests=report.get('tests',{})
    required=('compose_config','grafana_healthy','original_dashboard_provisioned',
              'two_slo_alerts_and_replica_alert_loaded','two_authenticated_scrapes','both_replica_readiness_metrics_observed',
              'original_http_metrics_both_replicas','edge_metrics_denied',
              'prometheus_detected_replica_failure','replica_restored')
    return (isinstance(tests,dict) and all(tests.get(key)=='pass' for key in required)
            and tests.get('gateway_still_available')=='8/8 pass'
            and type(report.get('application_ready_for_authenticated_traffic')) is bool
            and isinstance(tests.get('firebase_readiness_status'),dict)
            and set(tests['firebase_readiness_status'])=={'official_api_a:8091','official_api_b:8091'}
            and all(v in {'ready','degraded'} for v in tests['firebase_readiness_status'].values())
            and report['application_ready_for_authenticated_traffic'] is all(
                v == 'ready' for v in tests['firebase_readiness_status'].values())
            and 'Original Flask metrics' in report.get('scope',''))


def evaluate():
    report=previous()
    report['version']='V19.8'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['original_flask_metrics_auth']={
        'real_flask_wsgi_with_synthetic_firebase':metrics_wsgi_valid(read(WSGI)),
        'evidence':WSGI.relative_to(ROOT).as_posix(),
        'counts_in_weighted_acceptance':False,
    }
    report['original_stack_observability']={
        'two_real_original_flask_metrics_replicas_prometheus_grafana_and_failover':observability_valid(read(RUNTIME)),
        'evidence':RUNTIME.relative_to(ROOT).as_posix(),
        'counts_in_weighted_acceptance':False,
        'scope':'Original Flask Prometheus private scrape + Grafana only; not Firebase Authentication proof',
    }
    report['implementation_readiness_estimate_percent']=73
    report['implementation_readiness_note']=(
        'Internal qualitative engineering estimate; optional original Flask monitoring overlay, '
        'secret-backed Prometheus authentication, two SLO alerts, CI and end-to-end probe added. '
        'Does not imply any Docker/Flask runtime was executed in the assistant environment.')
    report['ready_for_submission']=False
    return report


def save():
    report=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report


if __name__=='__main__':
    report=save()
    print(json.dumps({
        'version':report['version'],
        'implementation_estimate_percent':report['implementation_readiness_estimate_percent'],
        'acceptance_verified_percent':report['weighted_acceptance_verified_percent'],
        'flask_metrics_wsgi_proved':report['original_flask_metrics_auth']['real_flask_wsgi_with_synthetic_firebase'],
        'real_original_observability_proved':report['original_stack_observability']['two_real_original_flask_metrics_replicas_prometheus_grafana_and_failover'],
        'ready_for_submission':False,
    },indent=2,ensure_ascii=False))
