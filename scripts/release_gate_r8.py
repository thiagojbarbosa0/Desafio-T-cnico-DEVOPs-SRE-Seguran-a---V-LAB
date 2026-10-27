#!/usr/bin/env python3
"""Fail-closed, zero-weight R8 synthetic audit evidence for derived V19.9.

The original V19.15 is authoritative. No R8 synthetic HTTP result may upgrade
Flask/Firebase/Docker/observability acceptance or publication readiness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

from scripts.release_gate_work_v19_9 import annotate
from scripts.release_gate_v19_8 import evaluate
from scripts.prove_r8_atomic_audit import SOURCES

ROOT=Path(__file__).resolve().parents[1]
PROOF='evidence/generated/R8_SYNTHETIC_ATOMIC_AUDIT.json'
OUT='evidence/generated/RELEASE_GATE_R8_DERIVED.json'
REQUIRED=(
 'two_live_replicas','token_works_across_replicas',
 'successful_write_audited_exactly_once','audit_failure_causes_http_500_without_detail',
 'rollback_prevents_orphaned_write','event_count_unchanged_on_failed_write',
 'recovery_after_audit_failure','append_only_trigger_rejects_delete',
)

def assess_proof(root:Path) -> dict:
    failures=[]
    try:
        p=root/PROOF
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 65536:
            raise ValueError('proof_missing_or_oversized')
        record=json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(record,dict):
            raise ValueError('non_object_proof')
        if record.get('version')!='R8-derived-V19.9' or record.get('validated') is not True:
            failures.append('wrong_version_or_unvalidated')
        checks=record.get('checks')
        if not isinstance(checks,dict) or any(checks.get(k) is not True for k in REQUIRED):
            failures.append('incomplete_checks')
        hashes=record.get('source_sha256')
        if not isinstance(hashes,dict) or set(hashes)!=set(SOURCES):
            failures.append('missing_or_extra_source_bindings')
        else:
            for rel in SOURCES:
                source=root/rel
                if source.is_symlink() or not source.is_file():
                    failures.append('source_missing_or_symlink:'+rel)
                elif hashes[rel]!=hashlib.sha256(source.read_bytes()).hexdigest():
                    failures.append('source_mismatch:'+rel)
        if record.get('additional_acceptance_points') != 0:
            failures.append('unauthorized_acceptance_claim')
    except (OSError,UnicodeError,ValueError,TypeError) as exc:
        failures.append('missing_or_invalid_proof')
    return {'confirmed_current_source':not failures,'reasons':sorted(set(failures)),
            'evidence':PROOF,'additional_acceptance_points':0,
            'scope':'Synthetic Python HTTP + SQLite; NOT Flask/Firebase/Docker'}


def add_r8(report:dict, root:Path=ROOT)->dict:
    report=dict(report)
    report['version']='R8 derived from V19.9 (NOT main V19.15)'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['r8_synthetic_atomic_audit']=assess_proof(root)
    report['current_source_change_notice']=dict(report.get('current_source_change_notice',{}))
    report['current_source_change_notice']['why']=(
        'R8 modifies the synthetic HTTP/SQLite server. Previously collected '
        'Flask/Firebase/Docker or synthetic proofs may not be reused without '
        'current source hashes and re-execution.')
    report['ready_for_submission']=False
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-r8',action='store_true',help='Nonzero exit if R8 proof is missing/stale')
    args=parser.parse_args(argv)
    report=add_r8(annotate(evaluate()))
    target=ROOT/OUT
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'r8_validated':report['r8_synthetic_atomic_audit']['confirmed_current_source'],
      'weighted_acceptance_verified':report.get('weighted_acceptance_verified_percent'),
      'ready_for_submission':False,
      'reasons':report['r8_synthetic_atomic_audit']['reasons']},indent=2))
    return 1 if args.require_r8 and not report['r8_synthetic_atomic_audit']['confirmed_current_source'] else 0

if __name__=='__main__':raise SystemExit(main())
