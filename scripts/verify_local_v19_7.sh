#!/usr/bin/env bash
# From source root, always prefer .venv if one exists and contains Flask.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .venv/bin/activate ]]; then
  export PATH="$PWD/.venv/bin:$PATH"
fi
printf '\n[1/5] Python offline regressions\n'
python3 -m scripts.record_offline_v16
printf '\n[2/5] Real native Nginx: synthetic lab + ORIGINAL gateway contract\n'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/prove_nginx_native.py
  python3 scripts/prove_official_nginx_contract_v19_7.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json evidence/generated/NGINX_OFFICIAL_ROUTING_V19_7.json
  echo 'SKIPPED: Nginx unavailable (not validated)'
fi
printf '\n[3/5] Flask real HTTP if installed; otherwise no runtime claims\n'
if python3 -c 'import flask, flask_cors' >/dev/null 2>&1; then
  python3 -m integration.run_original_http_stubbed
  python3 -m integration.run_v19_4_flask_wsgitest
  python3 -m integration.run_v19_6_cors_runtime
  if command -v nginx >/dev/null 2>&1; then
    python3 scripts/prove_original_flask_nginx.py
  fi
else
  rm -f evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json \
        evidence/generated/FLASK_AUTH_QUOTAS_V19_4.json \
        evidence/generated/FLASK_CORS_RUNTIME_V19_6.json \
        evidence/generated/NGINX_ORIGINAL_FLASK_STUBBED_V19.json
  echo 'SKIPPED: Real Flask/Flask-Cors dependencies missing'
fi
printf '\n[4/5] Node session isolation\n'
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  export NODE_PATH="$(npm root -g)"
  if [[ -f "$NODE_PATH/typescript/lib/typescript.js" ]]; then
    node scripts/test_session_gate_v19_2.cjs
    node scripts/test_user_chats_runtime_v19_2.cjs
    node scripts/test_profile_session_runtime_v19_2.cjs
  else
    echo 'SKIPPED: global TypeScript runtime unavailable'
  fi
fi
printf '\n[5/5] Source-hash checked release gate\n'
python3 -m scripts.release_gate_v19_7
printf '\nDocker, Firebase Emulator and frontend production build need separate executions.\n'
