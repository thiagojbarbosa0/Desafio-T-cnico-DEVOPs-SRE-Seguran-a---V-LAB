#!/usr/bin/env python3
"""Fail closed for known upstream credential-file leak in our derivative.

Not a complete secret scanner. Use gitleaks/TruffleHog in CI before publication.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
unsafe=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ('__pycache__','node_modules','.git','.venv','venv')):continue
    if p.name in {'reddit_key.json','credentials.json','service-account.json','service_account.json'}:
        unsafe.append(p.relative_to(ROOT))
    if p.suffix.lower() in {'.pem','.p12','.pfx'}:
        unsafe.append(p.relative_to(ROOT))
if unsafe:
    raise SystemExit('Unsafe credential files included: '+str([str(x) for x in unsafe]))
print('Known credential-file check OK (not a complete secret scanner)')
