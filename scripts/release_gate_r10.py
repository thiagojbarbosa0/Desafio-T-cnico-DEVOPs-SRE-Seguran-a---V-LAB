#!/usr/bin/env python3
"""Fail-closed, zero-weight acceptance gate for R10 synthetic deadline proof."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scripts.release_gate_r9 import add_r9
from scripts.release_gate_r8 import add_r8
from scripts.release_gate_work_v19_9 import annotate
from scripts.release_gate_v19_8 import evaluate
from scripts.prove_r10_deadline import SOURCES

ROOT=Path(__file__).resolve().parents[1]
PROOF='evidence/generated/R10_SYNTHETIC_ABSOLUTE_DEADLINE.json'
OUT='evidence/generated/RELEASE_GATE_R10_DERIVED.json'
REQUIRED=('two_replicas_alive','trickling_headers_terminated',
          'trickling_body_returns_408','authenticated_slow_write_denied',
          'no_orphan_mutation_or_audit','both_replicas_recovered','shared_store_unchanged')


def assess_proof(root:Path):
    problems=[]
    try:
        path=root/PROOF
        if path.is_symlink() or not path.is_file() or path.stat().st_size>65536:
            raise ValueError('invalid R10 proof file')
        payload=json.loads(path.read_text('utf-8'))
        if not isinstance(payload,dict):raise ValueError('expected object')
        if payload.get('version')!='R10-derived-V19.9' or payload.get('validated') is not True:
            problems.append('wrong_version_or_validation')
        checks=payload.get('checks')
        if not isinstance(checks,dict) or set(checks)!=set(REQUIRED) or any(checks[k] is not True for k in REQUIRED):
            problems.append('missing_extra_or_failed_checks')
        if type(payload.get('additional_acceptance_points')) is not int or payload['additional_acceptance_points']!=0:
            problems.append('unauthorized_acceptance_claim')
        bindings=payload.get('source_sha256')
        if not isinstance(bindings,dict) or set(bindings)!=set(SOURCES):
            problems.append('invalid_source_bindings')
        else:
            for rel in SOURCES:
                source=root/rel
                if source.is_symlink() or not source.is_file() or source.stat().st_size>3_000_000:
                    problems.append('source_missing_or_unsafe:'+rel)
                elif bindings[rel]!=hashlib.sha256(source.read_bytes()).hexdigest():
                    problems.append('source_changed:'+rel)
    except (OSError,UnicodeError,ValueError,TypeError,KeyError):
        problems.append('invalid_or_missing_proof')
    return {'confirmed_current_source':not problems,'reasons':sorted(set(problems)),
            'evidence':PROOF,'additional_acceptance_points':0,
            'scope':'Python synthetic TCP+SQLite; NOT Flask/Firebase/Docker'}


def add_r10(report:dict,root:Path=ROOT):
    report=dict(report)
    report['version']='R10 derived from V19.9 (NOT main V19.15)'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['r10_synthetic_absolute_deadline']=assess_proof(root)
    report['ready_for_submission']=False
    report['current_source_change_notice']=dict(report.get('current_source_change_notice') or {})
    report['current_source_change_notice']['why']=(
        'R10 changed synthetic HTTP transport. Historical Flask/Firebase/Docker proofs '
        'do not attest these bytes. Re-run original stack and review upstream findings.')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-r10',action='store_true')
    args=parser.parse_args(argv)
    report=add_r10(add_r9(add_r8(annotate(evaluate()))))
    out=ROOT/OUT;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    statuses={
        'r8_proof_current':report['r8_synthetic_atomic_audit']['confirmed_current_source'],
        'r9_proof_current':report['r9_synthetic_transport']['confirmed_current_source'],
        'r10_proof_current':report['r10_synthetic_absolute_deadline']['confirmed_current_source'],
        'weighted_acceptance_verified_percent':report.get('weighted_acceptance_verified_percent'),
        'ready_for_submission':False}
    print(json.dumps(statuses,indent=2))
    return 1 if args.require_r10 and not all([statuses['r8_proof_current'],statuses['r9_proof_current'],statuses['r10_proof_current']]) else 0

if __name__=='__main__':raise SystemExit(main())
