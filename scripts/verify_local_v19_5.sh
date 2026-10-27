#!/usr/bin/env bash
# V19.5: fast, reproducible validation; fail closed if a required executed check fails.
# Does not install dependencies, contact external services or use private Firebase.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then export PATH="$PWD/.venv/bin:$PATH"; fi

echo '[V19.5: 1/5] Full offline regression, source checks, sanitized evidence'
python3 -m scripts.record_offline_v16

echo '[V19.5: 2/5] Actual Nginx, if binary is available'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/check_nginx_main_config_v19_3.py
  python3 scripts/prove_nginx_native.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json
  echo 'NOT EXECUTED: Nginx is not installed'
fi

echo '[V19.5: 3/5] Flask integration, only if dependencies are available'
if python3 -c 'import flask, flask_cors' 2>/dev/null; then
  python3 -m integration.run_original_http_stubbed
  python3 -m integration.run_v19_4_flask_wsgitest
  if command -v nginx >/dev/null 2>&1; then python3 scripts/prove_original_flask_nginx.py; fi
else
  echo 'NOT EXECUTED: Flask/Flask-Cors unavailable; never recorded as passed'
  rm -f evidence/generated/FLASK_AUTH_QUOTAS_V19_4.json
fi

echo '[V19.5: 4/5] Frontend session isolation (does not replace React build)'
if command -v node >/dev/null 2>&1; then
  if [[ -f frontend/node_modules/typescript/lib/typescript.js ]]; then
    export NODE_PATH="$PWD/frontend/node_modules"
  elif command -v npm >/dev/null 2>&1 && [[ -f "$(npm root -g)/typescript/lib/typescript.js" ]]; then
    export NODE_PATH="$(npm root -g)"
  else
    export NODE_PATH=''
  fi
  if [[ -n "$NODE_PATH" ]]; then
    node scripts/test_session_gate_v19_2.cjs
    node scripts/test_user_chats_runtime_v19_2.cjs
    node scripts/test_profile_session_runtime_v19_2.cjs
  else
    echo 'NOT EXECUTED: TypeScript module unavailable for Node behavioral tests'
  fi
fi

echo '[V19.5: 5/5] Exact-source release gate, separate F04 static proof'
python3 -m scripts.release_gate_v19_5
echo 'V19.5 local verification completed. This is NOT full submission approval.'
