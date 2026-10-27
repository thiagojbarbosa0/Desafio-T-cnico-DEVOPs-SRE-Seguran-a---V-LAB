#!/usr/bin/env bash
# Full Fedora validation only when explicitly requested by the owner.
# --install-deps and --with-docker retain their meaning from V14.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then
  export PATH="$PWD/.venv/bin:$PATH"
fi
bash scripts/fedora_validation_v13.sh "$@"
python3 scripts/security_preflight_v14.py
python3 -m scripts.release_gate_v15
