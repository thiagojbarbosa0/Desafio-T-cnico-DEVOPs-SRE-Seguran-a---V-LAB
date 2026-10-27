#!/usr/bin/env bash
# Full integration requires a host with Python, Java, npm, and optionally Docker.
# --install-deps explicitly authorizes installing free dependencies; no upstream credentials used.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/fedora_validation_v13.sh "$@"
python3 -m scripts.release_gate_v14
