#!/usr/bin/env python3
"""Deterministic offline SBOM from existing package-lock.json; NOT an SCA scan."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'frontend/package-lock.json').read_text())
components=[]
for location,info in sorted(lock.get('packages',{}).items()):
    if not location.startswith('node_modules/') or not isinstance(info,dict):continue
    package=location.rsplit('node_modules/',1)[-1]
    version=info.get('version')
    if not version:continue
    components.append({'type':'library','name':package,'version':version,'purl':f'pkg:npm/{package.replace("@","%40",1)}@{version}'})
# Package-lock may contain repeated aliases; dedupe by name/version.
components=list({(x['name'],x['version']):x for x in components}.values())
assert len(components)>50,'Unexpectedly small SBOM; verify package-lock input.'
result={'bomFormat':'CycloneDX','specVersion':'1.5','version':1,
        'metadata':{'component':{'type':'application','name':'CourseSphere-derived-frontend','version':'V7'},
                    'properties':[{'name':'coursesphere:source','value':'frontend/package-lock.json'},
                                  {'name':'coursesphere:coverage','value':'Declared locked npm packages only; install state not checked'}]},
        'components':components}
output=ROOT/'evidence/generated/SBOM_frontend_CycloneDX.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(f'SBOM generated: {len(components)} locked npm components (no CVE analysis)')
