#!/usr/bin/env bash
# Offline-only: no dependency installs or Docker starts. Native Nginx if installed.
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'python3 -m scripts.doctor_v17 || true' EXIT
python3 -m scripts.record_offline_v16
if command -v nginx >/dev/null 2>&1; then
    timeout 60s python3 scripts/prove_nginx_native.py
else
    rm -f evidence/generated/NGINX_LIVE_V9.json
    echo 'Nginx proof unavailable: NOT TESTED'
fi
