#!/usr/bin/env python3
"""Offline SHA-256 inventory of important current evidence; not a signature."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
paths=['HANDOFF_MESTRE_V7.md','docs/RELATORIO_PENTEST_V7.md',
       'evidence/generated/ORIGIN_BEFORE_AFTER.json','evidence/generated/SBOM_frontend_CycloneDX.json',
       'evidence/generated/LOCAL_REPLICA_FAILURE.json','evidence/generated/test_suite_v7.log',
       'audit/baseline/endpoints_original.txt','backend/endpoints.py','frontend/src/api.ts',
       'compose.yaml','ops/nginx/gateway.conf','ops/grafana/dashboards/coursesphere.json']
records=[]
for p in paths:
    f=ROOT/p
    if not f.is_file():raise SystemExit(f'Missing evidence: {p}')
    records.append({'path':p,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
result={'scope':'V7 local evidence checksum inventory. No third party attestation.','files':records}
output=ROOT/'evidence/generated/MANIFEST_SHA256_V7.json'
output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(f'Inventory manifest: {len(records)} files')
