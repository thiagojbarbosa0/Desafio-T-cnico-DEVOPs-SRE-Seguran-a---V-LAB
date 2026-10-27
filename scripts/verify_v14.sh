#!/usr/bin/env bash
# V14 reproducible verification. Fail closed; preserve evidence file provenance.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/verify_v13.sh
python3 scripts/security_preflight_v14.py
python3 -m scripts.release_gate_v14
