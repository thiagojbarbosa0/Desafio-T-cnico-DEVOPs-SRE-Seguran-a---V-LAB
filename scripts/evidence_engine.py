#!/usr/bin/env python3
"""Offline forensic runner: original-vs-remediated handler behavior.

Only synthetically executes selected function bodies. Does not import original
Flask/Firebase modules, make network requests or access real credentials.
"""
from __future__ import annotations
import ast
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.origin_harness import execute_handler, ORIGINAL, PATCHED

FINDINGS=[
 {'id':'CS-01','name':'Cadastro privilegiado sem autenticação no backend', 'category':'A07:2021 Identification and Authentication Failures', 'severity':'ALTA (condicionada à exposição da API)', 'method':'handler', 'function':'create_user', 'params':{'payload':{'email':'synthetic@example.invalid','password':'SYNTHETIC_PASSWORD'}}, 'expected_old':200,'expected_new':410,
  'root_cause':'O endpoint anônimo usava a API administrativa do Firebase para criar contas.','fix':'A rota administrativa foi desativada (410); cadastro passou para createUserWithEmailAndPassword no frontend.'},
 {'id':'CS-02','name':'ID token aceito em query string', 'category':'A02:2021 Cryptographic Failures / CWE-598', 'severity':'MÉDIA', 'method':'handler', 'function':'get_user_info', 'params':{'query_token':'SYNTHETIC_TOKEN'}, 'expected_old':200,'expected_new':401,
  'root_cause':'O GET lia request.args.get("id_token"), permitindo credenciais em URL e logs.','fix':'Aceitar somente Authorization: Bearer; frontend alterado para cabecalho.'},
 {'id':'CS-03','name':'Detalhes internos de exceções retornados', 'category':'A05:2021 Security Misconfiguration / CWE-209', 'severity':'MÉDIA (dependente de dados nos erros)', 'method':'handler', 'function':'get_user_info', 'params':{'query_token':'SYNTHETIC_TOKEN','firebase_profile_error':'SYNTHETIC_INTERNAL_TRACE_MARKER'}, 'new_params':{'token':'SYNTHETIC_TOKEN','firebase_profile_error':'SYNTHETIC_INTERNAL_TRACE_MARKER'},'expected_old':400,'expected_new':500,
  'root_cause':'Interpolação str(e) nas respostas HTTP.','fix':'Resposta generica e sem informacoes internas.'},
 {'id':'CS-04','name':'Consulta de recomendação anônima', 'category':'A07:2021 Identification and Authentication Failures / A04 Insecure Design', 'severity':'BAIXA/MÉDIA (backend original retorna stub)', 'method':'handler', 'function':'get_user_query', 'params':{'payload':{'query':'Safe synthetic search'}},'expected_old':200,'expected_new':401,
  'root_cause':'try_get_user_info(None) falha silenciosamente, mas a rota continua sem credenciais.','fix':'Obrigatoriedade de token validado e limite no tamanho do prompt.'},
 {'id':'CS-05','name':'Mensagens sem limite de quantidade', 'category':'A04:2021 Insecure Design / CWE-770', 'severity':'MÉDIA (impacto depende de limites da infraestrutura)', 'method':'handler', 'function':'save_chat','params':{'token':'SYNTHETIC_TOKEN','payload':{'messages':[{'sender':'alice','content':'safe','messageID':'abc'}]*101}},'expected_old':200,'expected_new':400,
  'root_cause':'Lista de mensagens enviada diretamente ao Firebase, sem limite por requisição.','fix':'Validar no backend maximo de 100 mensagens, formato dos campos e limitar body em 32 KiB no Flask.'},
 {'id':'CS-06','name':'Perfil aceita texto excessivamente grande', 'category':'A04:2021 Insecure Design / CWE-20', 'severity':'BAIXA/MÉDIA', 'method':'handler','function':'set_user_info', 'params':{'payload':{'id_token':'SYNTHETIC_TOKEN','about':'A'*2000}},'new_params':{'token':'SYNTHETIC_TOKEN','payload':{'about':'A'*2000}},'expected_old':200,'expected_new':400,
  'root_cause':'Campos do perfil eram persistidos sem validacao de comprimento/tipo.','fix':'Validacao de esquema, quantidade de entradas e comprimentos por campo.'},
]

def location(filename, pattern):
    lines=filename.read_text().splitlines()
    for i,line in enumerate(lines,1):
        if pattern in line:return i
    return None

def status_code(result):return result[1]

def main():
    entries=[]
    for item in FINDINGS:
        args=item['params']
        old,calls_before=execute_handler(ORIGINAL,item['function'],**args)
        new,calls_after=execute_handler(PATCHED,item['function'],**item.get('new_params',args))
        expected=(item['expected_old'],item['expected_new'])
        got=(status_code(old),status_code(new))
        if got!=expected:
            raise SystemExit(f"FAIL: {item['id']} expected {expected}, got {got}")
        entries.append({k:v for k,v in item.items() if k not in ('params','new_params','expected_old','expected_new') } |
            {'evidence_type':'isolated_original_function_execution', 'original_status':got[0], 'patched_status':got[1],
             'result':'BEHAVIOR_CONFIRMED_IN_HANDLER_HARNESS','real_external_service_tested':False,
             'original_source':'audit/baseline/endpoints_original.txt','patched_source':'backend/endpoints.py',
             'original_line':location(ORIGINAL,'def '+item['function']+'('),
             'patched_line':location(PATCHED,'def '+item['function']+'('),
             'original_calls':[x[0] for x in calls_before], 'patched_calls':[x[0] for x in calls_after]})
    key_meta=json.loads((ROOT/'audit/baseline/credential_exposure_metadata.json').read_text())
    if not {'client_id','client_secret'}.issubset(key_meta['fields_with_values']):
        raise SystemExit('Original credential audit metadata not found')
    if (ROOT/key_meta['path_in_original']).exists():
        raise SystemExit('Original secret must not be included in derivative')
    entries.append({'id':'CS-07','name':'Credencial de serviço externo no ZIP original','category':'A02:2021 Cryptographic Failures / CWE-798',
        'severity':'ALTA se a credencial ainda for valida', 'evidence_type':'original_archive_local_metadata_inspection',
        'result':'SECRET_FIELDS_CONFIRMED_VALUES_EXCLUDED_FROM_DERIVATIVE', 'real_external_service_tested':False,
        'root_cause':'Arquivo reddit_key.json com client_id e client_secret nao estava excluido do pacote original.',
        'fix':'Arquivo real removido do projeto derivado, template sem valores e .gitignore; revogacao depende do dono da credencial.',
        'source':key_meta['path_in_original'],'fields_present':key_meta['fields_present'],
        'original_status':None,'patched_status':None})
    entries.append({'id':'CS-08','name':'CORS aberto sem lista de origens','category':'A05:2021 Security Misconfiguration',
        'severity':'BAIXA/MÉDIA (isoladamente nao burla autenticacao)', 'evidence_type':'static_source_comparison',
        'result':'SOURCE_PATTERN_CONFIRMED','real_external_service_tested':False,
        'root_cause':'CORS(app) sem restricao de origens.','fix':'Origens explicitamente configuradas em ALLOWED_ORIGINS.',
        'original_source':'audit/baseline/endpoints_original.txt','patched_source':'backend/endpoints.py',
        'original_line':location(ORIGINAL,'CORS(app)'), 'patched_line':location(PATCHED,'CORS(app, origins='),
        'original_status':None,'patched_status':None})
    entries.append({'id':'CS-09','name':'Debug habilitado na execução direta do Flask','category':'A05:2021 Security Misconfiguration',
        'severity':'ALTA apenas se exposto em ambiente nao local','evidence_type':'static_source_comparison',
        'result':'SOURCE_PATTERN_CONFIRMED','real_external_service_tested':False,
        'root_cause':'app.run(debug=True) no ponto de entrada.','fix':'Debug desabilitado por padrao.',
        'original_source':'audit/baseline/endpoints_original.txt','patched_source':'backend/endpoints.py',
        'original_line':location(ORIGINAL,'app.run(debug=True)'), 'patched_line':location(PATCHED,'app.run(debug=False)'),
        'original_status':None,'patched_status':None})
    report={'version':'V7','generated_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'scope':'Local original source package + offline isolated handler execution; NO live exploit',
        'original_source_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        'patched_source_sha256':hashlib.sha256(PATCHED.read_bytes()).hexdigest(),
        'counts':{'original_function_behaviors_reproduced':len(FINDINGS), 'static_or_metadata_observations':3,
                  'production_exploit_confirmed':0}, 'findings':entries,
        'caveats':['No Flask runtime installed in this session; handler bodies tested with stubbed Flask/Firebase context.',
                   'No external Firebase/Reddit API was accessed.',
                   'A behavior reproduced by a stubbed handler is not automatically an exploitable production vulnerability.',
                   'Credentials in the original archive must be revoked by their owner even though omitted from derivative.']}
    out=ROOT/'evidence'/'generated'
    out.mkdir(parents=True,exist_ok=True)
    (out/'ORIGIN_BEFORE_AFTER.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# Evidence Engine V7 — resultados reproduziveis', '',
           '**Método:** execucao dos corpos de funcoes originais e corrigidas em contexto simulado, com dados sinteticos. **Nao e pentest HTTP do Flask em producao.**','',
           '| ID | Achado no original | Antes | Depois | Evidencia |','|---|---|---|---|---|']
    for x in entries:
        before='HTTP '+str(x['original_status']) if x['original_status'] else 'Estatico/metadados'
        after='HTTP '+str(x['patched_status']) if x['patched_status'] else 'Arquivo/configuracao'
        lines.append(f"| {x['id']} | {x['name']} | {before} | {after} | {x['evidence_type']} |")
    lines.extend(['','As provas permitem verificar alteracoes no codigo, nao demonstram impacto em instancias externas.',
                  'Para cada item, ver detalhes de categoria, causa raiz, severidade condicional e linhas em `ORIGIN_BEFORE_AFTER.json`.',''])
    (out/'RESUMO_EVIDENCIAS.md').write_text('\n'.join(lines))
    print(f"Evidence Engine: {len(FINDINGS)} original handler behaviors confirmed + 3 static findings, 0 live-service exploits claimed")
    return report

if __name__=='__main__':main()
