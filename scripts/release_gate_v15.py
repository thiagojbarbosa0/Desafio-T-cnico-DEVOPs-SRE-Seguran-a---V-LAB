#!/usr/bin/env python3
"""V15 acceptance status. No generated 'proof' is promoted without validation."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v14 import evaluate as evaluate_v14

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'evidence/generated/RELEASE_GATE_V15.json'

def evaluate():
    result = evaluate_v14()
    result['version'] = 'V15'
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    # This is a conservative subjective progress estimate, NOT a claim of testing.
    result['implementation_readiness_estimate_percent'] = 63
    result['implementation_readiness_note'] = (
        'Qualitative estimate of implementation scope; V14: ~62%. '
        'Does not imply deployability, acceptance or an official V-Lab score.')
    result['evidence_notice'] = (
        'On 2026-10-23 the Fedora user reported 15/15 real Flask HTTP tests '
        'passing with a synthetic Firebase adapter on the V14.1 source. '
        'The V15 release gate does not import that report without the validated '
        'JSON artifact from the same build. See docs/HANDOFF_V15.md.')
    result['next_user_action']['single_command_when_ready'] = \
        'bash scripts/fedora_validation_v15.sh --install-deps --with-docker'
    return result

if __name__ == '__main__':
    result=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({
        'version':result['version'],
        'implementation_estimate_percent':result['implementation_readiness_estimate_percent'],
        'verified_acceptance_percent':result['weighted_acceptance_verified_percent'],
        'gates_passed':result['gates_passed'],
        'gates_total':result['gates_total'],
        'ready_for_submission':result['ready_for_submission'],
    },indent=2,ensure_ascii=False))
