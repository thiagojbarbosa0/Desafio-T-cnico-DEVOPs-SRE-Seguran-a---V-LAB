#!/usr/bin/env bash
# V14.3: install project-local TypeScript before running its syntax parser.
# Mark a successful build ONLY after tsc and Vite have finished successfully.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/generated
rm -f evidence/generated/FRONTEND_BUILD_V13.json
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo 'ERRO: Node.js e npm sao necessarios para validar o React.' >&2
  exit 2
fi

echo '== [1/3] Instalando dependencias travadas do React (incluindo TypeScript) =='
(
  cd frontend
  npm ci --no-audit --no-fund
)

echo '== [2/3] Validando sintaxe TypeScript/TSX =='
node scripts/check_frontend_syntax_v14_2.cjs

echo '== [3/3] Compilando o React para producao =='
(
  cd frontend
  export VITE_USE_FIREBASE_EMULATORS=true
  npm run build
)

python3 - <<'PYBUILD'
import json
from pathlib import Path
from datetime import datetime, timezone
from scripts.source_fingerprint import frontend_fingerprint
out=Path('evidence/generated/FRONTEND_BUILD_V13.json')
out.write_text(json.dumps({
    'validated': True,
    'scope': 'React/TypeScript/Vite production build using demo Firebase emulator config',
    'generated_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'bash scripts/verify_frontend_build_v14_2.sh',
    'source_fingerprint': frontend_fingerprint(),
}, indent=2, ensure_ascii=False) + '\n')
print('Build React validado! Evidencia:', out)
PYBUILD
python3 -m scripts.release_gate_v14
