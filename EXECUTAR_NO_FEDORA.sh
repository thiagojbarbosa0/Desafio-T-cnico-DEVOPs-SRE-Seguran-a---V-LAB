#!/usr/bin/env bash
# Run from anywhere, including an extracted ZIP with spaces in the parent path.
set -uo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 2
if ! command -v python3 >/dev/null 2>&1; then
  echo 'ERRO: Python 3 nao encontrado. Instale com: sudo dnf install python3' >&2
  exit 2
fi
cd -- "$ROOT" || exit 2
exec python3 scripts/diagnostico_total_r13.py "$@"
