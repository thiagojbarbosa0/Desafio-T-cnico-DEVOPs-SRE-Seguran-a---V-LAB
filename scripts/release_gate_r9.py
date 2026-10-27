#!/usr/bin/env python3
"""R9 synthetic transport proof is zero-weight and never releases V19.15."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scripts.release_gate_r8 import add_r8
from scripts.release_gate_work_v19_9 import annotate
from scripts.release_gate_v19_8 import evaluate
from scripts.prove_r9_transport import SOURCES

ROOT=Path(__file__).resolve().parents[1]
PROOF='evidence/generated/R9_SYNTHETIC_HTTP_TRANSPORT.json'
OUT='evidence/generated/RELEASE_GATE_R9_DERIVED.json'
REQUIRED=(
    'both_replicas_live','valid_json_truncated_by_cl_rejected',
    'slow_body_times_out_408','oversize_declared_rejected',
    'truncated_authenticated_write_rejected','no_mutation_or_success_audit',
    'valid_request_still_accepted','readiness_after_timeout',
    'bounded_active_handlers','capacity_recovers_after_idle_disconnect',
)

def assess_proof(root:Path):
    problems=[]
    try:
        file=root/PROOF
        if file.is_symlink() or not file.is_file() or file.stat().st_size>65536:
            raise ValueError('invalid proof file')
        record=json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(record,dict): raise ValueError('not a JSON object')
        if record.get('version')!='R9-derived-V19.9' or record.get('validated') is not True:
            problems.append('wrong_version_or_validation')
        if not isinstance(record.get('checks'),dict) or any(record['checks'].get(k) is not True for k in REQUIRED):
            problems.append('missing_or_failed_checks')
        if record.get('additional_acceptance_points') != 0:
            problems.append('unauthorized_acceptance_claim')
        hashes=record.get('source_sha256')
        if not isinstance(hashes,dict) or set(hashes)!=set(SOURCES):
            problems.append('invalid_source_bindings')
        else:
            for rel in SOURCES:
                source=root/rel
                if source.is_symlink() or not source.is_file():
                    problems.append('source_unavailable_or_symlink:'+rel)
                elif source.stat().st_size>3_000_000 or hashes[rel]!=hashlib.sha256(source.read_bytes()).hexdigest():
                    problems.append('source_changed:'+rel)
    except (OSError,UnicodeError,ValueError,TypeError):
        problems.append('invalid_or_missing_proof')
    return {'confirmed_current_source':not problems,'reasons':sorted(set(problems)),
            'evidence':PROOF,'additional_acceptance_points':0,
            'scope':'Python synthetic TCP+SQLite; NOT Flask/Firebase/Docker'}


def add_r9(report:dict,root:Path=ROOT):
    report=dict(report)
    report['version']='R9 derived from V19.9 (NOT main V19.15)'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['r9_synthetic_transport']=assess_proof(root)
    report['current_source_change_notice']=dict(report.get('current_source_change_notice') or {})
    report['current_source_change_notice']['why']='R9 changes synthetic HTTP framing and timeouts; previously generated proof must be re-run and bound to source hashes; historical original stack not credited.'
    report['ready_for_submission']=False
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-r9',action='store_true')
    args=parser.parse_args(argv)
    report=add_r9(add_r8(annotate(evaluate())))
    out=ROOT/OUT
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'r8_proof_current':report['r8_synthetic_atomic_audit']['confirmed_current_source'],
      'r9_proof_current':report['r9_synthetic_transport']['confirmed_current_source'],
      'weighted_acceptance_verified_percent':report.get('weighted_acceptance_verified_percent'),
      'ready_for_submission':False,'reasons':report['r9_synthetic_transport']['reasons']},indent=2))
    return 1 if args.require_r9 and not (
        report['r8_synthetic_atomic_audit']['confirmed_current_source']
        and report['r9_synthetic_transport']['confirmed_current_source']
    ) else 0

if __name__=='__main__': raise SystemExit(main())
