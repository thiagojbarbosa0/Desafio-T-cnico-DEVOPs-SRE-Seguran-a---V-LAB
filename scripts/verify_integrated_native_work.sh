#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export COURSESPHERE_USE_FIREBASE_EMULATORS=1 GCLOUD_PROJECT=demo-coursesphere-vlab
export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000
unset FIREBASE_CREDENTIALS_FILE FIREBASE_DATABASE_URL GOOGLE_APPLICATION_CREDENTIALS OPENAI_API_KEY
firebase emulators:exec --project "$GCLOUD_PROJECT" --only auth,database 'python3 -m scripts.prove_integrated_native_work'
