"""Content fingerprints of the files that actually affect each verification target.

The digests invalidate stale runtime evidence after a relevant source/config edit.
They are not signatures or proof of which infrastructure executed the test.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def fingerprint(paths: list[str]) -> str:
    h = hashlib.sha256()
    for rel in sorted(set(paths)):
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        h.update(rel.encode('utf-8') + b'\0')
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def files_below(folder: str, suffixes: set[str] | None = None) -> list[str]:
    base = ROOT / folder
    if not base.exists():
        return []
    return [p.relative_to(ROOT).as_posix() for p in base.rglob('*')
            if p.is_file() and (suffixes is None or p.suffix in suffixes)]


def frontend_fingerprint() -> str:
    root = ROOT / 'frontend'
    wanted = ['frontend/package.json', 'frontend/package-lock.json']
    wanted.extend(files_below('frontend/src'))
    for rel in ['index.html', 'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json']:
        if (root / rel).is_file():
            wanted.append('frontend/' + rel)
    return fingerprint(wanted)


def nginx_fingerprint() -> str:
    # The gateway proof starts backend.local_server, which imports the store and
    # security primitives. Changes to those modules must invalidate old proofs.
    return fingerprint([
        'ops/nginx/gateway.conf',
        'ops/nginx/nginx.conf',
        'backend/local_server.py',
        'backend/demo_store.py',
        'backend/security_core.py',
        'scripts/prove_nginx_native.py',
    ])


def docker_fingerprint() -> str:
    # Include compose definitions, all sandbox Python code, Docker build context,
    # Prometheus alerts, Grafana provisioning, and the verifier itself.
    paths = [
        'compose.yaml', 'backend/Dockerfile',
        'scripts/verify_docker_stack.py',
    ]
    paths.extend(files_below('backend', {'.py'}))
    paths.extend(files_below('ops/nginx'))
    paths.extend(files_below('ops/prometheus'))
    paths.extend(files_below('ops/grafana'))
    paths.extend(files_below('dashboard'))
    return fingerprint(paths)
