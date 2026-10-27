#!/usr/bin/env bash
# V19.6: prove what actually ran; never elevate skipped integration checks.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then
  export PATH="$PWD/.venv/bin:$PATH"
fi

echo '[1/5] Offline suite + hashed evidence (mandatory)'
python3 -m scripts.record_offline_v16

echo '[2/5] Native Nginx (optional; not Docker)'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/check_nginx_main_config_v19_3.py
  python3 scripts/prove_nginx_native.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json
  echo 'NOT EXECUTED: Nginx is not installed'
fi

echo '[3/5] Actual Flask and Flask-Cors (optional, fail-closed when run)'
if python3 -c 'import flask,flask_cors' >/dev/null 2>&1; then
  python3 -m integration.run_original_http_stubbed
  python3 -m integration.run_v19_4_flask_wsgitest
  python3 -m integration.run_v19_6_cors_runtime
  if command -v nginx >/dev/null 2>&1; then
    python3 scripts/prove_original_flask_nginx.py
  fi
else
  # Preserve absence explicitly, never reuse older versions of these claims.
  rm -f evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json \
        evidence/generated/FLASK_AUTH_QUOTAS_V19_4.json \
        evidence/generated/NGINX_ORIGINAL_FLASK_STUBBED_V19.json
  rm -f evidence/generated/FLASK_CORS_RUNTIME_V19_6.json
  echo 'NOT EXECUTED: real Flask and Flask-Cors integration (install in .venv or CI)'
fi

echo '[4/5] Session isolation tests (only if Node+TypeScript are available)'
if command -v node >/dev/null 2>&1; then
  if [[ -f frontend/node_modules/typescript/lib/typescript.js ]]; then
    export NODE_PATH="$PWD/frontend/node_modules"
  elif command -v npm >/dev/null 2>&1 && [[ -f "$(npm root -g)/typescript/lib/typescript.js" ]]; then
    export NODE_PATH="$(npm root -g)"
  else
    NODE_PATH=''
  fi
  if [[ -n "$NODE_PATH" ]]; then
    node scripts/test_session_gate_v19_2.cjs
    node scripts/test_user_chats_runtime_v19_2.cjs
    node scripts/test_profile_session_runtime_v19_2.cjs
  else
    echo 'NOT EXECUTED: TypeScript runtime absent (not a React build)'
  fi
else
  echo 'NOT EXECUTED: Node is absent'
fi

echo '[5/5] Exact-source release score (not a hiring grade)'
python3 -m scripts.release_gate_v19_6
printf '\nV19.6 local checks finished. Firebase Emulator/React build/Docker are separate gates.\n'
