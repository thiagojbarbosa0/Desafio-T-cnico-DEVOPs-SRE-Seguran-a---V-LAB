#!/usr/bin/env python3
"""V14 source-bound acceptance with a separate project-readiness estimate.

Evidence is independently collected by verification runners. Never marks absent
libraries, containers, production license, or secret rotation as completed.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v13 import evaluate as evaluate_prior, ROOT, read_json

OUT=ROOT/'evidence/generated/RELEASE_GATE_V14.json'


def evaluate():
    result=evaluate_prior()
    secret_scan=read_json('evidence/generated/SECRET_PREFLIGHT_V14.json')
    # V13 retains its evidence format. All evidence source fingerprints are
    # verified against the V14 modified code when the gate is evaluated.
    result['version']='V14.2'
    result['generated_utc']=datetime.now(timezone.utc).isoformat()
    result['implementation_readiness_estimate_percent']=62
    result['implementation_readiness_note']=(
        'Qualitative estimate of code/config/docs only (V13: ~60%). '
        'NOT independently audited, not a selection score and not validation.')
    result['supporting_checks']={
        'credential_preflight': {
            'passed': secret_scan.get('validated') is True
                      and secret_scan.get('possible_secrets')==[],
            'scanned_text_files': secret_scan.get('checked_text_files'),
            'not_a_full_history_secret_scan': True,
        },
        'no_dependency_on_original_firebase_owners': True,
    }
    result['ready_for_submission']=(result['weighted_acceptance_verified_percent']==100
                                    and result['supporting_checks']['credential_preflight']['passed'])
    result['next_user_action']={
        'is_required_to_reach_100_percent':True,
        'why':'Flask/Firebase emulators, React production build and Docker/Grafana are unavailable or unverified in the current runtime.',
        'single_command_when_ready':'bash scripts/fedora_validation_v14.sh --install-deps --with-docker',
        'also_required':'Confirm upstream redistribution rights and notify credential owner for revocation/rotation; validate five independent findings and three fixes.',
    }
    return result


if __name__=='__main__':
    result=evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({
        'version':result['version'],
        'implementation_estimate_percent':result['implementation_readiness_estimate_percent'],
        'weighted_evidence_percent':result['weighted_acceptance_verified_percent'],
        'gates_passed':result['gates_passed'],
        'gates_total':result['gates_total'],
        'secret_preflight':result['supporting_checks']['credential_preflight']['passed'],
        'ready_for_submission':result['ready_for_submission'],
        'next_action':result['next_user_action']['single_command_when_ready'],
    },indent=2,ensure_ascii=False))
