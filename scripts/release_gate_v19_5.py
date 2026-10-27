#!/usr/bin/env python3
"""V19.5: carry forward the live-test gates, add a separate sanitized F04 provenance track.

The F04 static artifact does NOT turn five vulnerabilities into five exploitable
production findings, nor add points to the eight weighted runtime gates.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v19_4 import evaluate as previous

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/generated/F04_UPSTREAM_CREDENTIAL_EXPOSURE.json'
OUTPUT = ROOT / 'evidence/generated/RELEASE_GATE_V19_5.json'
FIELDS = ['client_id', 'client_secret']


def validate_f04(report: object) -> bool:
    if not isinstance(report, dict) or report.get('finding_id') != 'F04':
        return False
    if not re.fullmatch(r'[a-f0-9]{64}', str(report.get('source_snapshot_sha256', ''))):
        return False
    info = report.get('file_evidence')
    if not isinstance(info, dict):
        return False
    if (info.get('relative_path') != 'backend/cornell-course-sphere-data/reddit-data/reddit_key.json'
            or info.get('fields_present') != FIELDS
            or info.get('credential_like_non_placeholder') is not True
            or info.get('credential_currently_valid') != 'NOT_TESTED'
            or info.get('external_service_contacted') is not False):
        return False
    # The report should be schema-limited, not a container for actual values.
    return (set(info) == {
        'relative_path', 'fields_present', 'credential_like_non_placeholder',
        'credential_currently_valid', 'external_service_contacted'
    } and set(report) == {
        'finding_id', 'finding', 'source_snapshot_sha256',
        'source_snapshot_size_bytes', 'checked_at_utc', 'file_evidence',
        'scope', 'recommended_owner_action'
    })


def evaluate():
    result = previous()
    result['version'] = 'V19.5'
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    try:
        metadata = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        metadata = None
    passed = validate_f04(metadata)
    result['supplemental_upstream_credential_exposure_F04'] = {
        'provenance_metadata_verified': passed,
        'credential_validity': 'NOT_TESTED',
        'exploitation_claimed': False,
        'counts_in_weighted_acceptance': False,
        'source':'user-provided original CourseSphere ZIP, inspected locally',
        'evidence':'evidence/generated/F04_UPSTREAM_CREDENTIAL_EXPOSURE.json',
        'next_owner_action':'Notify upstream owner privately and request credential rotation/revocation if active',
    }
    result['implementation_readiness_estimate_percent'] = 69
    result['implementation_readiness_note'] = (
        'Previous qualitative estimate retained. V19.5 adds an independently '
        'reproducible static source exposure finding and a prevention control; '
        'the main Flask, Firebase, React and Docker acceptance gaps remain.')
    result['ready_for_submission'] = False
    return result


def save():
    result = evaluate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    r=save()
    print(json.dumps({'version':r['version'],
                      'implementation_estimate_percent':r['implementation_readiness_estimate_percent'],
                      'verified_acceptance_percent':r['weighted_acceptance_verified_percent'],
                      'gates_passed':r['gates_passed'],
                      'F04_source_exposure_proof':r['supplemental_upstream_credential_exposure_F04']['provenance_metadata_verified'],
                      'ready_for_submission':r['ready_for_submission']},indent=2))
