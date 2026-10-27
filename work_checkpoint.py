#!/usr/bin/env python3
"""Export a verified recoverable source checkpoint, excluding local secrets/builds."""
import argparse
import hashlib
from pathlib import Path
import zipfile
from datetime import datetime, timezone

EXCLUDED = {'.git', '.venv', 'node_modules', '__pycache__', 'dist', '.cache', '.firebase', '.local'}
SECRET_NAMES = {'credentials.json', 'reddit_key.json', 'service-account.json', 'service_account.json'}

def eligible(path, root):
    relative = path.relative_to(root)
    return (not any(part in EXCLUDED for part in relative.parts)
            and not path.is_symlink() and path.is_file()
            and not path.name.startswith('.env')
            and path.name not in SECRET_NAMES
            and path.suffix.lower() not in {'.pem', '.p12', '.pfx', '.pyc', '.zip'}
            and not path.name.endswith('-debug.log'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out_dir).resolve()
    if out == root or root in out.parents:
        parser.error('out-dir must be outside the source tree')
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = out / f'CourseSphere_V19_9_WORK_{stamp}.zip'
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if eligible(path, root):
                archive.write(path, Path('CourseSphere_V19_9') / path.relative_to(root))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{digest}  {target.name}\n')
    print(target)
    print('SHA256', digest)

if __name__ == '__main__':
    main()
