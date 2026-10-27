#!/usr/bin/env python3
"""R11 direct-replica Firebase quota evidence, fail-closed and zero-weight.

A mock HTTP server and tests are NOT evidence of Firebase Emulator integration.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from scripts.release_gate_r10 import add_r10
from scripts.release_gate_r9 import add_r9
from scripts.release_gate_r8 import add_r8
from scripts.release_gate_work_v19_9 import annotate
from scripts.release_gate_v19_8 import evaluate
from scripts.verify_official_replica_quota_r11 import ROOT, OUT, SOURCES, CHECKS

GATE_PATH = ROOT / 'evidence/generated/RELEASE_GATE_R11_DERIVED.json'


def assess(root: Path = ROOT):
    failures = []
    try:
        proof = root / OUT
        if proof.is_symlink() or not proof.is_file() or proof.stat().st_size > 65536:
            raise ValueError('No valid R11 official emulator proof')
        doc = json.loads(proof.read_text('utf-8'))
        if not isinstance(doc, dict) or doc.get('version') != 'R11-derived-V19.9' or doc.get('validated') is not True:
            failures.append('invalid_version_or_validation')
        if doc.get('scope') != 'two original Flask replicas + local Firebase Auth/RTDB emulators only':
            failures.append('unsupported_proof_scope')
        if (type(doc.get('additional_acceptance_points')) is not int
                or doc['additional_acceptance_points'] != 0):
            failures.append('unauthorized_acceptance_points')
        if doc.get('user_data_in_report') is not False:
            failures.append('privacy_marker_missing')
        checks = doc.get('checks')
        if (not isinstance(checks, dict) or set(checks) != set(CHECKS)
                or any(checks[key] is not True for key in CHECKS)):
            failures.append('missing_or_failed_checks')
        hashes = doc.get('source_sha256')
        if not isinstance(hashes, dict) or set(hashes) != set(SOURCES):
            failures.append('invalid_hash_bindings')
        else:
            for relative in SOURCES:
                path = root / relative
                if (path.is_symlink() or not path.is_file()
                        or path.stat().st_size > 3_000_000):
                    failures.append('missing_or_unsafe_source:' + relative)
                elif hashes[relative] != hashlib.sha256(path.read_bytes()).hexdigest():
                    failures.append('stale_source:' + relative)
    except (OSError, ValueError, TypeError, UnicodeError, KeyError):
        failures.append('missing_or_invalid_proof')
    return {
        'confirmed_current_source': not failures,
        'reasons': sorted(set(failures)),
        'evidence': OUT,
        'additional_acceptance_points': 0,
        'scope': 'real original Flask replicas + local Firebase emulator; manual execution required',
    }


def add_r11(report: dict, root: Path = ROOT) -> dict:
    result = dict(report)
    result['version'] = 'R11 derived from V19.9 (NOT V19.15)'
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    result['r11_original_flask_two_replica_quota'] = assess(root)
    result['ready_for_submission'] = False
    result['current_source_change_notice'] = dict(result.get('current_source_change_notice') or {})
    result['current_source_change_notice']['why'] = (
        'R11 changed original Flask response metadata; rerun original Flask/Firebase/Docker '
        'attestation for this exact source. A mock proof earns zero points.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-r11', action='store_true')
    args = parser.parse_args(argv)
    result = add_r11(add_r10(add_r9(add_r8(annotate(evaluate())))))
    GATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GATE_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    statuses = {
        'r8_synthetic': result['r8_synthetic_atomic_audit']['confirmed_current_source'],
        'r9_synthetic': result['r9_synthetic_transport']['confirmed_current_source'],
        'r10_synthetic': result['r10_synthetic_absolute_deadline']['confirmed_current_source'],
        'r11_original_flask_emulator': result['r11_original_flask_two_replica_quota']['confirmed_current_source'],
        'weighted_percent': result.get('weighted_acceptance_verified_percent'),
        'ready_for_submission': False,
    }
    print(json.dumps(statuses, indent=2))
    return 1 if args.require_r11 and not all(statuses[key] for key in (
        'r8_synthetic', 'r9_synthetic', 'r10_synthetic', 'r11_original_flask_emulator')) else 0


if __name__ == '__main__':
    raise SystemExit(main())
