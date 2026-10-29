# HANDOFF MESTRE — COURSESPhERE V19.8

**Base:** CourseSphere V19.7. Esta versão é continuidade incremental, preservando frontend React/TypeScript/Vite original, Flask original corrigido, Firebase Auth/Realtime Database, configurações e scripts anteriores. O laboratório CRUD/SRE sintético continua separado em `compose.yaml`.

## Objetivo do edital e estado

O desafio AppSec/SRE exige: comprovar pelo menos **cinco falhas reais no repositório original em ao menos duas categorias**, corrigir **três causas raízes** e demonstrar antes/depois, acrescentar **dois hardenings**, entregar logs/SLIs/SLOs e uma stack Docker com **dois backends** e Nginx realizando balanceamento/failover, além de relatório reprodutível. CI, scans e dashboards aumentam a qualidade, mas não substituem requisitos centrais.

**V19.8 — implementação estimada: 73%; aceite formal comprovado nesta cópia: 15%.** Ambos são índices INTERNOS, não nota ou probabilidade. A meta de implementação não representa validação. Só os grupos offline e Nginx nativo deram evidência novamente neste ambiente; prova Docker/Flask real/Firebase/React atual precisam ocorrer em máquina apta.

## O que esta rodada modificou — efetivamente implementado

1. `backend/metrics_access.py`: proteção fail-closed para `/metrics`. Padrão desabilitado. Com opt-in, local loopback mantém diagnóstico; acesso de rede exige bearer com segredo >=32 caracteres proveniente de arquivo (não valor em variável de ambiente), comparação em tempo constante. Ignora `X-Forwarded-For`; não registra token. `backend/endpoints.py` integrado a esse controle.
2. `compose.official.observability.yaml`: overlay **opcional** separado da sandbox, com Prometheus, Grafana, dois Flask originais, Docker secret e portas localhost.
3. `ops/prometheus/prometheus.official.yml` + `alerts.official.yml`: scrape individual das réplicas, token de arquivo montado e três alertas. SLIs/SLOs propostos: 99% sem 5xx e p95 ≤0,5 s, ambos em janelas de 5 min. São metas locais didáticas.
4. `ops/grafana/provisioning-official/` e `dashboards-original/`: fontes de dados e seis painéis do **Flask original** (métricas `coursesphere_original_*`), não da sandbox.
5. `scripts/start_official_observability_v19_8.sh`, `official_observability_preflight_v19_8.py`: geram segredos exclusivos locais com permissões 0600 e não sobrescrevem existentes; rejeitam symlinks e valores insuficientes. Estes secretos `.env.*` e `.local` **não entram no pacote**.
6. `scripts/verify_official_observability_v19_8.py`: teste Docker REAL preparado e fail-closed: verifica Grafana API/dashboard, regras Prometheus, duas séries com scrapes autenticados, HTTP em cada réplica, `/metrics` vedado no gateway, detecção de perda e retorno após restart. Salva apenas JSON sanitizado com hashes; sem Docker nesta máquina, **NÃO foi executado**.
7. `integration/test_v19_8_metrics_runtime.py` + `run_v19_8_metrics_runtime.py`: 8 testes de WSGI com Flask real e Firebase simulado; **não executados por falta de Flask**. O runner exit=1 quando testes são pulados, impedindo alegação de validação.
8. `tests/test_v19_8_original_observability.py`: 29 novos testes Python offline incluindo autenticação, segredos inválidos, conf, CI e checagem das regras.
9. `scripts/release_gate_v19_8.py` e `scripts/verify_local_v19_8.sh`: evidências novas por SHA-256, sem acrescentar pontos inventados ao aceite; CI ganhou job original Flask + Prometheus/Grafana e testes HTTP separados.

## O que REALMENTE foi executado e passou

- **337/337 regressões Python offline**, registradas por `scripts.record_offline_v16`.
- **Nginx REAL nativo**: gateway original com upstreams **sintéticos**, respostas roteadas 21/20 incluindo aquecimento, 8/8 após desligar backend, query com marcador não gravado no log. Sandbox separada também passou com failover.
- **Três testes executáveis Node de isolamento de sessões** (sem build completo React): passaram.
- YAML de Compose/Prometheus/alertas/Grafana/workflow: parse sintático com PyYAML. Não substitui `docker compose config` nem `promtool check config`.
- Teste WSGI Flask V19.8: **8 skipped, runner recusou validar e saiu com erro**, comportamento correto neste ambiente sem Flask.
- Prova Docker original/Prometheus/Grafana: **não executada** (Docker indisponível). Build completo npm e Firebase Emulator: **não executados nesta rodada**.
- Índice interno de aceite atual: **15%** (2 dos 8 grupos; sem reciclar evidências antigas de Flask após mudança do código).

## Bloqueios mais relevantes

1. Revisão manual das cinco vulnerabilidades reais originais, pelo menos duas categorias, e demonstrações reproduzíveis de três correções. Os testes do laboratório separado **não contam** como upstream.
2. Reexecutar Flask 15 cenários HTTP com Firebase simulado, 8 novos testes de autenticação das métricas e o teste de réplica Flask real atrás Nginx para hashes atuais.
3. Rodar Firebase Emulator para Auth/Database e suas regras, com 23 cenários planejados; verificar isolamento/cotas. Não usar credenciais dos autores.
4. Rodar frontend React `npm ci && npm run build` na versão atual, testes de navegação real e troca de sessão.
5. Rodar `compose.official.yaml` (Flask original) e o overlay observabilidade V19.8, provar SLI/SLO e failover; também validar o laboratório SRE sintético exigido na banca se aplicável.
6. Rotação/notificação ao dono sobre possível credencial JSON exposta no upstream e confirmação de licença/redistribuição — sem publicar valores, sem afirmar credencial ativa.

## Primeiro procedimento no Fedora ou Work com Docker

```bash
# Antes de rodar testes que geram evidence/generated: conferir MANIFEST_SHA256_V19_8.txt.
bash scripts/verify_local_v19_8.sh

# Com Flask e flask-cors no Python local:
python3 -m integration.run_v19_8_metrics_runtime

# Com Docker, rede para puxar imagens e build npm:
bash scripts/start_official_observability_v19_8.sh
python3 scripts/verify_official_observability_v19_8.py --failover
python3 -m scripts.release_gate_v19_8
```

Ver `docs/OBSERVABILIDADE_ORIGINAL_V19_8.md` para arquitetura, portas, SLOs, riscos e comandos de parada.

**IMPORTANTE:** no Compose oficial sem credenciais Firebase próprias e sem emuladores, apenas a SPA e rotas públicas podem ser validadas. Login, perfil, chat e quotas não são uma experiência ponta a ponta pronta. O frontend de demonstração aponta para emuladores locais que esta stack **não inicia**; não dizer que o Firebase ficou integrado.

## Regra de continuidade / checkpointer

Continuar de V19.8. Testar, corrigir e emitir um novo ZIP e handoff **durante a sessão**, antes do limite de contexto. Gravar `docs/WORK_LATEST.md` ou equivalente após marcos significativos. Não supor que jobs GitHub Actions declarados já rodaram. Nunca falsificar percentuais, screenshots ou execução Docker. Evitar brilho/neon, manter aparência SaaS sóbria e projeto original intacto.
