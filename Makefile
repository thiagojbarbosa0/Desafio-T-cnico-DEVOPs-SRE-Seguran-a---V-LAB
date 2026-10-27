.PHONY: test verify evidence sbom resilience local docker clean nginx-proof firebase-emulators
verify test:
	bash scripts/verify.sh
evidence:
	python3 scripts/evidence_engine.py
sbom:
	python3 scripts/generate_sbom.py
resilience:
	python3 scripts/prove_resilience_local.py
local:
	bash scripts/start_local.sh
docker:
	bash scripts/start_docker.sh
clean:
	rm -rf .local/*.sqlite3 .local/*.sqlite3-shm .local/*.sqlite3-wal

# Requires host Nginx (native proof, no Docker or Firebase).
nginx-proof:
	python3 scripts/prove_nginx_native.py
# Requires local Firebase CLI/Java and Python Flask/firebase-admin packages.
firebase-emulators:
	bash scripts/verify_official_emulators.sh
