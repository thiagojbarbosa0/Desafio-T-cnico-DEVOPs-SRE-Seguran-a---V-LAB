#!/usr/bin/env bash
# Local-first verification. No paid API, credentials, npm install or Docker needed.
# Flask WSGI tests run only if Flask dependencies are already available.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then export PATH="$PWD/.venv/bin:$PATH"; fi

echo '[1/5] Fresh offline Python regressions + source hashes'
python3 -m scripts.record_offline_v16

echo '[2/5] Native Nginx configuration and failover'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/check_nginx_main_config_v19_3.py
  python3 scripts/prove_nginx_native.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json
  echo 'NOT TESTED: native Nginx missing'
fi

echo '[3/5] Auth/quotas on actual Flask WSGI, synthetic Firebase'
if python3 -c 'import flask, flask_cors' >/dev/null 2>&1; then
  python3 -m integration.run_v19_4_flask_wsgitest
else
  rm -f evidence/generated/FLASK_AUTH_QUOTAS_V19_4.json
  echo 'NOT TESTED: Flask or Flask-Cors not installed; no passing proof generated'
fi

echo '[4/5] Frontend session guard (if local/global TypeScript available)'
if command -v node >/dev/null 2>&1; then
  if [ -f frontend/node_modules/typescript/lib/typescript.js ]; then
    NODE_PATH="$PWD/frontend/node_modules" node scripts/test_session_gate_v19_2.cjs
    NODE_PATH="$PWD/frontend/node_modules" node scripts/test_user_chats_runtime_v19_2.cjs
    NODE_PATH="$PWD/frontend/node_modules" node scripts/test_profile_session_runtime_v19_2.cjs
  elif command -v npm >/dev/null 2>&1 && [ -f "$(npm root -g)/typescript/lib/typescript.js" ]; then
    NODE_PATH="$(npm root -g)" node scripts/test_session_gate_v19_2.cjs
    NODE_PATH="$(npm root -g)" node scripts/test_user_chats_runtime_v19_2.cjs
    NODE_PATH="$(npm root -g)" node scripts/test_profile_session_runtime_v19_2.cjs
  else
    echo 'NOT TESTED: TypeScript runtime not available; no frontend build claimed'
  fi
fi

echo '[5/5] Evidence gate for this exact source'
python3 -m scripts.release_gate_v19_4
