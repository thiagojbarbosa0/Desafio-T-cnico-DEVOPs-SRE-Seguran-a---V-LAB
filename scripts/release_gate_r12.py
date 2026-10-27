#!/usr/bin/env python3
"""R12 source-bound zero-weight offline evidence gate.

The original Flask + Firebase integrated release gate is unchanged and
submission remains BLOCKED until fresh runtime proofs are collected.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from scripts.prove_r12_strict_json import ROOT, OUT, SOURCES, EXPECTED
from scripts.release_gate_r11 import add_r11
from scripts.release_gate_r10 import add_r10
from scripts.release_gate_r9 import add_r9
from scripts.release_gate_r8 import add_r8
from scripts.release_gate_work_v19_9 import annotate
from scripts.release_gate_v19_8 import evaluate

PATH='evidence/generated/RELEASE_GATE_R12_DERIVED.json'


def assess(root:Path=ROOT)->dict:
    issues=[]
    try:
        p=root/OUT
        if p.is_symlink() or not p.is_file() or p.stat().st_size>65536:
            raise ValueError('missing or oversized proof')
        proof=json.loads(p.read_text('utf-8'))
        if not isinstance(proof,dict):raise ValueError('invalid shape')
        if proof.get('version')!='R12-derived-V19.9' or proof.get('validated') is not True:
            issues.append('invalid_version_or_validation')
        if proof.get('scope')!='standard-library strict JSON parser, offline only; no Flask/Firebase/Docker claims':
            issues.append('scope_mismatch')
        for key,expected in (('tests_run',EXPECTED),('skipped',0),('failures',0),('errors',0),('additional_acceptance_points',0)):
            if type(proof.get(key)) is not int or proof[key]!=expected:
                issues.append('unexpected_'+key)
        hashes=proof.get('source_sha256')
        if not isinstance(hashes,dict) or set(hashes)!=set(SOURCES):
            issues.append('invalid_hash_bindings')
        else:
            for source in SOURCES:
                file=root/source
                if file.is_symlink() or not file.is_file() or file.stat().st_size>3_000_000:
                    issues.append('missing_or_linked:'+source)
                elif hashes[source]!=hashlib.sha256(file.read_bytes()).hexdigest():
                    issues.append('stale_source:'+source)
    except (OSError,ValueError,UnicodeError,TypeError,KeyError):
        issues.append('missing_or_invalid_evidence')
    return {'confirmed_current_source':not issues,'reasons':sorted(set(issues)),
            'evidence':OUT,'additional_acceptance_points':0,
            'scope':'offline parser tests only; NOT integrated Flask/Firebase proof'}


def add_r12(base:dict,root:Path=ROOT)->dict:
    report=dict(base)
    report['version']='R12 derived from V19.9 (NOT V19.15)'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    report['r12_original_flask_strict_json_offline']=assess(root)
    report['ready_for_submission']=False
    report['current_source_change_notice']=dict(report.get('current_source_change_notice') or {})
    report['current_source_change_notice']['why']=(
        'R12 changed JSON parsing in the original Flask endpoints: all previous '
        'runtime attestations of Flask/Firebase must be regenerated. Offline parser '
        'proof and mocked HTTP tests are worth ZERO acceptance points.')
    return report


def main(argv=None):
    argp=argparse.ArgumentParser(description=__doc__)
    argp.add_argument('--require-r12',action='store_true')
    args=argp.parse_args(argv)
    report=add_r12(add_r11(add_r10(add_r9(add_r8(annotate(evaluate()))))))
    output=ROOT/PATH
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    result={
        'r12_offline_strict_json':report['r12_original_flask_strict_json_offline']['confirmed_current_source'],
        'r11_real_firebase_emulator':report['r11_original_flask_two_replica_quota']['confirmed_current_source'],
        'weighted_acceptance_verified_percent':report.get('weighted_acceptance_verified_percent'),
        'ready_for_submission':False,
    }
    print(json.dumps(result,indent=2))
    return 1 if args.require_r12 and not result['r12_offline_strict_json'] else 0


if __name__=='__main__':raise SystemExit(main())
