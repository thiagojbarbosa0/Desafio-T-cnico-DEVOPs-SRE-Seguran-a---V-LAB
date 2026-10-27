#!/usr/bin/env python3
"""CourseSphere R13 self-contained Fedora-friendly test reporter.

Default is offline and non-destructive. --full additionally installs dependencies
and exercises original Flask/Firebase emulators, frontend production build and
optional Docker gateway; checks remain separately labeled (PASS/FAIL/SKIP).
Does not change project versions, push code, require accounts or claim release.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, cmd: list[str], output: Path, *, timeout: int = 120,
             env: dict | None = None, skip_reason: str | None = None) -> dict:
    entry = {'name': name, 'status': 'SKIP', 'reason': None,
             'duration_seconds': 0, 'log': None}
    if skip_reason:
        entry['reason'] = skip_reason
        return entry
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    try:
        with output.open('w', encoding='utf-8') as log:
            os.chmod(output, 0o600)
            completed = subprocess.run(cmd, cwd=ROOT, stdout=log,
                                       stderr=subprocess.STDOUT,
                                       timeout=timeout, env=env, check=False)
        entry['status'] = 'PASS' if completed.returncode == 0 else 'FAIL'
        entry['exit_code'] = completed.returncode
        entry['log'] = output.name
    except FileNotFoundError:
        entry['status'] = 'SKIP'
        entry['reason'] = 'Executable not installed'
        output.unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        entry['status'] = 'FAIL'
        entry['reason'] = 'Timeout'
        entry['log'] = output.name
    except OSError:
        entry['status'] = 'FAIL'
        entry['reason'] = 'Unable to write or execute local check'
    finally:
        entry['duration_seconds'] = round(time.monotonic() - start, 2)
    return entry


def run(*, full: bool, out_dir: Path, skip_native_nginx: bool = False) -> dict:
    out_dir = out_dir.expanduser().resolve()
    if out_dir == ROOT or out_dir == ROOT.parent:
        raise ValueError('Reports must be in a dedicated subdirectory')
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    logs = out_dir / 'logs'
    logs.mkdir(exist_ok=True)
    os.chmod(logs, 0o700)
    steps = []
    safe_env = os.environ.copy()
    # Never accidentally feed live project credentials into an emulator test.
    for key in ('FIREBASE_CREDENTIALS_FILE', 'FIREBASE_DATABASE_URL',
                'GOOGLE_APPLICATION_CREDENTIALS', 'OPENAI_API_KEY'):
        safe_env.pop(key, None)

    def check(name, cmd, *, timeout=120, reason=None, environment=None):
        entry = run_step(name, cmd, logs / (name + '.log'), timeout=timeout,
                         skip_reason=reason, env=environment or safe_env)
        steps.append(entry)
        print(f"[{entry['status']}] {name}" + (f" ({entry['reason']})" if entry['reason'] else ''), flush=True)
        return entry

    py = sys.executable
    check('python_regression_offline', ['bash', 'scripts/verify.sh'], timeout=240)
    check('npm_lock_structure', [py, 'scripts/npm_lock_integrity_vlab.py'], timeout=45)
    node_checks = ('test_session_gate_v19_2.cjs',
                   'test_user_chats_runtime_v19_2.cjs',
                   'test_profile_session_runtime_v19_2.cjs')
    for index, filename in enumerate(node_checks, 1):
        check(f'node_session_{index}', ['node', 'scripts/' + filename],
              reason=None if shutil.which('node') else 'Node.js unavailable', timeout=30)
    check('nginx_native_gateway', [py, 'scripts/prove_nginx_native.py'], timeout=75,
          reason='Disabled by request' if skip_native_nginx else
                 ('Nginx unavailable' if not shutil.which('nginx') else None))
    check('nginx_official_contract', [py, 'scripts/prove_official_nginx_contract_v19_7.py'],
          timeout=75,
          reason='Disabled by request' if skip_native_nginx else
                 ('Nginx unavailable' if not shutil.which('nginx') else None))
    check('release_gate_derived', [py, '-m', 'scripts.release_gate_r14'], timeout=40)

    if full:
        frontend = ROOT / 'frontend'
        if shutil.which('npm'):
            check('frontend_npm_ci', ['npm', 'ci', '--no-audit', '--no-fund',
                                    '--prefix', str(frontend)], timeout=600)
            if steps[-1]['status'] == 'PASS':
                check('frontend_build', ['npm', 'run', 'build', '--prefix', str(frontend)],
                      environment=dict(safe_env, VITE_USE_FIREBASE_EMULATORS='true'), timeout=240)
            else:
                check('frontend_build', ['npm', 'run', 'build', '--prefix', str(frontend)],
                      reason='npm ci did not pass')
        else:
            check('frontend_npm_ci', ['npm'], reason='npm unavailable')
            check('frontend_build', ['npm'], reason='npm unavailable')
        venv = ROOT / '.venv'
        check('python_venv', [py, '-m', 'venv', str(venv)], timeout=70)
        vpython = str(venv / 'bin/python')
        if steps[-1]['status'] == 'PASS':
            check('backend_pip', [vpython, '-m', 'pip', 'install', '-r',
                                  'backend/requirements.txt'], timeout=480)
            if steps[-1]['status'] == 'PASS':
                # Integrations are run only with a named emulator project on
                # loopback; scripts/verify_official_emulators.sh enforces this.
                check('flask_firebase_emulators', ['bash', 'scripts/verify_official_emulators.sh'],
                      environment=dict(safe_env, PATH=str(venv / 'bin') + os.pathsep + safe_env.get('PATH', '')),
                      timeout=900)
            else:
                check('flask_firebase_emulators', ['bash'], reason='Backend dependencies unavailable')
        else:
            check('backend_pip', [py], reason='Virtualenv creation failed')
            check('flask_firebase_emulators', ['bash'], reason='Virtualenv creation failed')
        # Docker is not started automatically: the official compose project
        # has a fixed name and could conflict with a pre-existing user stack.
        check('docker_official_stack', ['docker'],
              reason='Safety hold: start existing named Docker stack only after checking ownership')
    else:
        for name in ('frontend_build', 'backend_pip', 'flask_firebase_emulators',
                     'docker_official_stack'):
            check(name, ['true'], reason='Full mode not requested')

    counts = {name: sum(step['status'] == name for step in steps)
              for name in ('PASS', 'FAIL', 'SKIP')}
    report = {
        'schema_version': 1,
        'project_line': 'R14 derived from V19.9/R13; NOT the V19.15 checkout',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'offline locally executed checks, optional dependency setup and integration',
        'full_mode': bool(full),
        'counts': counts,
        'steps': steps,
        'docker_firebase_acceptance_claim': False,
        'ready_for_submission': False,
    }
    output = out_dir / 'RESUMO.json'
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.chmod(output, 0o600)
    (out_dir / 'LEIA_O_RESULTADO.txt').write_text(
        'CourseSphere R14 - diagnostico local\n'
        + 'PASS={PASS} FAIL={FAIL} SKIP={SKIP}\n'.format(**counts)
        + 'Nenhum resultado offline substitui Firebase/Docker integrado.\n'
        + 'Relatorio: ' + str(output) + '\n', encoding='utf-8')
    print('Relatorio:', output)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='Instala deps e tenta emuladores locais')
    parser.add_argument('--skip-nginx', action='store_true')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args(argv)
    target = args.output or (Path.home() / 'CourseSphere-Diagnosticos' /
                             datetime.now().strftime('%Y%m%d_%H%M%S'))
    try:
        report = run(full=args.full, out_dir=target, skip_native_nginx=args.skip_nginx)
    except (OSError, ValueError) as exc:
        print('Erro ao preparar o diagnóstico:', type(exc).__name__, file=sys.stderr)
        return 2
    return 1 if report['counts']['FAIL'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
