#!/usr/bin/env bash
# Opt-in integration checks. No installations/containers without explicit flags.
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'python3 -m scripts.doctor_v16 || true' EXIT
if [ -x .venv/bin/python ]; then
  export PATH="$PWD/.venv/bin:$PATH"
fi
bash scripts/fedora_validation_v15.sh "$@"
