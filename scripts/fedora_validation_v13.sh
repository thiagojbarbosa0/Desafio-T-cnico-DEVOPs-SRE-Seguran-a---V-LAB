#!/usr/bin/env bash
# Safe, zero-cost validation of the local CourseSphere derivative on Fedora.
# --install-deps explicitly permits internet downloads into the workspace.
# --with-docker explicitly permits isolated local test containers.
set -euo pipefail
cd "$(dirname "$0")/.."
INSTALL=0
DOCKER=0
for arg in "$@"; do
  case "$arg" in
    --install-deps) INSTALL=1 ;;
    --with-docker) DOCKER=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

printf '\n== Stage 1: offline suite, Nginx native ==\n'
bash scripts/verify_v13.sh

printf '\n== Stage 2: Flask original HTTP, synthetic Firebase ==\n'
if ! python3 -c 'import flask,flask_cors,werkzeug' 2>/dev/null; then
  if [ "$INSTALL" -eq 1 ]; then
    echo 'Installing ONLY into local .venv (not system Python)'
    if [ ! -f .venv/bin/activate ]; then python3 -m venv .venv; fi
    source .venv/bin/activate
    python3 -m pip install 'Flask>=3,<4' 'Flask-Cors>=4,<6'
  else
    echo 'PENDING: Flask unavailable. Rerun with --install-deps to install into .venv.'
  fi
fi
if python3 -c 'import flask,flask_cors,werkzeug' 2>/dev/null; then
  python3 -m integration.run_original_http_stubbed
fi

printf '\n== Stage 3: React production build ==\n'
if [ "$INSTALL" -eq 1 ]; then
  if command -v npm >/dev/null 2>&1; then
    bash scripts/verify_frontend_build_v14_2.sh
  else
    echo 'PENDING: Node/npm unavailable, install Node 22 separately.'
  fi
else
  echo 'PENDING: npm ci requires dependencies; use --install-deps to approve downloads.'
fi

printf '\n== Stage 4: official Firebase Emulator integration ==\n'
if [ "$INSTALL" -eq 1 ]; then
  if [ ! -f .venv/bin/activate ]; then python3 -m venv .venv; fi
  source .venv/bin/activate
  python3 -m pip install -r backend/requirements.txt
  bash scripts/verify_official_emulators.sh
else
  echo 'PENDING: local Firebase emulators require dependencies; use --install-deps.'
fi

printf '\n== Stage 5: optional local Docker observability ==\n'
if [ "$DOCKER" -eq 1 ]; then
  command -v docker >/dev/null || { echo 'Docker missing' >&2; exit 2; }
  docker compose version >/dev/null
  if [ ! -f .env ]; then
    python3 - <<'PYSECRETS'
import secrets
from pathlib import Path
Path('.env').write_text('DEMO_SIGNING_KEY='+secrets.token_urlsafe(48)+'\nGRAFANA_ADMIN_PASSWORD='+secrets.token_urlsafe(32)+'\n')
PYSECRETS
    chmod 600 .env
  fi
  docker compose --profile observability up -d --build
  echo 'Docker containers remain running for your inspection; stop with docker compose --profile observability down'
  python3 scripts/verify_docker_stack.py --failover
else
  echo 'PENDING: Docker test requires explicit --with-docker approval.'
fi

printf '\n== Stage 6: updated acceptance status ==\n'
python3 -m scripts.release_gate_v14
printf '\nAll executed checks recorded. Manual proof of five flaws/three fixes and license/secret rotation remain outside automation.\n'
