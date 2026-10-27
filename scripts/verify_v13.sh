#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/generated
printf '\n[1/4] Testes offline - só contam se executados nesta rodada\n'
python3 - <<'PY'
import json, re, subprocess, sys
from pathlib import Path
from datetime import datetime,timezone
from scripts.release_gate_v13 import offline_fingerprint
root=Path('.')
command=['bash','scripts/verify.sh']
r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(root/'evidence/generated/TESTES_OFFLINE_V13.log').write_text(r.stdout)
print('\n'.join(r.stdout.splitlines()[-12:]))
match=re.findall(r'Ran (\d+) tests.*?\n\nOK\b',r.stdout,re.S)
count=int(match[-1]) if match else 0
ok=r.returncode==0 and count>=134
artifact={'validated':ok,'tests_run':count,'failures':0 if ok else 1,'errors':0 if ok else 1,
 'source_fingerprint':offline_fingerprint(),
 'generated_utc':datetime.now(timezone.utc).isoformat(),
 'command':'bash scripts/verify.sh','exit_code':r.returncode}
(root/'evidence/generated/TESTES_OFFLINE_V13.json').write_text(json.dumps(artifact,indent=2)+'\n')
if not ok: sys.exit(1)
PY
printf '\n[2/4] Nginx real, se existir\n'
if command -v nginx >/dev/null 2>&1; then
  python3 scripts/prove_nginx_native.py
else
  rm -f evidence/generated/NGINX_LIVE_V9.json
  echo 'NOT TESTED: Nginx indisponível'
fi
printf '\n[3/4] Flask HTTP original + fake Firebase, se libs existirem\n'
HTTP_PYTHON=python3
if [ -x .venv/bin/python ] && .venv/bin/python -c 'import flask,flask_cors,werkzeug' >/dev/null 2>&1; then
  HTTP_PYTHON=.venv/bin/python
fi
if "$HTTP_PYTHON" -c 'import flask,flask_cors,werkzeug' >/dev/null 2>&1; then
  "$HTTP_PYTHON" -m integration.run_original_http_stubbed
else
  rm -f evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json
  echo 'NOT TESTED: Flask e Flask-Cors indisponíveis; será executado no Fedora/CI'
fi
printf '\n[4/4] Gate ponderado de evidências\n'
python3 scripts/release_gate_v13.py
