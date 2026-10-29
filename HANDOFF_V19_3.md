# COURSESPHERE V19.3 — HANDOFF ATUAL

**Data:** 23/10/2026 · **Origem:** `CourseSphere_V19_2_CONTINUIDADE_WORK.zip` · **Escopo:** AppSec + SRE do CourseSphere original (Flask + React + Firebase) e laboratório sintético isolado.

## 1. Objetivo do edital

A banca prioriza cinco vulnerabilidades reais e independentes em ao menos duas categorias, com passos e impacto; três correções de causa raiz testadas; duas medidas de hardening; logs, métricas, 2 SLIs/2 SLOs; Docker de backend/frontend, duas réplicas balanceadas por Nginx; relatório claro e reprodutível. Extras como CI, scanner, STRIDE, Grafana, failover e Firebase Emulator são diferenciais, mas **não substituem o mínimo**.

Não reconstruir o CourseSphere nem confundir o laboratório didático de cursos/aulas com vulnerabilidades do código upstream. A própria aplicação upstream está incompleta em recomendações e CRUD de cursos; não alegar o contrário.

## 2. O que o Work entregou na V19.1 e o que veio da V19.2

- Work V19.1: 227 testes offline, build React, 15 testes HTTP Flask com Firebase simulado, duas instâncias Flask atrás do Nginx nativo; correção de tratamento HTTP 413. Registros históricos de 42% do aceite interno para V19.1.
- V19.2: isolamento de sessão em UserChats, perfil e chat; testes Node de A→B, A→B→A, logout e atraso de requisição. Após alterar React, o build V19.1 perdeu validade para a versão nova. Aceite V19.2: 35% (3/8), não uma nota prevista.
- As cinco questões principais de upstream permanecem em `docs/REVISAO_ACHADOS_WORK.md`. F01/F02 têm **severidade condicional** e não podem ser alegadas como escalada real sem política do produto confirmada. F03/F05/F06 possuem evidência HTTP mais forte. D01/D02 são defeitos de versões derivadas, não achados upstream.

## 3. Implementado nesta rodada — V19.3

### Proteção de URL e privacidade de logs na camada Nginx

- `ops/nginx/nginx.conf` (novo): configura logs de acesso **estruturados em JSON**, usando somente método, `$uri` (caminho sem query), status, request ID, backend e duração. Nunca inclui URL completa, query, Referer nem cabeçalhos de autenticação.
- `compose.yaml`: monta explicitamente o `nginx.conf` novo, além do gateway que já existia.
- `ops/nginx/gateway.conf`: bloqueia no edge parâmetros `id_token`, `access_token`, `auth_token` e `api_key` (HTTP 401). Em `/api/`, **qualquer query string**, inclusive nome de parâmetro codificado, recebe HTTP 400. As rotas Flask oficiais não usam query para operações legítimas: autenticação via Bearer e payload JSON. **Mudança de contrato intencional**: se a API futuramente exigir filtros/paginação via query, atualizar a política com allowlist testada em vez de desativar o bloqueio indiscriminadamente.
- `scripts/prove_nginx_native.py`: executa Nginx real + duas instâncias sintéticas, verifica 40 requisições distribuídas, 8 após derrubar réplica, bloqueio de `/metrics`, HTTP 401 para token em query, HTTP 400 para query comum/codificada e ausência de marcador nos logs de acesso. Prova executada: PASS.
- `scripts/prove_original_flask_nginx.py`: mesma prova adicional preparada para duas instâncias **Flask verdadeiras com Firebase simulado**, incluindo log redaction; não executada nesta rodada por falta de Flask.
- `scripts/check_nginx_main_config_v19_3.py`: verifica sintaxe do Nginx principal + gateway, sem subir containers. Executado com Nginx real: PASS.
- `scripts/release_gate_v19_3.py`: V19.3 só aceita a prova Nginx se houver log redaction, bloqueio de query e hash atual dos arquivos, além dos critérios anteriores. Documenta explicitamente limites dos resultados.

### Mais provas prontas para Firebase Emulator

- `integration/test_official_emulators.py`: de 21 para **23 cenários preparados**; o 22º exercita dois listeners Flask HTTP contra a mesma quota no banco emulado; o 23º impede leitura/gravação autenticada dos contadores `server_security`. Testes de quota evitam cruzar inadvertidamente a virada da janela de 60 segundos.
- `integration/run_official_emulator_tests.py` e gates atualizados para exigir exatamente 23 testes, zero skips, zero erros e hash correto.
- Esses testes **NÃO foram executados** com o Firebase Emulator neste ambiente. Os dois listeners do teste 22 compartilham o mesmo processo Python, de modo que ele **não substitui** uma prova de duas réplicas em processos/containers separados.
- Regressões sintéticas atualizaram fixtures para não criar falsa falha por contagem antiga.

### CI e documentação

- CI passa a rodar checagem da configuração principal antes das duas provas Nginx, além de registrar o gate V19.3.
- Regressões novas rejeitam provas sem redaction, com configuração desatualizada ou com parâmetros codificados aceitos.
- Visual do produto foi preservado: interface SaaS profissional sem neon.

## 4. Execuções verificadas nesta rodada

| Comando/escopo | Resultado real | O que NÃO comprova |
|---|---|---|
| `python -m unittest discover -s tests -q` | **240/240 PASS** | Firebase real, build React |
| `python3 -m scripts.record_offline_v16` | PASS, dados e hashes atualizados | Testes HTTP de Flask não executados nesta sessão |
| `python scripts/check_nginx_main_config_v19_3.py` | PASS, Nginx verdadeiro | Docker rodando |
| `python scripts/prove_nginx_native.py` | PASS: 20/20 entre réplicas, 8/8 após falha; URLs perigosas recusadas e 55 linhas JSON conferidas | Aplicação Flask original em produção |
| `NODE_PATH=$(npm root -g) node scripts/test_*session*_v19_2.cjs` (3 comandos concretos do README) | PASS em três provas simuladas | Browser E2E ou build completo |
| Sintaxe TypeScript/TSX (parser) | PASS, 23 arquivos | Typecheck/bundle Vite |
| Teste HTTP original com Firebase simulado | **histórico da V19.1**, não reexecutado aqui | Firebase Auth/RTDB real |
| Firebase Auth/RTDB Emulator (23 casos) | **PENDENTE** | Não atribuir aprovação |
| Docker/Prometheus/Grafana | **PENDENTE** | Não atribuir aprovação |

Não foi possível instalar Flask/Flask-Cors neste ambiente (índice de pacotes indisponível), nem fazer `npm ci` completo. O Docker também não está instalado. Não gerar prints falsos nem reutilizar evidência de outra revisão.

## 5. Progresso e próximos passos

**Implementação estimada: ~69%**, conservada da V19.2 pela inexistência de novo build e testes integrados completos. **Aceite ponderado após regenerar evidências: consultar `evidence/generated/RELEASE_GATE_V19_3.json`**. O modelo é interno, não corresponde aos pesos oficiais do edital nem à chance de passar.

P0 — **Para avançar a nota, não apenas a quantidade de testes:** reexaminar F01/F02 com política de negócio, encontrar achados upstream independentes caso não se sustentem, fechar cinco descobertas reproduzíveis e três correções de causa raiz. Revisar licença/permissão e avisar os responsáveis pelo segredo no snapshot upstream (nunca publicar valores).

P1 — Reexecutar build completo React V19.3 e três testes de sessão; instalar ambiente de emuladores local `demo-coursesphere-vlab` e executar **23 casos**, verificando regras e quotas; executar duas instâncias Flask/Nginx com Firebase simulado para revalidar o gateway; CI deve gerar resultados com hash.

P1 — Executar `docker compose --profile observability up -d --build` e `python3 scripts/verify_docker_stack.py --failover`, comprovando Grafana, Prometheus, Nginx, duas réplicas e reinício. **A infraestrutura Compose é do laboratório sintético**, não da aplicação original inteira: explicitar isso na defesa e, se necessário, criar ambiente do original.

P2 — Revisar documentação e relatórios finais, scorecard de riscos, checklist da banca e licença. Evitar novas features sem ganho claro em qualidade de evidência.

## 6. Comandos para retomada

Na raiz `CourseSphere_V19` extraída do ZIP:

```bash
python3 -m scripts.record_offline_v16
python3 scripts/check_nginx_main_config_v19_3.py
python3 scripts/prove_nginx_native.py
python3 -m scripts.release_gate_v19_3
```

Quando o usuário decidir rodar integrações no Fedora, sem usar projeto Firebase real dos autores:

```bash
bash scripts/verify_frontend_build_v14_2.sh
node scripts/test_session_gate_v19_2.cjs
node scripts/test_user_chats_runtime_v19_2.cjs
node scripts/test_profile_session_runtime_v19_2.cjs
bash scripts/verify_official_emulators.sh
docker compose --profile observability up -d --build
python3 scripts/verify_docker_stack.py --failover
```

O script de emuladores requer Python Flask/Firebase Admin, Node, Java e Firebase CLI; o de Docker requer Docker Engine e Compose. Verificar secrets localmente. Sempre conferir SHA-256 e os relatórios gerados, sem expor credenciais.

## 7. Controle editorial

Este é o handoff atual para as próximas sessões/Work. Leia este documento ANTES dos handoffs históricos. Se a sessão ficar longa, salvar ZIP e esta documentação primeiro. Nenhuma ação remota foi tomada. Nenhuma garantia de aprovação ou 100% foi dada.
