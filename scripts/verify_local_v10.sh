#!/usr/bin/env bash
# Safe one-command offline verification; no Docker/Firebase or external connections.
# Binds native Nginx proof exclusively to 127.0.0.1 when available.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/generated
bash scripts/verify.sh 2>&1 | tee evidence/generated/RESULTADO_TESTES_V10.txt
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/prove_nginx_native.py
else
  echo 'Native Nginx not installed; gateway proof skipped (not passed).'
fi
python3 scripts/release_gate_v10.py
