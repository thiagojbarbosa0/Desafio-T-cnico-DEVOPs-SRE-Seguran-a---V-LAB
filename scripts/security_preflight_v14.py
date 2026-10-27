#!/usr/bin/env python3
"""Conservative, offline credential preflight before PUBLIC GitHub release.

Checks tracked-like text files. This is NOT an alternative to gitleaks, GitHub
secret scanning, repository history review or upstream key rotation.
Never prints suspicious string values. False positives need human review.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/SECRET_PREFLIGHT_V14.json'
EXCLUDED={'node_modules','.venv','__pycache__','.git','evidence','.pytest_cache',
          'dist','build','experiment','venv'}
EXTENSIONS={'.py','.js','.jsx','.ts','.tsx','.json','.yml','.yaml','.md','.txt','.env','.sh','.toml'}
BAD_FILENAMES={'reddit_key.json','service-account.json','service_account.json',
               'credentials.json','id_rsa','id_ed25519'}
PATTERNS={
    'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'openai_secret':re.compile(r'(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{25,}'),
    'github_token':re.compile(r'\bgh[psuo]_[A-Za-z0-9]{30,}\b'),
    'aws_access_key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
}
# Catch the upstream JSON OAuth leak even if the file has been renamed.
# Do not treat a field name alone as a secret; only non-placeholder values.
OAUTH_FIELDS = {'client_secret', 'private_key', 'refresh_token'}
PLACEHOLDER_VALUE = re.compile(r'(?i)^(?:\s*|your[-_ ]?.*|example.*|sample.*|demo.*|dummy.*|changeme|replace.*|placeholder|xxx+|<[^>]+>|\$\{[^}]+\})$')

def contains_oauth_secret(obj):
    if isinstance(obj, list):
        return any(contains_oauth_secret(v) for v in obj)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in OAUTH_FIELDS and isinstance(value, str):
                if len(value) >= 12 and not PLACEHOLDER_VALUE.fullmatch(value):
                    return True
            if contains_oauth_secret(value):
                return True
    return False



def scan_tree(root: Path):
    findings=[]
    scanned=0
    for path in root.rglob('*'):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(root).parts):
            continue
        rel=path.relative_to(root).as_posix()
        if path.name in BAD_FILENAMES or path.suffix.lower() in {'.pem','.p12','.pfx'}:
            findings.append({'file':rel,'rule':'sensitive_filename'})
        if path.suffix.lower() not in EXTENSIONS and not path.name.endswith('.env.example'):
            continue
        if path.stat().st_size>1_000_000:
            continue
        try:
            content=path.read_text(encoding='utf-8')
        except (OSError,UnicodeDecodeError):
            continue
        scanned+=1
        if path.suffix.lower()=='.json':
            try:
                if contains_oauth_secret(json.loads(content)):
                    findings.append({'file':rel,'rule':'credential_shaped_json_value'})
            except (ValueError, TypeError, RecursionError):
                # The regex scanner below still checks malformed/non-JSON text.
                pass
        for name,pattern in PATTERNS.items():
            # No matching secret is ever put in the artifact.
            if pattern.search(content):
                findings.append({'file':rel,'rule':name})
    return scanned,findings


def main():
    scanned,findings=scan_tree(ROOT)
    report={'validated':not findings,'checked_text_files':scanned,
            'possible_secrets':findings,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'limits':'Pattern and filename checks only. Does not scan Git history or revoke keys.'}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Credential preflight: scanned {scanned} text files, flagged {len(findings)} potential issues')
    if findings:
        print('File paths and rule names only:',findings)
    return 0 if not findings else 1


if __name__=='__main__':
    sys.exit(main())
