#!/usr/bin/env python3
"""Sanitized and offline-only proof of credential material committed upstream.

Requires a local ORIGINAL ZIP passed by the operator. Never displays, writes,
transmits or hashes individual credential *values*. A digest of the entire ZIP
identifies the supplied upstream snapshot, without claiming credential validity.
The original ZIP is NOT copied into the distribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'backend/cornell-course-sphere-data/reddit-data/reddit_key.json'
OUTPUT = ROOT / 'evidence/generated/F04_UPSTREAM_CREDENTIAL_EXPOSURE.json'
PLACEHOLDER = re.compile(r'(?i)^(?:\s*|your[-_ ]?.*|example.*|sample.*|demo.*|dummy.*|changeme|replace.*|placeholder|xxx+|<[^>]+>|\$\{[^}]+\})$')


def collect(zip_path: Path) -> dict:
    """Return metadata only; actual JSON values NEVER leave this function."""
    with ZipFile(zip_path) as archive:
        candidates = [info for info in archive.infolist()
                      if info.filename.endswith('/' + TARGET) or info.filename == TARGET]
        if len(candidates) != 1:
            raise ValueError('Expected exactly one credential-shaped upstream file')
        entry = candidates[0]
        if entry.is_dir() or entry.file_size > 10_000:
            raise ValueError('Unexpected upstream entry size/type')
        path = PurePosixPath(entry.filename)
        if '..' in path.parts:
            raise ValueError('Unsafe upstream archive path')
        decoded = json.loads(archive.read(entry).decode('utf-8'))
        if not isinstance(decoded, dict):
            raise ValueError('Expected JSON object')
        fields = {'client_id', 'client_secret'}
        if not fields <= decoded.keys():
            raise ValueError('Expected fields missing')
        secret = decoded['client_secret']
        client_id = decoded['client_id']
        if not isinstance(secret, str) or not isinstance(client_id, str):
            raise ValueError('Unexpected field type')
        if len(secret) < 12 or PLACEHOLDER.fullmatch(secret):
            raise ValueError('Credential-looking value missing or clearly placeholder')
        if len(client_id) < 6 or PLACEHOLDER.fullmatch(client_id):
            raise ValueError('Client ID looking value missing or placeholder')
        # No value, partial value, or value hash enters the report.
        credential_metadata = {
            'relative_path': TARGET,
            'fields_present': sorted(fields),
            'credential_like_non_placeholder': True,
            'credential_currently_valid': 'NOT_TESTED',
            'external_service_contacted': False,
        }
    hasher = hashlib.sha256()
    with zip_path.open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            hasher.update(chunk)
    return {
        'finding_id': 'F04',
        'finding': 'Credential-shaped material included in original upstream source archive',
        'source_snapshot_sha256': hasher.hexdigest(),
        'source_snapshot_size_bytes': zip_path.stat().st_size,
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'file_evidence': credential_metadata,
        'scope': 'Local static artifact inspection only. Not credential verification, exploitation, or breach confirmation.',
        'recommended_owner_action': 'Privately notify owner, confirm scope and rotate/revoke if valid; avoid publishing secret or original artifact.',
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Path to original user-provided CourseSphere ZIP')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    opts = parser.parse_args(argv)
    try:
        report = collect(opts.source)
    except (OSError, ValueError, KeyError, BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f'NOT VERIFIED: {type(exc).__name__} (no evidence written)', file=sys.stderr)
        return 2
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"F04 sanitized evidence VERIFIED: original ZIP SHA256={report['source_snapshot_sha256']}, output={opts.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
