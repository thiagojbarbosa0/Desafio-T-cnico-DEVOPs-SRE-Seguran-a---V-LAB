#!/usr/bin/env bash
# Offline-first: execute regressions only once, then isolated native Nginx.
# Does not install packages, run Firebase emulators, or start Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'python3 -m scripts.doctor_v16 || true' EXIT
python3 -m scripts.record_offline_v16
if command -v nginx >/dev/null 2>&1; then
  timeout 45s python3 scripts/prove_nginx_native.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json
  echo 'Nginx native: NOT TESTED (nginx not installed).'
fi
