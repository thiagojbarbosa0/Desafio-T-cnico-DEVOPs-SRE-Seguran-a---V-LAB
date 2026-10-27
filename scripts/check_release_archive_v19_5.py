#!/usr/bin/env python3
"""Reject common secret leaks and unsafe entries in a CourseSphere release ZIP.

Offline, no network, no secret values in outputs. This is a conservative
release preflight, not a full history-wide secret scanner or security audit.
"""
from __future__ import annotations
import argparse
import json
import re
import stat
import sys
from pathlib import PurePosixPath, Path
from zipfile import ZipFile, BadZipFile

from scripts.security_preflight_v14 import contains_oauth_secret, PATTERNS, BAD_FILENAMES

SENSITIVE_PARTS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.env', 'dist'}
SENSITIVE_EXTS = {'.pem', '.p12', '.pfx', '.key'}
# A single upstream course dataset is ~90 MiB uncompressed; preserve it, but
# scan it incrementally rather than silently exempting it from the release.
UPSTREAM_LARGE_JSONL = 'backend/cornell-course-sphere-data/course-roster-kaggle/professor_data.jsonl'
JSON_CREDENTIAL_ASSIGNMENT = re.compile(r'(?i)\"(?:client_secret|private_key|refresh_token)\"\s*:\s*\"(?!YOUR|REPLACE|EXAMPLE|DEMO)[^\"]{12,}')

def scan_large_jsonl(stream):
    """Streaming heuristic for credential patterns; never store values."""
    previous=''
    for block in iter(lambda:stream.read(1024 * 1024), b''):
        text=previous + block.decode('utf-8',errors='ignore')
        for label, pattern in list(PATTERNS.items()) + [('oauth_json_assignment', JSON_CREDENTIAL_ASSIGNMENT)]:
            if pattern.search(text):
                return label
        previous=text[-1024:]
    return None



def scan_release(path: Path) -> dict:
    findings=[]
    scanned=0
    found=set()
    size_total=0
    with ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name=info.filename
            rel=PurePosixPath(name)
            scanned+=1
            if name in found:
                findings.append({'path':name,'issue':'duplicate_entry'})
            found.add(name)
            if (rel.is_absolute() or '..' in rel.parts or '\\' in name):
                findings.append({'path':name,'issue':'unsafe_archive_path'})
                continue
            if info.external_attr >> 16 & 0o170000 == stat.S_IFLNK:
                findings.append({'path':name,'issue':'symlink_entry'})
                continue
            if any(part in SENSITIVE_PARTS for part in rel.parts):
                findings.append({'path':name,'issue':'runtime_or_secret_directory'})
                continue
            if rel.name.lower() in BAD_FILENAMES or rel.suffix.lower() in SENSITIVE_EXTS:
                findings.append({'path':name,'issue':'credential_filename'})
                continue
            if rel.suffix.lower() in {'.zip','.tar','.gz','.7z','.rar'}:
                findings.append({'path':name,'issue':'nested_archive_not_reviewed'})
                continue
            # Bound memory and reject oversized text files from introspection.
            if info.file_size > 30_000_000:
                if (rel.as_posix().endswith('/'+UPSTREAM_LARGE_JSONL)
                        and info.file_size <= 150_000_000):
                    with archive.open(info) as large_stream:
                        matched=scan_large_jsonl(large_stream)
                    size_total+=info.file_size
                    if matched:
                        findings.append({'path':name,'issue':'large_dataset_'+matched})
                    continue
                findings.append({'path':name,'issue':'oversized_unreviewed_payload'})
                continue
            size_total+=info.file_size
            if rel.suffix.lower() not in {'.json','.yaml','.yml','.py','.js','.ts','.tsx','.md','.txt','.sh','.toml','.html'}:
                continue
            if info.file_size > 1_000_000:
                continue
            try:
                text=archive.read(info).decode('utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            # JSON OAuth values can hide behind renamed files; never print values.
            if rel.suffix.lower()=='.json':
                try:
                    if contains_oauth_secret(json.loads(text)):
                        findings.append({'path':name,'issue':'credential_shaped_json_value'})
                except (ValueError, TypeError, RecursionError):
                    pass
            for key,expr in PATTERNS.items():
                if expr.search(text):
                    findings.append({'path':name,'issue':key})
    return {
        'status':'PASS' if not findings else 'FAIL',
        'files_inspected':scanned,
        'uncompressed_bytes_inspected':size_total,
        'findings':findings,
        'scope':'Archive paths, filenames, shallow file content and JSON secrets. Not Git history or active credential verification.',
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release_zip',type=Path)
    parser.add_argument('--json-out',type=Path)
    args=parser.parse_args(argv)
    try:
        result=scan_release(args.release_zip)
    except (OSError,BadZipFile) as exc:
        print(f'FAIL: Unable to inspect release ZIP ({type(exc).__name__})',file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'], 'files_inspected':result['files_inspected'],
                      'findings':result['findings']},ensure_ascii=False))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
