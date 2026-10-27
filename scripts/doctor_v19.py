#!/usr/bin/env python3
"""A static, offline-first status report for the owner (no browser or services needed).

Reads the release evaluator, rather than trusting cached pass/fail messages. Does
not install, delete, start, or stop any external service. Never displays secrets.
"""
from __future__ import annotations
import argparse
import html
import json
import shutil
import sys
from pathlib import Path
from scripts.release_gate_v19 import evaluate, save

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / 'evidence/generated/STATUS_V19.json'
PAGE = ROOT / 'reports/CONTROLE_V19.html'

LABELS = {
    'offline_regressions': 'Regressões e segurança offline',
    'nginx_real_failover': 'Nginx: balanceamento e falha',
    'original_flask_http_before_after': 'Flask original: prova HTTP antes/depois',
    'firebase_auth_database_emulators': 'Firebase Auth e banco: emuladores',
    'original_react_production_build': 'React: compilação de produção',
    'docker_observability_failover': 'Docker, Prometheus e Grafana',
    'five_findings_three_root_cause_fixes': '5 achados + 3 correções verificadas',
    'redistribution_and_upstream_rotation': 'Permissão de publicação e credencial upstream',
}
COMMANDS = {
    'offline_regressions': 'bash scripts/verify_v19.sh',
    'nginx_real_failover': 'python3 scripts/prove_nginx_native.py',
    'original_flask_http_before_after': '.venv/bin/python -m integration.run_original_http_stubbed',
    'firebase_auth_database_emulators': 'bash scripts/verify_official_emulators.sh',
    'original_react_production_build': 'bash scripts/verify_frontend_build_v14_2.sh',
    'docker_observability_failover': 'python3 scripts/verify_docker_stack.py --failover',
    'five_findings_three_root_cause_fixes': 'Revisar docs/SECURITY_MATRIX_V14.md e docs/RELATORIO_PENTEST_V12.md',
    'redistribution_and_upstream_rotation': 'Confirmar licença e notificar o responsável pela credencial',
}


def build_status():
    gate = evaluate()
    return {
        'version': 'V19',
        'project': 'CourseSphere original + laboratório AppSec/SRE isolado',
        'implementation_estimate_percent': gate['implementation_readiness_estimate_percent'],
        'verified_acceptance_percent': gate['weighted_acceptance_verified_percent'],
        'ready_for_submission': gate['ready_for_submission'],
        'gates': [
            {'id': key, 'name': LABELS[key], 'weight': value['weight'],
             'verified': bool(value['passed']), 'next_step': COMMANDS[key],
             'note': value['reason']}
            for key, value in gate['gates'].items()
        ],
        'local_capabilities': {
            'python': bool(shutil.which('python3')),
            'node': bool(shutil.which('node')),
            'npm': bool(shutil.which('npm')),
            'nginx': bool(shutil.which('nginx')),
            'docker_cli': bool(shutil.which('docker')),
            'java': bool(shutil.which('java')),
            'project_venv_present': (ROOT / '.venv/bin/python').is_file(),
        },
        'warnings': [
            'A aprovação pelo gate não é previsão de aprovação na seleção.',
            'Flask HTTP com Firebase simulado não equivale a Firebase Emulator.',
            'Agora os clientes Firebase não podem gravar diretamente no RTDB; testar as regras ao vivo.',
            'O Nginx principal mede o laboratório; a prova Flask/Nginx adicional é opcional e separada.',
            'Não publicar o laboratório nem credenciais de terceiros.',
        ],
        'reference': 'HANDOFF_MESTRE_V19.md',
    }


def render_html(status):
    esc = html.escape
    cards = []
    for gate in status['gates']:
        badge = 'Comprovado' if gate['verified'] else 'Pendente'
        klass = 'success' if gate['verified'] else 'pending'
        cards.append(f'''<tr><td><strong>{esc(gate['name'])}</strong><small>{esc(gate['note'])}</small></td>
<td><span class="pill {klass}">{badge}</span></td><td>{gate['weight']}%</td>
<td><code>{esc(gate['next_step'])}</code></td></tr>''')
    rows = '\n'.join(cards)
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CourseSphere · Controle V19</title><style>
:root{{--bg:#f5f7fa;--paper:#fff;--ink:#172334;--muted:#64748b;--line:#dce3eb;--blue:#265ca3}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,Arial,sans-serif}}
main{{max-width:1060px;margin:0 auto;padding:32px 22px 64px}}header{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:24px}}
h1{{font-size:26px;margin:3px 0}}h2{{font-size:18px;margin:0 0 12px}}p{{color:var(--muted)}}.eyebrow{{font-size:12px;letter-spacing:.13em;color:var(--blue);font-weight:700}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.card{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:22px}}
.number{{font-size:36px;font-weight:700;letter-spacing:-.04em}}.bar{{height:9px;background:#e3e9ef;border-radius:10px;overflow:hidden;margin-top:10px}}.fill{{height:100%;background:var(--blue)}}
table{{width:100%;border-collapse:collapse;text-align:left}}th,td{{border-bottom:1px solid var(--line);padding:14px 10px;vertical-align:top}}th{{font-size:12px;color:var(--muted)}}small{{display:block;color:var(--muted);margin-top:2px}}
.pill{{white-space:nowrap;border-radius:99px;padding:4px 9px;font-size:12px;font-weight:600}}.success{{background:#e7f4ed;color:#126037}}.pending{{background:#f1f3f5;color:#4b5563}}
code{{font-size:12px;color:#314861;overflow-wrap:anywhere}}ul{{padding-left:22px}}li{{margin:6px 0}}.tablewrap{{overflow-x:auto}}
@media(max-width:650px){{.grid{{grid-template-columns:1fr}}main{{padding:20px 12px}}th,td{{padding:10px 6px}}}}
</style></head><body><main><header><div class="eyebrow">V-LAB / APPSEC + SRE</div>
<h1>CourseSphere · Controle da entrega</h1>
<p>Status derivado de evidências verificadas para o código atual. Percentuais são internos e não representam nota.</p></header>
<div class="grid"><section class="card"><h2>Implementação estimada</h2><div class="number">{status['implementation_estimate_percent']}%</div>
<div class="bar"><div class="fill" style="width:{status['implementation_estimate_percent']}%"></div></div>
<p>Estimativa qualitativa de engenharia; não substitui testes.</p></section>
<section class="card"><h2>Aceite comprovado</h2><div class="number">{status['verified_acceptance_percent']}%</div>
<div class="bar"><div class="fill" style="width:{status['verified_acceptance_percent']}%"></div></div>
<p>Validações com evidência vinculada à versão.</p></section></div>
<section class="card" style="margin-top:18px"><h2>Critérios de validação</h2><div class="tablewrap"><table>
<thead><tr><th>Critério</th><th>Situação</th><th>Peso interno</th><th>Próxima ação</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
<section class="card" style="margin-top:18px"><h2>O que considerar antes da entrega</h2><ul>
{''.join(f'<li>{esc(w)}</li>' for w in status['warnings'])}</ul>
<p>Leia <code>docs/HANDOFF_V19.md</code> para histórico, decisões e comandos seguros de execução.</p></section>
</main></body></html>'''


def run():
    status = build_status()
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    PAGE.write_text(render_html(status), encoding='utf-8')
    save()
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true', help='Exit nonzero if any acceptance gate remains')
    args = parser.parse_args()
    report = run()
    print(f"CourseSphere {report['version']}: implementação estimada {report['implementation_estimate_percent']}%, "
          f"aceite comprovado {report['verified_acceptance_percent']}%")
    print('Relatório:', PAGE)
    if args.strict and not report['ready_for_submission']:
        sys.exit(1)
