#!/usr/bin/env bash
# Original CourseSphere Flask & React + private Prometheus/Grafana stack.
# Never copies upstream/author credentials, and never rewrites existing secrets.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -L .local ] || [ -L .local/official_metrics_token ] || [ -L .env.official.observability ]; then
  echo 'Refusing symbolic links for monitoring credentials' >&2
  exit 1
fi
mkdir -p .local
chmod 700 .local
if [ ! -f .local/official_metrics_token ]; then
  umask 077
  python3 - <<'PY'
import secrets
from pathlib import Path
Path('.local/official_metrics_token').write_text(secrets.token_urlsafe(48)+'\n')
PY
fi
chmod 600 .local/official_metrics_token
if [ ! -f .env.official.observability ]; then
  umask 077
  python3 - <<'PY'
import secrets
from pathlib import Path
Path('.env.official.observability').write_text('OFFICIAL_GRAFANA_ADMIN_PASSWORD='+secrets.token_urlsafe(32)+'\n')
PY
fi
chmod 600 .env.official.observability
python3 scripts/official_observability_preflight_v19_8.py
exec docker compose --env-file .env.official.observability \
  -f compose.official.yaml -f compose.official.observability.yaml \
  --profile observability up -d --build
