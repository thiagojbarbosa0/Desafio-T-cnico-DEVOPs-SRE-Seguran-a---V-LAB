#!/usr/bin/env python3
"""Read-only ZIP distribution audit; prevents path confusion and unsafe packaging.

No claim about embedded credential validity, compiled runtime, or Git history.
This is NOT a replacement for the project's content secret scanner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import zipfile

FORBIDDEN_COMPONENTS = {
    '.git', '.local', '__pycache__', '.venv', 'venv', 'node_modules',
    '.pytest_cache', '.mypy_cache', '.npm', '.ssh', '.aws', '.gnupg',
}
FORBIDDEN_FILES = {'.env', '.npmrc', 'id_rsa', 'id_ed25519', 'credentials.json', 'service-account.json'}
MAX_ENTRIES = 5000
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_SINGLE_BYTES = 96 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250


def _safe_name(name: str) -> bool:
    if not name or '\\' in name or '\x00' in name or name.startswith('/'):
        return False
    parts = name.rstrip('/').split('/')
    if not all(part not in ('', '.', '..') for part in parts):
        return False
    if ':' in parts[0]:
        return False
    if any(part.lower() in FORBIDDEN_COMPONENTS for part in parts):
        return False
    basename = parts[-1].lower()
    if basename in FORBIDDEN_FILES or (basename.startswith('.env.') and not basename.endswith('.example')):
        return False
    return True


def audit_archive(path: Path) -> dict:
    """Reject dangerous filenames, links, duplicates, bombs and bad CRCs."""
    problems: list[str] = []
    entries = 0
    expanded_bytes = 0
    zip_sha256 = hashlib.sha256()
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError('archive_missing_or_symlinked')
        with path.open('rb') as source:
            while block := source.read(1024 * 1024):
                zip_sha256.update(block)
        with zipfile.ZipFile(path, 'r') as z:
            seen = set()
            for info in z.infolist():
                entries += 1
                if entries > MAX_ENTRIES:
                    problems.append('too_many_entries')
                    break
                name = info.filename
                if not _safe_name(name):
                    problems.append('unsafe_path')
                normalized = name.rstrip('/').casefold()
                if normalized in seen:
                    problems.append('duplicate_casefold_path')
                seen.add(normalized)
                mode = (info.external_attr >> 16) & 0xffff
                if stat.S_IFMT(mode) == stat.S_IFLNK:
                    problems.append('symlink_entry')
                if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    problems.append('non_regular_entry')
                if info.flag_bits & 1:
                    problems.append('encrypted_entry')
                if info.file_size < 0 or info.file_size > MAX_SINGLE_BYTES:
                    problems.append('oversized_file')
                expanded_bytes += info.file_size
                if expanded_bytes > MAX_TOTAL_BYTES:
                    problems.append('oversized_archive')
                    break
                if info.file_size > 1024 * 1024 and info.file_size > MAX_COMPRESSION_RATIO * max(1, info.compress_size):
                    problems.append('suspicious_compression_ratio')
                # Reading each file verifies CRC; no extraction or filesystem writes.
                if info.file_size <= MAX_SINGLE_BYTES and not problems:
                    with z.open(info) as src:
                        while src.read(1024 * 1024):
                            pass
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        problems.append('unreadable_archive:'+type(exc).__name__)
    return {
        'validated': entries > 0 and not problems,
        'entries_checked': entries,
        'uncompressed_bytes_declared': expanded_bytes,
        'sha256': zip_sha256.hexdigest() if zip_sha256.digest_size else None,
        'issues': sorted(set(problems)),
        'scope': 'Archive structure, paths, CRC and compression bounds only; not license, runtime or exhaustive secret analysis',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = audit_archive(args.archive)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['validated'] else 1


if __name__ == '__main__':
    sys.exit(main())
