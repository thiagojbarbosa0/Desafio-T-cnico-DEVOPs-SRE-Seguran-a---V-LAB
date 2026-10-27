#!/usr/bin/env python3
"""Conservative V18 gate. Never accept stale evidence after changes."""
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v17 import evaluate as previous

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/RELEASE_GATE_V18.json'

def evaluate():
    report = previous()
    report['version'] = 'V18'
    report['generated_utc'] = datetime.now(timezone.utc).isoformat()
    report['implementation_readiness_estimate_percent'] = 67
    report['implementation_readiness_note'] = (
        'Qualitative estimate only. V18 adds RTDB-shared chat-write quotas and '
        'stronger offline/emulator checks. NOT an approval prediction.')
    report['evidence_notice'] = (
        'V18 changed original Flask endpoints, shared_quota, test harness and '
        'Firebase emulator tests. Prior Flask/Firebase artifacts are historical '
        'and will be rejected by SHA-256 checks until rerun.')
    report['next_user_action']['single_command_when_ready'] = (
        'bash scripts/fedora_validation_v16.sh --install-deps --with-docker')
    return report

def save():
    data = evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    return data

if __name__ == '__main__':
    data = save()
    print(json.dumps({'version':data['version'],
                      'implementation_estimate_percent':data['implementation_readiness_estimate_percent'],
                      'verified_acceptance_percent':data['weighted_acceptance_verified_percent'],
                      'gates_passed':data['gates_passed'],
                      'gates_total':data['gates_total'],
                      'ready_for_submission':data['ready_for_submission']}, indent=2))
