#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
# Strict build: npm ci requires registry access or complete local cache.
npm ci --no-audit --no-fund
# Build using only the isolated demo Firebase project, never the upstream authors' project.
export VITE_USE_FIREBASE_EMULATORS=true
npm run build
cd ..
python3 - <<'PYBUILD'
import json
from scripts.source_fingerprint import frontend_fingerprint
from datetime import datetime,timezone
from pathlib import Path
p=Path('evidence/generated/FRONTEND_BUILD_V13.json')
p.write_text(json.dumps({'validated':True,'scope':'original React/Vite TypeScript production build',
  'timestamp_utc':datetime.now(timezone.utc).isoformat(),
  'command':'npm ci --no-audit --no-fund && npm run build',
  'source_fingerprint':frontend_fingerprint()},indent=2)+'\n')
print('Validated frontend build evidence:',p)
PYBUILD
