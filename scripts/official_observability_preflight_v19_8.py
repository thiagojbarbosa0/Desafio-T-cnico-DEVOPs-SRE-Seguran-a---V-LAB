#!/usr/bin/env python3
"""Fail closed before starting the ORIGINAL metrics overlay; never print secrets."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKEN = ROOT / '.local/official_metrics_token'
ENV = ROOT / '.env.official.observability'


def check(root: Path = ROOT) -> list[str]:
    errors = []
    token = root / '.local/official_metrics_token'
    settings = root / '.env.official.observability'
    if (root / '.local').is_symlink():
        errors.append('Private metrics directory must not be a symbolic link')
    for path in (token, settings):
        if path.is_symlink():
            errors.append(f'Private local file must not be a symbolic link: {path.relative_to(root)}')
            continue
        if not path.is_file():
            errors.append(f'Missing private local file: {path.relative_to(root)}')
            continue
        if path.stat().st_mode & 0o077:
            errors.append(f'Private local file has group/other permissions: {path.relative_to(root)}')
        if path.stat().st_size > 4096:
            errors.append(f'Oversized configuration file: {path.relative_to(root)}')
    if token.is_file() and token.stat().st_size <= 4096:
        content = token.read_text(errors='replace').strip()
        if len(content) < 40 or not re.fullmatch(r'[A-Za-z0-9_-]+', content):
            errors.append('Metrics bearer secret is malformed or insufficiently long')
    if settings.is_file() and settings.stat().st_size <= 4096:
        text = settings.read_text(errors='replace')
        lines = [x for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
        if len(lines) != 1 or not re.fullmatch(r'OFFICIAL_GRAFANA_ADMIN_PASSWORD=[A-Za-z0-9_-]{32,}', lines[0]):
            errors.append('Grafana secret environment file must contain one safe generated password')
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--require-docker', action='store_true')
    args = p.parse_args()
    errors = check()
    if args.require_docker:
        import shutil
        if shutil.which('docker') is None:
            errors.append('Docker CLI is absent; runtime validation is blocked')
    if errors:
        for error in errors:
            print('FAIL:', error, file=sys.stderr)
        return 1
    print('PASS: private local metrics and dashboard secrets are prepared (values suppressed)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
