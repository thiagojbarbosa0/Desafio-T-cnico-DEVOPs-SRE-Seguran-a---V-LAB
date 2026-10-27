#!/usr/bin/env bash
# Local, offline checks; no dependency install, no Docker, no internet.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m scripts.record_offline_v16
node scripts/check_frontend_syntax_v14_2.cjs
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/prove_nginx_native.py
else
  echo 'SKIPPED: native nginx unavailable (not a passing proof)'
  rm -f evidence/generated/NGINX_LIVE_V9.json
fi
# This second proof only runs when real Flask and Flask-Cors exist.
if command -v nginx >/dev/null 2>&1 && python3 -c 'import flask, flask_cors' >/dev/null 2>&1; then
  python3 scripts/prove_original_flask_nginx.py
else
  echo 'SKIPPED: original Flask/NGINX replica proof requires Flask and nginx'
  rm -f evidence/generated/NGINX_ORIGINAL_FLASK_STUBBED_V19.json
fi
python3 -m scripts.doctor_v19
