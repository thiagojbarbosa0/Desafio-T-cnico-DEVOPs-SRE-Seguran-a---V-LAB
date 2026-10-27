#!/usr/bin/env python3
"""Inventory of distributable files; excludes generated local secrets and caches."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/SHA256_V8.json'
SKIP={'.local','__pycache__','node_modules','.git','.pytest_cache','dist'}
entries=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or any(x in SKIP for x in p.relative_to(ROOT).parts):continue
    if p==OUT or p.suffix=='.pyc' or p.name=='.DS_Store':continue
    entries.append({'path':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({'schema':'coursesphere.v8.sha256-manifest','total_files':len(entries),'files':entries},indent=2)+'\n')
print('Hash manifest:',len(entries),'files')
