#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export COURSESPHERE_USE_FIREBASE_EMULATORS=1
export GCLOUD_PROJECT=demo-coursesphere-vlab
export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
export FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000
export ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
unset FIREBASE_CREDENTIALS_FILE FIREBASE_DATABASE_URL GOOGLE_APPLICATION_CREDENTIALS OPENAI_API_KEY
cd backend
exec python3 -m flask --app endpoints:app run --no-reload --no-debugger --host 127.0.0.1 --port 5000
