#!/usr/bin/env bash
# Offline-first V19.3 verification. It never installs dependencies or invokes
# external services. All runtime passes must be from executions in this run.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m scripts.record_offline_v16
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/check_nginx_main_config_v19_3.py
  python3 scripts/prove_nginx_native.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json
  echo 'NOT TESTED: native Nginx missing (no passing proof recorded)'
fi
if command -v node >/dev/null 2>&1; then
  # Prefer project-local TypeScript; global TS fallback is for local synthetic
  # tests only and must NEVER be confused with a production React build.
  if [ -f frontend/node_modules/typescript/lib/typescript.js ]; then
    for script in test_session_gate_v19_2 test_user_chats_runtime_v19_2 test_profile_session_runtime_v19_2; do
      node "scripts/${script}.cjs"
    done
  elif command -v npm >/dev/null 2>&1 && [ -f "$(npm root -g)/typescript/lib/typescript.js" ]; then
    export NODE_PATH="$(npm root -g)"
    for script in test_session_gate_v19_2 test_user_chats_runtime_v19_2 test_profile_session_runtime_v19_2; do
      node "scripts/${script}.cjs"
    done
  else
    echo 'NOT TESTED: session Node checks require TypeScript (not a build PASS)'
  fi
fi
python3 -m scripts.release_gate_v19_3
