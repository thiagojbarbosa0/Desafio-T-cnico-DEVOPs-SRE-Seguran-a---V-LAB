#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export APP_MODE=demo
export BIND_HOST=127.0.0.1
export PORT="${PORT:-8091}"
export INSTANCE_ID=standalone
export DEMO_DB_PATH="${DEMO_DB_PATH:-$PWD/.local/coursesphere.sqlite3}"
mkdir -p .local
if [[ -z "${DEMO_SIGNING_KEY:-}" ]]; then
  if [[ ! -f .local/signing_key ]]; then
    python3 - <<'PY' > .local/signing_key
import secrets
print(secrets.token_urlsafe(48))
PY
    chmod 600 .local/signing_key
  fi
  export DEMO_SIGNING_KEY="$(cat .local/signing_key)"
fi
python3 -m backend.local_server &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
python3 -m backend.dev_gateway
