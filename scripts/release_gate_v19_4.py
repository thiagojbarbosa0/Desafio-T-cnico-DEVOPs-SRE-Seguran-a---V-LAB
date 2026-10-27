#!/usr/bin/env python3
"""V19.4 evidence gate: preserve scoring, add separate fail-closed WSGI proof.

No new internal points for unexecuted tests; output is NOT a selection grade.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v19_3 import evaluate as previous
from integration.run_v19_4_flask_wsgitest import ROOT, OUT as WSGI_FILE, SOURCES

OUT = ROOT/'evidence/generated/RELEASE_GATE_V19_4.json'


def valid_wsgi(record):
    if not isinstance(record,dict):return False
    if record.get('validated') is not True or record.get('tests_run')!=7:
        return False
    if any(record.get(k)!=0 for k in ('skipped','failures','errors')):
        return False
    digests=record.get('source_sha256')
    if not isinstance(digests,dict):return False
    return all(digests.get(path)==hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
               for path in SOURCES)


def evaluate():
    report=previous()
    report['version']='V19.4'
    report['generated_utc']=datetime.now(timezone.utc).isoformat()
    try:record=json.loads(WSGI_FILE.read_text())
    except (OSError,ValueError):record={}
    verified=valid_wsgi(record)
    report['supplemental_wsgi_auth_and_quotas']={
        'validated':verified,
        'scope':'Real Flask WSGI routing with synthetic Firebase; not Firebase Emulator or production',
        'expected_tests':7,
        'evidence':str(WSGI_FILE.relative_to(ROOT)),
        'counts_in_weighted_acceptance':False,
    }
    report['implementation_readiness_estimate_percent']=69
    report['implementation_readiness_note']=(
        'Maintained prior qualitative estimate; CI repair, shared quotas for profile/deletion, '
        'privacy-safe authentication logging and tests do not replace missing integration proof.')
    report['ready_for_submission']=False  # Explicit human pentest/permission gates remain unfinished.
    return report


def save():
    report=evaluate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    report=save()
    print(json.dumps({'version':report['version'],
        'implementation_estimate_percent':report['implementation_readiness_estimate_percent'],
        'verified_acceptance_percent':report['weighted_acceptance_verified_percent'],
        'gates_passed':report['gates_passed'],
        'wsgi_auth_and_quotas':report['supplemental_wsgi_auth_and_quotas']['validated'],
        'ready_for_submission':report['ready_for_submission']},indent=2))
