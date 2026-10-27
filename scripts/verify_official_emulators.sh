#!/usr/bin/env bash
# On a Fedora system with Java, Node and Flask/Firebase Python packages installed,
# run the original Flask HTTP routes against Google's LOCAL Firebase emulators.
set -euo pipefail
cd "$(dirname "$0")/.."
# Use the project virtualenv when tests were installed locally on Fedora.
if [ -x .venv/bin/python ]; then export PATH="$PWD/.venv/bin:$PATH"; fi
export COURSESPHERE_USE_FIREBASE_EMULATORS=1
export GCLOUD_PROJECT=demo-coursesphere-vlab
export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
export FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000
export ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
unset FIREBASE_CREDENTIALS_FILE FIREBASE_DATABASE_URL GOOGLE_APPLICATION_CREDENTIALS OPENAI_API_KEY
python3 - <<'PY'
import importlib.util
required=['flask','flask_cors','firebase_admin','google.auth','werkzeug']
missing=[]
for mod in required:
    try: __import__(mod)
    except ImportError: missing.append(mod)
if missing:
    raise SystemExit('Missing Python packages: '+', '.join(missing)+'\nInstall: python3 -m pip install -r backend/requirements.txt')
PY
if command -v firebase >/dev/null 2>&1; then
  firebase emulators:exec --project "$GCLOUD_PROJECT" --only auth,database \
    'python3 -m integration.run_official_emulator_tests && python3 -m integration.run_r13_two_replica_quota'
elif command -v npx >/dev/null 2>&1; then
  npx --yes "firebase-tools@${FIREBASE_CLI_VERSION:-15.34.0}" emulators:exec --project "$GCLOUD_PROJECT" --only auth,database \
    'python3 -m integration.run_official_emulator_tests && python3 -m integration.run_r13_two_replica_quota'
else
  echo 'Need Firebase CLI: npm install -g firebase-tools' >&2
  exit 2
fi
