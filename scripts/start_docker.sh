#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! docker compose version >/dev/null 2>&1; then
  echo 'Docker Compose indisponível. Alternativa: bash scripts/start_local.sh' >&2; exit 1
fi
mkdir -p .local
if [[ ! -f .env ]]; then
  python3 - <<'PY'
from pathlib import Path
import secrets
Path('.env').write_text('DEMO_SIGNING_KEY='+secrets.token_urlsafe(48)+'\nGRAFANA_ADMIN_PASSWORD='+secrets.token_urlsafe(32)+'\n')
PY
  chmod 600 .env
fi
docker compose up -d --build
printf '\nDashboard: http://127.0.0.1:8080/lab/\n'
