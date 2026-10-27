#!/usr/bin/env bash
# V15 offline/static/native Nginx verification. Never claims Docker or Firebase.
set -euo pipefail
cd "$(dirname "$0")/.."
# Prefer the already prepared virtual environment, if available. This prevents
# reporting Flask as missing when it is installed only in .venv.
if [ -x .venv/bin/python ]; then
  export PATH="$PWD/.venv/bin:$PATH"
fi
bash scripts/verify_v13.sh
python3 scripts/security_preflight_v14.py
if command -v node >/dev/null 2>&1; then
  echo 'Optional TypeScript syntax-only check (not a production build):'
  if ! node scripts/check_frontend_syntax_v14_2.cjs; then
    echo 'TypeScript parser missing or syntax invalid; this is NOT a passing build.'
  fi
fi
python3 -m scripts.release_gate_v15
