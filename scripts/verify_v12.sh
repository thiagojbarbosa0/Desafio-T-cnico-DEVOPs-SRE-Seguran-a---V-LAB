#!/usr/bin/env bash
# Strict validation: only steps actually executed may produce validated evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/generated
printf '\n[1/4] Python regression suite + safe sandbox\n'
bash scripts/verify.sh 2>&1 | tee evidence/generated/RESULTADO_TESTES_V12.txt
printf '\n[2/4] Test real Nginx gateway if binary is present\n'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/prove_nginx_native.py
else
  echo 'NOT EXECUTED: Nginx unavailable, cannot count as verified.'
  rm -f evidence/generated/NGINX_LIVE_V9.json
fi
printf '\n[3/4] Real Flask with synthetic Firebase services\n'
if python3 -c 'import flask, flask_cors, werkzeug' >/dev/null 2>&1; then
  python3 -m integration.run_original_http_stubbed
else
  echo 'NOT EXECUTED: Flask/Flask-Cors not installed. See CI or Fedora instructions.'
  rm -f evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json
fi
printf '\n[4/4] Verify evidence gates without assuming unavailable integrations\n'
python3 scripts/release_gate_v12.py
