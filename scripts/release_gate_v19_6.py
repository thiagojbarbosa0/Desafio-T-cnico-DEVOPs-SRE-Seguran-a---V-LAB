"""V19.6: add independent, source-hashed Flask CORS runtime proof to gate.

This supplementary validation carries no invented evaluation points; the eight
original requirements still determine the verified acceptance percentage.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v19_5 import evaluate as previous
from integration.run_v19_6_cors_runtime import OUT as CORS_EVIDENCE, SOURCES, EXPECTED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/generated/RELEASE_GATE_V19_6.json'


def valid_cors_runtime(report: object) -> bool:
    if not isinstance(report, dict) or report.get('validated') is not True:
        return False
    if report.get('tests_run') != EXPECTED or any(report.get(x) != 0 for x in ('skipped','failures','errors')):
        return False
    fingerprints = report.get('source_sha256')
    if not isinstance(fingerprints, dict):
        return False
    return all(fingerprints.get(source) == hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
               for source in SOURCES)


def evaluate():
    report = previous()
    report['version'] = 'V19.6'
    report['generated_utc'] = datetime.now(timezone.utc).isoformat()
    try:
        evidence = json.loads(CORS_EVIDENCE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        evidence = None
    report['supplemental_flask_cors_runtime'] = {
        'validated': valid_cors_runtime(evidence),
        'scope': 'Real Flask/flask-cors WSGI, Firebase/QueryManager synthetic, five cases',
        'evidence': CORS_EVIDENCE.relative_to(ROOT).as_posix(),
        'counts_in_weighted_acceptance': False,
    }
    report['implementation_readiness_estimate_percent'] = 69
    report['implementation_readiness_note'] = (
        'Qualitative estimate retained; V19.6 adds strict CORS deployment configuration, '
        'offline regressions, HTTP runtime tests and exact-source evidence hashes. '
        'Missing Firebase/React/Docker proofs and manual review remain blocking.')
    report['ready_for_submission'] = False
    return report


def save():
    report = evaluate()
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    report = save()
    print(json.dumps({
        'version': report['version'],
        'implementation_estimate_percent': report['implementation_readiness_estimate_percent'],
        'verified_acceptance_percent': report['weighted_acceptance_verified_percent'],
        'gates_passed': report['gates_passed'],
        'cors_http_validated': report['supplemental_flask_cors_runtime']['validated'],
        'ready_for_submission': False,
    }, indent=2, ensure_ascii=False))
