#!/usr/bin/env python3
"""Zero-weight R14 gate: source-fresh real emulator proof AND fixture teardown.

This doesn't authorize submission or silently upgrade old R11 evidence.
The R11 quota proof alone may be generated without the scoped coordinator,
so R14 independently requires that the cleanup step actually completed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

from scripts.release_gate_r11 import assess as assess_r11
from scripts.release_gate_r12 import add_r12
from scripts.release_gate_r11 import add_r11
from scripts.release_gate_r10 import add_r10
from scripts.release_gate_r9 import add_r9
from scripts.release_gate_r8 import add_r8
from scripts.release_gate_work_v19_9 import annotate
from scripts.release_gate_v19_8 import evaluate
from scripts.verify_official_replica_quota_r11 import ROOT, OUT

OUTPUT = 'evidence/generated/RELEASE_GATE_R14_DERIVED.json'
MAX_EVIDENCE_AGE = timedelta(hours=24)
MAX_FUTURE_SKEW = timedelta(minutes=5)


def assess(root: Path = ROOT, *, now: datetime | None = None) -> dict:
    prior = assess_r11(root)
    issues = list(prior['reasons'])
    try:
        artifact = root / OUT
        if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 65536:
            raise ValueError('Missing or invalid proof')
        proof = json.loads(artifact.read_text('utf-8'))
        if not isinstance(proof, dict):
            raise ValueError('Invalid proof format')
        if proof.get('fixture_cleanup_verified') is not True:
            issues.append('scoped_fixture_cleanup_not_proved')
        if proof.get('proof_origin') != 'r14_scoped_emulator_coordinator':
            issues.append('not_issued_by_scoped_coordinator')
        generated = proof.get('generated_utc')
        if not isinstance(generated, str) or len(generated) > 45:
            raise ValueError('Invalid timestamp')
        date = datetime.fromisoformat(generated)
        if date.tzinfo is None:
            issues.append('untrusted_naive_timestamp')
        else:
            date = date.astimezone(timezone.utc)
            check_time = now or datetime.now(timezone.utc)
            if check_time.tzinfo is None:
                raise ValueError('Gate clock must be timezone-aware')
            check_time = check_time.astimezone(timezone.utc)
            if date < check_time - MAX_EVIDENCE_AGE:
                issues.append('integrated_proof_expired')
            if date > check_time + MAX_FUTURE_SKEW:
                issues.append('integrated_proof_from_future')
    except (OSError, ValueError, TypeError, UnicodeError, KeyError, OverflowError):
        issues.append('no_valid_scoped_cleanup_attestation')
    return {
        'confirmed_current_source': not issues,
        'reasons': sorted(set(issues)),
        'evidence': OUT,
        'additional_acceptance_points': 0,
        'scope': 'real Flask + loopback Firebase Emulator with successful scoped cleanup; no production claim',
    }


def add_r14(report: dict, root: Path = ROOT) -> dict:
    result = dict(report)
    result['version'] = 'R14 derived from V19.9 (NOT V19.15)'
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    result['r14_scoped_integrated_quota_cleanup'] = assess(root)
    result['ready_for_submission'] = False
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-r14', action='store_true')
    args = parser.parse_args(argv)
    base = add_r12(add_r11(add_r10(add_r9(add_r8(annotate(evaluate()))))))
    report = add_r14(base)
    out = ROOT / OUTPUT
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    result = {
        'r14_flask_firebase_with_cleanup': report['r14_scoped_integrated_quota_cleanup']['confirmed_current_source'],
        'r14_blockers': report['r14_scoped_integrated_quota_cleanup']['reasons'],
        'weighted_acceptance_verified_percent': report.get('weighted_acceptance_verified_percent'),
        'ready_for_submission': False,
    }
    print(json.dumps(result, indent=2))
    return 1 if args.require_r14 and not result['r14_flask_firebase_with_cleanup'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
