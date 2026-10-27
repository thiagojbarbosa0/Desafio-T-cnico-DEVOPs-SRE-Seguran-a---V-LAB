#!/usr/bin/env python3
"""Classify npm audit JSON without mutating package-lock or installing dependencies.

Full and --omit=dev reports must originate from the same immutable checkout.
Unknown/partial data remain UNKNOWN, never silently treated as zero advisories.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
if __package__:
    from .evidence_integrity_vlab import load_json, EvidenceError
else:
    from evidence_integrity_vlab import load_json, EvidenceError

SEVERITIES = ('critical','high','moderate','low','info')
SAFE_PACKAGE = re.compile(r'^(?:@[a-z0-9._-]+/)?[a-z0-9._-]+$', re.I)

def _metadata_check(data: dict, issues: dict):
    # npm returns error details in JSON on a failed audit request; never mark green.
    if 'error' in data or 'errors' in data:
        raise EvidenceError('npm audit returned a tool/network error')
    metadata = data.get('metadata')
    if metadata is None:
        return  # Older saved reports remain triageable but not independently authenticated.
    if not isinstance(metadata, dict):
        raise EvidenceError('invalid npm audit metadata')
    counts = metadata.get('vulnerabilities')
    if counts is None:
        return
    if not isinstance(counts, dict):
        raise EvidenceError('invalid metadata vulnerability counts')
    for severity in SEVERITIES:
        expected = counts.get(severity, 0)
        if type(expected) is not int or expected < 0:
            raise EvidenceError('invalid npm audit severity totals')
        actual = sum(1 for x in issues.values() if x['severity'] == severity)
        if actual != expected:
            raise EvidenceError('npm audit summary disagrees with vulnerability list')
    if 'total' in counts and counts['total'] != len(issues):
        raise EvidenceError('npm audit total disagrees with vulnerability list')


def _issues(data, *, require_metadata: bool = False):
    if not isinstance(data, dict):
        raise EvidenceError('npm audit JSON is not an object')
    if 'error' in data or 'errors' in data:
        raise EvidenceError('npm audit error response is not security evidence')
    if require_metadata and (data.get('auditReportVersion') != 2 or
                             not isinstance(data.get('metadata'), dict) or
                             not isinstance(data['metadata'].get('vulnerabilities'), dict)):
        raise EvidenceError('complete npm audit v2 metadata is required')
    vulnerabilities = data.get('vulnerabilities')
    if not isinstance(vulnerabilities, dict):
        raise EvidenceError('npm audit must provide vulnerabilities object; report incomplete')
    result = {}
    for name, issue in vulnerabilities.items():
        if not isinstance(name, str) or not SAFE_PACKAGE.fullmatch(name) or not isinstance(issue, dict):
            raise EvidenceError('malformed vulnerability entry')
        severity = issue.get('severity')
        if severity not in SEVERITIES:
            raise EvidenceError('missing or unknown severity for '+name)
        result[name] = {
            'severity':severity,
            'direct':issue.get('isDirect') is True,
            'fix_type':('major_or_explicit_change' if isinstance(issue.get('fixAvailable'),dict)
                        else 'npm_suggested' if issue.get('fixAvailable') is True else 'none_reported'),
            'via_count':len(issue['via']) if isinstance(issue.get('via'),list) else None,
        }
    _metadata_check(data, result)
    return result


def triage(full: dict, production: dict | None = None, *, require_metadata: bool = False) -> dict:
    all_issues = _issues(full, require_metadata=require_metadata)
    prod_issues = _issues(production, require_metadata=require_metadata) if production is not None else None
    rows=[]
    for name, info in sorted(all_issues.items(), key=lambda p:(SEVERITIES.index(p[1]['severity']),p[0])):
        exposure = ('not_measured' if prod_issues is None else
                    'production' if name in prod_issues else 'dev_only_by_audit')
        rows.append({'package':name, 'exposure':exposure, **info})
    extra = sorted(set(prod_issues or {})-set(all_issues))
    if extra:
        raise EvidenceError('production report contains issues missing in full report')
    if prod_issues is not None and any(
        prod_issues[k]['severity'] != all_issues[k]['severity'] for k in prod_issues
    ):
        raise EvidenceError('full and production audits disagree on severity')
    counts={s:sum(r['severity']==s for r in rows) for s in SEVERITIES}
    pcounts={s:sum(r['severity']==s and r['exposure']=='production' for r in rows)
             for s in SEVERITIES} if prod_issues is not None else None
    return {
        'validated': True,
        'full_audit_vulnerable_packages':len(rows),
        'counts_by_severity':counts,
        'production_audit_available':prod_issues is not None,
        'production_counts_by_severity':pcounts,
        'priority':'P0' if prod_issues is not None and (pcounts['critical'] or pcounts['high'])
                   else 'P1_review_required' if any(counts.values()) else 'none_reported',
        'items':rows,
        'limitations': [
            'npm audit reports are advisory snapshots, not proof of exploitability.',
            'Full and production audit must use the same package-lock and registry snapshot.',
            'A transitive dependency shown as dev_only_by_audit may still ship in unusual bundling; verify output.',
            'Do not run npm audit fix --force automatically.',
        ],
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',type=Path,required=True)
    p.add_argument('--production',type=Path)
    p.add_argument('--lock',type=Path,default=Path(__file__).resolve().parents[1]/'frontend/package-lock.json')
    p.add_argument('--fail-on-prod-high',action='store_true',help='CI gate: deny unknown production scope or high/critical production advisories')
    p.add_argument('--require-npm-metadata',action='store_true',help='CI gate: require complete npm audit v2 metadata')
    p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    try:
        report=triage(load_json(args.full),load_json(args.production) if args.production else None,require_metadata=args.require_npm_metadata)
        if not args.lock.is_file() or args.lock.is_symlink():
            raise EvidenceError('missing trustworthy local lockfile')
        report['lock_sha256']=hashlib.sha256(args.lock.read_bytes()).hexdigest()
        report['audit_input_sha256']={
            'full':hashlib.sha256(args.full.read_bytes()).hexdigest(),
            'production':hashlib.sha256(args.production.read_bytes()).hexdigest() if args.production else None}
        if args.fail_on_prod_high:
            if report['production_counts_by_severity'] is None:
                report['validated']=False
                report['failure_reason']='production_scope_not_measured'
            elif any(report['production_counts_by_severity'][severity] for severity in ('critical','high')):
                report['validated']=False
                report['failure_reason']='high_or_critical_production_advisories'
    except (EvidenceError, OSError) as exc:
        # Keep names and paths private: user can inspect locally, but no secrets spill to CI.
        report={'validated':False,'error_type':type(exc).__name__,
                'production_audit_available':args.production is not None}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['validated'] else 2

if __name__=='__main__':sys.exit(main())
