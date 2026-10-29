# COURSESPHERE V19.7 — HANDOFF OPERACIONAL (24/10/2026)

## 1. O QUE O DESAFIO REALMENTE PEDE

O V-Lab quer análise técnica do **CourseSphere original**, com pelo menos 5 vulnerabilidades efetivas em 2+ categorias, 3 correções da causa raiz comprovadas, 2 medidas de hardening, logs/métricas + 2 SLIs/SLOs, Docker com pelo menos 2 backends e Nginx, relatório de pentest/SRE e reprodução clara. Diferenciais são opcionais; os requisitos de segurança e evidência têm prioridade alta. A stack upstream é Flask, React/TS, Firebase Auth/RTDB e SQLite; o CRUD didático é laboratório separado, não deve ser apresentado como funcionalidade nativa do upstream.

## 2. LINHA DE CONTINUIDADE

Base: V19.6, NÃO V19 antiga. Foram preservados os controles de token em Authorization, validações de payload, respostas de erros genéricos e 413, política de CORS estrita, rate limiting compartilhado por Firebase, isolamento de sessão React, proteção contra escrita direta RTDB, anonimização dos logs, infraestrutura do laboratório e o histórico de provas. Não restaurar arquivos secretos do ZIP original nem usar credenciais dos autores. Visual profissional discreto: sem neon.

## 3. PRINCIPAL AVANÇO DA V19.7

A infraestrutura anterior demonstrava duas réplicas do **laboratório Python sintético**, não duas réplicas da aplicação upstream. Esta versão adiciona uma implantação OPCIONAL e SEPARADA para o CourseSphere original:

- `compose.official.yaml`: `official_api_a`, `official_api_b`, `official_frontend` e `official_gateway` em rede privada; porta pública **apenas 127.0.0.1:8081**.
- `backend/Dockerfile.official`: original Flask sob Gunicorn, não `backend.local_server`, execução sem root e healthcheck.
- `frontend/Dockerfile.official` e `ops/nginx/frontend.official.conf`: React Vite, SPA fallback e servidor interno não privilegiado.
- `ops/nginx/gateway.official.conf`: roteamento real de `/users`, `/chats`, `/hash`, `/health` e SPA, rate limits de corpo e timeouts, `/metrics` bloqueado ao público e negação de query strings em rotas de API.
- `.dockerignore`: impede que `.env`, credenciais, segredos, caches e dependências locais entrem no contexto do Docker. Dataset pesado é preservado no repositório, mas não enviado à imagem.
- `scripts/prove_official_nginx_contract_v19_7.py`: usa **Nginx real**, com upstreams HTTP stdlib sintéticos, para exercitar **a configuração da stack original**, sem afirmar que executou Flask, React ou Docker.
- `scripts/verify_official_docker_v19_7.py`: runner para execução Docker real, distribuição entre réplicas, status anônimo 401, SPA, bloqueio de métricas e de token em URL, recuperação da instância. Falha com exit!=0 se não comprovado.
- `tests/test_v19_7_official_stack.py`, `tests/test_v19_7_release_gate.py`: regressões de arquitetura e recusa de evidências forjadas/incompletas.
- CI: jobs separados para Nginx nativo e stack Docker original, sem confundir com o laboratório.

## 4. RESULTADOS HONESTOS DA RODADA

- Testes offline, Nginx nativo e testes Node: consultar `evidence/generated/TESTES_OFFLINE_V13.json`, `evidence/generated/NGINX_OFFICIAL_ROUTING_V19_7.json`, `evidence/generated/NGINX_LIVE_V9.json` e os logs de validação.
- Teste Nginx original-stack: usa **Nginx real + upstreams sintéticos**. Não prova Flask original em contêiner, build React nem Firebase real.
- Compose original: arquivos de infraestrutura implementados; **Docker e imagens não executados aqui**, pois Docker não está instalado. O Docker test ficará pendente até CI/Fedora.
- Flask real, Flask-Cors e Firebase Emulator: não executados nesta rodada; pip indisponível no host; testes anteriores com Firebase simulado são históricos e não devem ser promovidos como atuais sem seus hashes.
- Build React atual: não executado aqui, falta cache npm completo.
- **Controles de aceitação ponderada são internos, não nota do V-Lab.** Cada alteração pode invalidar evidências antigas; não congelar 15% como verdade imutável.

## 5. RISCOS FUNDAMENTAIS AINDA ABERTOS

1. Os cinco achados candidatos do upstream F01–F06 precisam ser apresentados com metodologia e impacto estritos: F01 cadastro público e F02 recomendação anônima dependem da política funcional; F04 prova presença de arquivo com material de credenciais, NÃO atividade do segredo. Confirmar 5 achados reais e 3 correções de causa raiz sem inflar quantidade.
2. React com Firebase Emulator (Auth/RTDB), políticas, quotas transacionais e isolamentos de sessão ainda precisa de execução ponta a ponta.
3. Docker stack original ainda não foi iniciada neste host; faltam provas de imagens/healthchecks/restart e Build React. `/health` é liveness, **não** atesta acesso ao Firebase. O default não sobe emuladores; operações autenticadas não ficam funcionais sem ambiente de teste apropriado.
4. A telemetria do Flask original ainda não está conectada ao Prometheus/Grafana do Compose didático; não declarar que dashboard original funciona sem integrar scrape seguro entre contêineres.
5. Licença/autorização de redistribuição e rotação do material exposto do upstream são assuntos do proprietário. Sem permissão, não publicar código derivado como se fosse licença aberta.

## 6. COMO RETOMAR

Dentro do diretório raiz do ZIP:

```bash
bash scripts/verify_local_v19_7.sh
```

Para executar o Docker **original** no Fedora ou GitHub Actions (requer Docker + rede para imagens):

```bash
docker compose -f compose.official.yaml config --quiet
docker compose -f compose.official.yaml up -d --build
python3 scripts/verify_official_docker_v19_7.py --failover
docker compose -f compose.official.yaml down --remove-orphans
```

Para Firebase Emulator:

```bash
bash scripts/verify_official_emulators.sh
```

Não confiar em resultados de teste antigos com hash diferente. Atualizar a matriz dos achados e evidências antes de apresentação à banca.

## 7. PRÓXIMA DIREÇÃO RECOMENDADA

Prioridade: integração Auth/RTDB Emulator e builds React/Flask em contêiner, depois link de telemetria segura ao Grafana original. Em paralelo, resolver dúvidas de política dos achados F01/F02, e mapear 5 achados comprovados e 3 correções reproduzíveis, com severidade justificada. Só depois investir em Kubernetes ou IA.
