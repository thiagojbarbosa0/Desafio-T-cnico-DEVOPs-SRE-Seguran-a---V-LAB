#!/usr/bin/env python3
"""Release V16: conservative status based only on independently verified evidence."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v15 import evaluate as evaluate_prior

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/RELEASE_GATE_V16.json'


def evaluate():
    result = evaluate_prior()
    result['version'] = 'V16'
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    result['implementation_readiness_estimate_percent'] = 64
    result['implementation_readiness_note'] = (
        'Estimativa qualitativa de código/documentação/infraestrutura, sem atribuição de nota. '
        'Não significa validação operacional nem chance de aprovação.')
    result['evidence_notice'] = (
        'Os 15 testes Flask HTTP do usuário passaram no Fedora na V14.1; a V16 '
        'exige SHA-256 também dos módulos auxiliares usados por esses testes. '
        'O gate só aceita artefatos regenerados para a fonte atual.')
    result['next_user_action']['single_command_when_ready'] = \
        'bash scripts/fedora_validation_v16.sh --install-deps --with-docker'
    return result


def save(value=None):
    value = value or evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return value


if __name__ == '__main__':
    data = save()
    print(json.dumps({
        'version': data['version'],
        'implementation_estimate_percent': data['implementation_readiness_estimate_percent'],
        'verified_acceptance_percent': data['weighted_acceptance_verified_percent'],
        'gates_passed': data['gates_passed'],
        'gates_total': data['gates_total'],
        'ready_for_submission': data['ready_for_submission'],
    }, indent=2, ensure_ascii=False))
