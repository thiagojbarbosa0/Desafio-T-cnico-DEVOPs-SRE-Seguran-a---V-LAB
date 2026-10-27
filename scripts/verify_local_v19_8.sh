#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Includes Python offline, Node session tests, native Nginx and source-bound gate.
bash scripts/verify_local_v19_7.sh
if python3 -c 'import flask, flask_cors' >/dev/null 2>&1; then
    python3 -m integration.run_v19_8_metrics_runtime
else
    rm -f evidence/generated/FLASK_METRICS_AUTH_V19_8.json
    echo 'NOT VERIFIED: V19.8 Flask metrics WSGI (Flask missing)'
fi
python3 -m scripts.release_gate_v19_8
