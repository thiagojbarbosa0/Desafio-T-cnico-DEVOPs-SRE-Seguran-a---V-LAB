"""R7 derivative release decision on the recovered V19.9 codebase.

The ORIGINAL V19.15 remains authoritative. This report does not imply that
V19.15, Firebase Emulators or Docker have passed after R7 modifications.
"""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from scripts.release_gate_v19_8 import evaluate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/RELEASE_GATE_R7_DERIVED.json'
CHANGED_SOURCES=(
 'backend/shared_quota.py','backend/endpoints.py','backend/observability.py',
 'backend/demo_store.py','backend/security_core.py','backend/local_server.py',
 'scripts/prove_r7_dual_replica_auth.py',
 'backend/metrics_access.py','scripts/verify_official_observability_v19_8.py',
 'backend/request_correlation.py','backend/readiness.py','backend/firebase.py',
 'backend/firebase_configuration.py','integration/run_official_emulator_tests.py',
 'ops/nginx/gateway.official.conf','ops/prometheus/alerts.official.yml',
 'ops/grafana/dashboards-original/coursesphere-original.json',
 'scripts/release_gate_v19_8.py', 'scripts/release_gate_v12.py', '.github/workflows/ci.yml',
)

def annotate(report:dict)->dict:
    report=dict(report)
    gates=report.get('gates',{})
    def passed(name):
        obj=gates.get(name,{})
        return isinstance(obj,dict) and obj.get('passed') is True
    invalidated=[name for name in (
        'original_flask_http_before_after', 'firebase_auth_database_emulators',
        'docker_observability_failover') if not passed(name)]
    report['version']='R7 derived V19.9 (NOT main V19.15)'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['implementation_readiness_note']='historical V19.9 estimate; no automatic R7 or V19.15 uplift.'
    report['current_source_change_notice']={
        'changed_source':list(CHANGED_SOURCES),
        'invalidated_gates':invalidated,
        'must_retest_before_credit':bool(invalidated),
        'why':'Source changes through R7 invalidate previously collected HTTP/Firebase/metrics/monitoring proof until exact-source re-execution.',
    }
    report['new_security_boundary']={
        'client_rtdb_write':(
            'CURRENT_EMULATOR_PROOF_PRESENT' if passed('firebase_auth_database_emulators')
            else 'HISTORICAL_ONLY: client RTDB denial not re-proven against current sources'),
        'readiness_http':'NEW uncredited feature: requires real Flask/Firebase and authorized Prometheus scrapes',
    }
    report['r4_new_instrumentation']={
        'liveness_route':'/health (process only)',
        'dependency_readiness_route':'/ready (Auth + RTDB; cache 5s, generic 503, not demonstrated over HTTP in this environment)',
        'prometheus_customer_sli_exclusions':['/health','/ready'],
        'additional_acceptance_points':0,
    }
    report['r5_private_readiness_scrape']={
        'metric':'coursesphere_original_firebase_ready',
        'expected_replicas':['official_api_a:8091','official_api_b:8091'],
        'alert_names':['OriginalAPIDependencyReadinessDegraded','OriginalAPIReadinessTelemetryMissing'],
        'runtime_verified_in_this_iteration':False,
        'source_or_docker_attestation_claimed':False,
        'additional_acceptance_points':0,
        'scope':'Backend metrics logic tested in-process; end-to-end Auth/RTDB and Prometheus pending',
    }
    report['r6_firebase_configuration_guard']={
        'strict_emulator_loopback_hosts':True,
        'service_account_forbidden_in_emulator':True,
        'existing_default_app_reuse_cross_project_denied':True,
        'live_database_https_firebase_domain_required':True,
        'runtime_verified_against_real_firebase':False,
        'additional_acceptance_points':0,
        'note':'Pure validation and fake-SDK tests passed offline; Firebase Emulator integration not run here.',
    }
    # The synthetic proof is useful new test evidence, but NOT transferable to
    # the Flask/Firebase production architecture or the weighted acceptance.
    from hashlib import sha256
    proof_path = ROOT / 'evidence/generated/R7_SYNTHETIC_REPLICA_HTTP.json'
    try:
        proof = json.loads(proof_path.read_text(encoding='utf-8'))
        files = ('backend/demo_store.py', 'backend/security_core.py',
                 'backend/local_server.py', 'scripts/prove_r7_dual_replica_auth.py')
        required = ('two_liveness_checks', 'two_readiness_checks',
                    'cross_replica_signed_token', 'cross_user_access_blocked',
                    'shared_quota_across_both_replicas', 'no_increment_after_429')
        confirmed = (isinstance(proof, dict) and proof.get('validated') is True
                     and proof.get('version') == 'R7-derived-V19.9'
                     and all(proof.get('checks', {}).get(key) is True for key in required)
                     and proof.get('counts') == {'successful_login_requests':30,
                                                  'rate_limited_login_requests':11}
                     and all(proof.get('source_sha256', {}).get(f) ==
                             sha256((ROOT/f).read_bytes()).hexdigest() for f in files))
    except (ValueError, OSError, TypeError, AttributeError):
        confirmed = False
    report['r7_synthetic_two_replica_http'] = {
        'confirmed_current_source': confirmed,
        'evidence': proof_path.relative_to(ROOT).as_posix(),
        'scope': 'Python demo HTTP+SQLite, NOT original Flask/Firebase or Docker',
        'additional_acceptance_points': 0,
    }
    report['ready_for_submission']=False
    return report


def main():
    report=annotate(evaluate())
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'version':report['version'],
                      'weighted_acceptance_verified':report['weighted_acceptance_verified_percent'],
                      'ready_for_submission':False,
                      'invalidated_gates':report['current_source_change_notice']['invalidated_gates']},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
