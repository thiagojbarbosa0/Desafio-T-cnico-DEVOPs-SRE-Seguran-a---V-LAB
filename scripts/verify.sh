#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m compileall -q backend tests
if command -v node >/dev/null 2>&1; then node --check dashboard/app.js; else echo "node unavailable: JS syntax check skipped (Python/UI tests still run)"; fi
python3 -m unittest discover -s tests -v
if command -v node >/dev/null 2>&1; then
  node scripts/check_frontend_syntax_v10.cjs || {
    status=$?
    if [ "$status" -ne 2 ]; then exit "$status"; fi
    echo "TypeScript parser unavailable; full frontend validation still required"
  }
fi
python3 scripts/check_secrets.py
python3 scripts/security_preflight_v14.py
python3 scripts/evidence_engine.py
python3 scripts/collect_gateway_evidence_v8.py
python3 - <<'PY'
from pathlib import Path
import json
root=Path('.')
json.loads((root/'ops/grafana/dashboards/coursesphere.json').read_text())
assert (root/'compose.yaml').exists()
assert (root/'HANDOFF_MESTRE_V7.md').exists()
print('Static manifest checks OK')
PY
