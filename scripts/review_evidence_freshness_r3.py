#!/usr/bin/env python3
"""Inspect historic AppSec/SRE evidence against CURRENT source bytes.

A fresh hash means consistency with the checkout, not independently verified
execution, an upstream vulnerability or a right to publish. No acceptance
points are awarded by this tool. Missing/old evidence always fails closed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts.evidence_integrity_vlab import load_json, safe_relative, EvidenceError, SHA256

ROOT=Path(__file__).resolve().parents[1]
# Source hashes in older tests use semantic keys rather than filenames.
SEMANTIC_KEYS = {
    'original':'audit/baseline/endpoints_original.txt',
    'corrected':'backend/endpoints.py',
    'test_harness':'integration/test_original_http_stubbed.py',
    'security_core':'backend/security_core.py',
    'shared_quota':'backend/shared_quota.py',
    'cors_policy':'backend/cors_policy.py',
    'observability':'backend/observability.py',
    'endpoints':'backend/endpoints.py',
    'firebase':'backend/firebase.py',
    'firebase_configuration':'backend/firebase_configuration.py',
    'rules':'ops/firebase/database.rules.json',
    'emulator_harness':'integration/test_official_emulators.py',
    'emulator_runner':'integration/run_official_emulator_tests.py',
}

# Explicit roster: never blindly treat arbitrary JSON under evidence/ as trusted.
EVIDENCE_ROSTER = (
    ('original_flask_http', 'evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json'),
    ('firebase_emulators', 'evidence/generated/FLASK_FIREBASE_EMULATORS_V12.json'),
    ('flask_cors', 'evidence/generated/FLASK_CORS_RUNTIME_V19_6.json'),
    ('flask_metrics', 'evidence/generated/FLASK_METRICS_AUTH_V19_8.json'),
    ('frontend_profile_isolation', 'evidence/generated/PROFILE_RACE_WORK.json'),
    ('native_prometheus', 'evidence/generated/NATIVE_PROMETHEUS_WORK.json'),
    ('original_gateway_nginx', 'evidence/generated/NGINX_OFFICIAL_ROUTING_V19_7.json'),
)


def assess(root:Path, label:str, rel:str) -> dict:
    failures=[]
    try:
        proof=load_json(safe_relative(root,rel))
        if proof.get('validated') is not True:
            failures.append('proof_not_validated')
        if proof.get('skipped',0) != 0:
            failures.append('skipped_or_unknown_tests')
        files=proof.get('source_sha256')
        if not isinstance(files,dict) or not files:
            failures.append('missing_source_hashes')
        else:
            for key,digest in files.items():
                if not isinstance(key,str) or not isinstance(digest,str) or not SHA256.fullmatch(digest):
                    failures.append('malformed_source_binding')
                    continue
                source=SEMANTIC_KEYS.get(key,key)
                try:
                    actual=hashlib.sha256(safe_relative(root,source).read_bytes()).hexdigest()
                    if actual != digest:
                        failures.append('source_changed:'+source)
                except (EvidenceError,OSError):
                    failures.append('source_unavailable:'+source)
    except (EvidenceError,OSError):
        failures.append('proof_missing_or_malformed')
    return {'name':label,'evidence':rel,'source_consistent':not failures,
            'failures':sorted(set(failures))}


def audit(root:Path) -> dict:
    reports=[assess(root,name,rel) for name,rel in EVIDENCE_ROSTER]
    return {'status':'review_only', 'can_infer_runtime_acceptance':False,
            'records':reports,
            'source_consistent':sum(p['source_consistent'] for p in reports),
            'source_stale_or_incomplete':sum(not p['source_consistent'] for p in reports),
            'manual_review_required':['Five independent upstream vulnerabilities and three root-cause fixes',
                'Runtime/containers tied to exact current source',
                'Authorization to redistribute and source credential rotation'],
            'disclaimer':'Hashes check current checkout consistency, never prove genuine execution or upstream exploitability.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--output',type=Path)
    p.add_argument('--fail-on-stale',action='store_true')
    args=p.parse_args(argv)
    report=audit(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 1 if args.fail_on_stale and report['source_stale_or_incomplete'] else 0

if __name__=='__main__':sys.exit(main())
