#!/usr/bin/env bash
# Single local entrypoint. Errors are not converted into success statements.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/generated
printf '\n[1/4] Offline regressions and safe HTTP sandbox\n'
bash scripts/verify.sh 2>&1 | tee evidence/generated/RESULTADO_TESTES_V11.txt
printf '\n[2/4] Real Nginx config + loopback failover, if binary available\n'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/prove_nginx_native.py
else
  printf 'NOT RUN: nginx is unavailable. No pass claimed.\n'
fi
printf '\n[3/4] Original Flask HTTP before/after, only if dependencies installed\n'
if python3 -c 'import flask, flask_cors, werkzeug' >/dev/null 2>&1; then
  python3 -m integration.run_original_http_stubbed
else
  printf 'NOT RUN: requires Flask/Flask-Cors. See CI job original-flask-http-before-after.\n'
fi
printf '\n[4/4] Evidence acceptance gate\n'
python3 scripts/release_gate_v11.py
printf '\nReports: evidence/generated/RESULTADO_TESTES_V11.txt and evidence/generated/RELEASE_GATE_V11.json\n'
