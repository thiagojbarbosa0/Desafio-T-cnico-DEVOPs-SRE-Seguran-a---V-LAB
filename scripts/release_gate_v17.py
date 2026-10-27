#!/usr/bin/env python3
"""V17 evidence evaluation: no promotions without matching source digests."""
from datetime import datetime, timezone
from pathlib import Path
import json
from scripts.release_gate_v16 import evaluate as evaluate_previous

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/RELEASE_GATE_V17.json'

def evaluate():
    report = evaluate_previous()
    report['version'] = 'V17'
    report['generated_utc'] = datetime.now(timezone.utc).isoformat()
    report['implementation_readiness_estimate_percent'] = 66
    report['implementation_readiness_note'] = ('Qualitative scope estimate, not verified deployment or '
                                                'selection probability. Shared Firebase quota added in V17.')
    report['evidence_notice'] = (
        'V17 added shared quota code to original Flask and changed evidence fingerprints. '
        'The 15/15 HTTP tests from the Fedora V14.1 source remain historical, '
        'but need re-execution for this exact revision. Emulator suite now expects 20 tests.')
    report['next_user_action']['single_command_when_ready'] = (
        'bash scripts/fedora_validation_v16.sh --install-deps --with-docker')
    return report

def save():
    report = evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return report

if __name__ == '__main__':
    report = save()
    print(json.dumps({'version': report['version'],
                      'implementation_estimate_percent': report['implementation_readiness_estimate_percent'],
                      'verified_acceptance_percent': report['weighted_acceptance_verified_percent'],
                      'gates_passed': report['gates_passed'],
                      'gates_total': report['gates_total'],
                      'ready_for_submission': report['ready_for_submission']}, indent=2))
