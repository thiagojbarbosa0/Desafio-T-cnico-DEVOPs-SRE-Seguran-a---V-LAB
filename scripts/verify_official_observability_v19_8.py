#!/usr/bin/env python3
"""Integration gate for REAL original Flask replicas -> Prometheus -> Grafana.

Requires an ALREADY RUNNING optional Docker overlay. With no Docker/runtime this
exits nonzero. Only aggregate, redacted data are stored in the report.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/runtime/OFFICIAL_OBSERVABILITY_V19_8.json'
FILES = (
    'compose.official.yaml', 'compose.official.observability.yaml',
    'backend/Dockerfile.official', 'frontend/Dockerfile.official',
    'backend/endpoints.py', 'backend/metrics_access.py', 'backend/observability.py',
    'backend/firebase.py', 'backend/firebase_configuration.py', 'backend/readiness.py',
    'backend/shared_quota.py', 'ops/firebase/database.rules.json',
    'ops/prometheus/prometheus.official.yml', 'ops/prometheus/alerts.official.yml',
    'ops/grafana/dashboards-original/coursesphere-original.json',
    'ops/grafana/provisioning-official/datasources/datasources.yml',
    'ops/grafana/provisioning-official/dashboards/dashboards.yml',
    'scripts/start_official_observability_v19_8.sh',
    'scripts/official_observability_preflight_v19_8.py',
    'scripts/verify_official_observability_v19_8.py',
)
PROM = 'http://127.0.0.1:9092'
GRAFANA = 'http://127.0.0.1:3001'
WEB = 'http://127.0.0.1:8081'
EXPECTED = {'official_api_a:8091', 'official_api_b:8091'}


def query(expr: str) -> dict[str, float]:
    url = PROM + '/api/v1/query?' + urlencode({'query': expr})
    with urlopen(url, timeout=5) as resp:
        data = json.load(resp)
    if data.get('status') != 'success':
        raise AssertionError('Prometheus query did not succeed')
    result = {}
    for entry in data.get('data', {}).get('result', []):
        instance = entry['metric'].get('instance')
        if not isinstance(instance, str):
            raise AssertionError('Prometheus target missing instance label')
        result[instance] = float(entry['value'][1])
    return result


def wait(predicate, *, timeout=60):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        try:
            result=predicate()
            if result:
                return result
        except (OSError, HTTPError, URLError, ValueError, KeyError, AssertionError):
            pass
        time.sleep(1.5)
    raise AssertionError('Prometheus/Grafana expected condition was not observed within timeout')


def compose(*args):
    command=['docker','compose','--env-file','.env.official.observability',
             '-f','compose.official.yaml','-f','compose.official.observability.yaml',
             '--profile','observability',*args]
    p=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=90)
    if p.returncode != 0:
        raise RuntimeError(f'Docker Compose {args[0]} returned {p.returncode}; see container diagnostics locally')
    return p.stdout


def dashboard_is_provisioned():
    """Check the actual Grafana API; never publish the local admin password."""
    env_path=ROOT/'.env.official.observability'
    secret_lines=[line for line in env_path.read_text().splitlines()
                  if line.startswith('OFFICIAL_GRAFANA_ADMIN_PASSWORD=')]
    if len(secret_lines)!=1:
        raise AssertionError('Dashboard admin secret file missing or invalid')
    password=secret_lines[0].partition('=')[2]
    if len(password)<32:
        raise AssertionError('Dashboard password is too short')
    authorization=base64.b64encode(('admin:'+password).encode()).decode()
    endpoint=GRAFANA+'/api/dashboards/uid/coursesphere-original-v19-8'
    with urlopen(Request(endpoint,headers={'Authorization':'Basic '+authorization}), timeout=5) as resp:
        document=json.load(resp)
    model=document.get('dashboard',{})
    panels=model.get('panels',[])
    return (model.get('uid')=='coursesphere-original-v19-8'
            and len(panels)>=6
            and any('coursesphere_original_http_requests_total' in target.get('expr','')
                    for panel in panels for target in panel.get('targets',[])))


def alerts_are_loaded():
    with urlopen(PROM+'/api/v1/rules?type=alert',timeout=5) as response:
        data=json.load(response)
    names={rule.get('name') for group in data.get('data',{}).get('groups',[])
           for rule in group.get('rules',[])}
    return {'OriginalAPIAvailabilitySLO','OriginalAPILatencySLO','OriginalAPIReplicaUnavailable','OriginalAPIDependencyReadinessDegraded',
            'OriginalAPIReadinessTelemetryMissing'}<=names


def run(*, failover: bool, require_ready: bool=False) -> dict:
    report = {'version':'V19.8','validated':False,'scope':
              'Original Flask metrics over authenticated private Docker network, two distinct Prometheus targets and Grafana health',
              'generated_utc':datetime.now(timezone.utc).isoformat(),
              'source_sha256':{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in FILES},
              'tests':{}}
    stopped=False
    try:
        compose('config','--quiet')
        report['tests']['compose_config']='pass'
        def healthy():
            with urlopen(GRAFANA+'/api/health',timeout=4) as f:
                return f.status == 200 and json.load(f).get('database') == 'ok'
        wait(healthy,timeout=75)
        report['tests']['grafana_healthy']='pass'
        wait(dashboard_is_provisioned,timeout=60)
        report['tests']['original_dashboard_provisioned']='pass'
        wait(alerts_are_loaded,timeout=40)
        report['tests']['two_slo_alerts_and_replica_alert_loaded']='pass'
        with urlopen(WEB+'/health',timeout=4) as f:
            assert f.status==200 and json.load(f).get('service')=='coursesphere-api'
        for _ in range(10):
            with urlopen(WEB+'/health',timeout=4) as f: assert f.status==200
        def both_up():
            targets=query('up{job="coursesphere-original"}')
            return targets if set(targets)==EXPECTED and all(v==1 for v in targets.values()) else None
        wait(both_up,timeout=75)
        report['tests']['two_authenticated_scrapes']='pass'
        # Check the observed Firebase readiness of EACH separately scraped
        # replica. Merely loading an alert rule or checking /health is not proof.
        # The original unauthenticated compose may report 0; in that case the
        # test records the degraded condition, but does not declare it ready.
        def both_readiness_observed():
            samples=query('coursesphere_original_firebase_ready{job="coursesphere-original"}')
            return samples if set(samples)==EXPECTED and all(v in (0.0,1.0) for v in samples.values()) else None
        readiness_values=wait(both_readiness_observed,timeout=60)
        report['tests']['both_replica_readiness_metrics_observed']='pass'
        report['tests']['firebase_readiness_status']={key: ('ready' if value==1 else 'degraded')
                                                     for key,value in readiness_values.items()}
        # Readiness is intentionally distinct from scrape health. The
        # Firebase-integrated gate must still require both values to equal 1.
        report['application_ready_for_authenticated_traffic']=all(v==1 for v in readiness_values.values())
        if require_ready and not report['application_ready_for_authenticated_traffic']:
            raise AssertionError('Firebase Auth/RTDB degraded on one or both replicas')
        def collected_http():
            values=query('coursesphere_original_http_requests_total{route="/health"}')
            return values if set(values)==EXPECTED and all(v>=1 for v in values.values()) else None
        wait(collected_http,timeout=60)
        report['tests']['original_http_metrics_both_replicas']='pass'
        # The EDGE gateway must not publish any Prometheus telemetry.
        try:
            urlopen(WEB+'/metrics',timeout=4)
        except HTTPError as exc:
            if exc.code != 403: raise
        else:
            raise AssertionError('Public /metrics unexpectedly exposed')
        report['tests']['edge_metrics_denied']='pass'
        if failover:
            compose('stop','official_api_a')
            stopped=True
            def failure_detected():
                values=query('up{job="coursesphere-original"}')
                return values if set(values)==EXPECTED and values['official_api_a:8091']==0 and values['official_api_b:8091']==1 else None
            wait(failure_detected,timeout=65)
            report['tests']['prometheus_detected_replica_failure']='pass'
            for _ in range(8):
                with urlopen(WEB+'/health',timeout=5) as f: assert f.status==200
            report['tests']['gateway_still_available']='8/8 pass'
        report['validated']=True
    except Exception as exc:
        report['error_type']=type(exc).__name__
        report['error']=str(exc)[:170]
    finally:
        if stopped:
            try:
                compose('start','official_api_a')
                def restored():
                    values=query('up{job="coursesphere-original"}')
                    return set(values)==EXPECTED and all(v==1 for v in values.values())
                wait(restored,timeout=90)
                report['tests']['replica_restored']='pass'
            except Exception as exc:
                report['tests']['replica_restored']='failed'
                report['validated']=False
                report['recovery_error']=type(exc).__name__
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--failover',action='store_true')
    parser.add_argument('--require-ready',action='store_true',
                        help='Fail if either Firebase Auth/RTDB replica probe reports degraded')
    args=parser.parse_args()
    report=run(failover=args.failover, require_ready=args.require_ready)
    print(json.dumps({'validated':report['validated'],'tests':report['tests'],
                      'error':report.get('error')},indent=2))
    return 0 if report['validated'] else 1


if __name__=='__main__':
    raise SystemExit(main())
