# Optional original Flask + React Docker stack (V19.7)

**Why it exists.** The original Compose demonstration runs an independent synthetic course CRUD sandbox. The official CourseSphere is a Flask + React course recommender. For evaluation, the distinction is critical: we now provide a *separate*, minimal, local-only Docker Compose stack running TWO instances of the **real original patched Flask API** and the real React frontend, fronted by Nginx. This does **not** replace the demo stack.

## Running on Fedora (not executed in the ChatGPT container)

Prerequisites: Docker Compose V2, outbound connectivity for initial image/dependency installation, and a free localhost port 8081. From the project root:

```bash
docker compose -f compose.official.yaml config --quiet
docker compose -f compose.official.yaml up --build -d
python3 scripts/verify_official_docker_v19_7.py --failover
docker compose -f compose.official.yaml down --remove-orphans
```

Browser: <http://127.0.0.1:8081/>. Health: <http://127.0.0.1:8081/health>.

The **public health route works without credentials**. Login/profile/chat/recommendation depend on an authorized Firebase project or explicitly configured official emulators; the default image does not bundle secrets or contact the upstream project. Firebase web SDK is built for emulators (`VITE_USE_FIREBASE_EMULATORS=true`) but **an emulator service is not started here**. Do not interpret a working landing page as a successful end-to-end authenticated flow. The independent `scripts/verify_official_emulators.sh` remains the authoritative auth/database integration proof.

The API's `/metrics` currently requires direct loopback inside each Flask process and is not scraped from these containers; Prometheus/Grafana in `compose.yaml` remain for the synthetic demo only. The official stack does not claim full production observability.

No runtime port is exposed on 0.0.0.0; all external traffic is localhost:8081. API and frontend containers communicate over a private Compose network. No real secrets, paid APIs, or production Firebase credentials are included. Gunicorn access logs are disabled to avoid dumping URL query parameters; the Flask and edge layers generate route-only structured logs.

## Distinguishing proof levels

* `scripts/prove_original_flask_nginx.py` exercises native Nginx + REAL Flask with synthetic Firebase adapters (already implemented in prior versions).
* `scripts/verify_official_docker_v19_7.py` exercises the ORIGINAL Flask container images + Nginx + React health, but not auth/Firebase or Grafana.
* `scripts/verify_official_emulators.sh` tests REAL Flask/Firebase Auth/RTDB emulator integrations on localhost; it does not constitute a cloud production test.
* `scripts/verify_docker_stack.py` remains exclusively for the separate educational sandbox.

This stack is an engineering improvement and a prepared reproducible demonstration; **not a completed validation until actually executed**.
