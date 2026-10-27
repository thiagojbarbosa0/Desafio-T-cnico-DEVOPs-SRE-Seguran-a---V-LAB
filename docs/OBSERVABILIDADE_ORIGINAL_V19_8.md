# CourseSphere original — observabilidade privada (V19.8)

> **Escopo:** a aplicação **Flask original corrigida**, não a sandbox didática. A configuração está implementada, mas **não foi executada com Docker/Prometheus/Grafana neste ambiente**. O job `original-docker-observability-v19-8` no CI pode comprovar o resultado quando for executado no GitHub Actions.

## Arquitetura e isolamento

Navegador → `127.0.0.1:8081` → Nginx `official_gateway` → `official_api_a:8091` / `official_api_b:8091` (Gunicorn Flask original). React original é servido pelo `official_frontend`. A sandbox de CRUD continua em `compose.yaml`, independente.

Somente **dentro da rede privada Docker**, Prometheus consulta `/metrics` diretamente em cada réplica, usando `Authorization: Bearer <segredo_gerado_localmente>`. Nginx continua retornando **403 em `/metrics`**; o Flask retorna **404** para requisições externas sem o token válido. O token nunca é logado, não aparece em código ou ZIP, e é lido de `/run/secrets/official_metrics_token`. A checagem ignora `X-Forwarded-For`.

O dashboard Grafana oficial acessa `official_prometheus:9090`; portas locais: Nginx `8081`, Prometheus `9092`, Grafana `3001`. O fluxo não depende das métricas da sandbox.

**Atenção sobre Firebase:** a stack oficial base sobe com a configuração frontend de emuladores, mas **não inicia Firebase Auth/RTDB Emulator**, nem injeta credenciais de terceiros. Assim, o smoke test do React e das rotas públicas é válido, mas login, perfil e chat não ficam operacionais sem configuração autorizada adicional. **Não confundir com uma demonstração ponta a ponta autenticada.** Nunca expor os emuladores à Internet.

## Como executar no Fedora (Docker + internet para obter imagens e npm)

```bash
# Primeiro, conferir a integridade do ZIP antes de executar testes que alterem evidence/generated.
# Rodar na raiz da extração.
bash scripts/verify_local_v19_8.sh

# Gera secrets locais com modo 0600, valida e sobe Flask original,
# duas réplicas, React, Nginx, Prometheus e Grafana:
bash scripts/start_official_observability_v19_8.sh

# Quando os healthchecks e scrapes estiverem disponíveis:
python3 scripts/verify_official_observability_v19_8.py --failover
python3 -m scripts.release_gate_v19_8

# Abrir no navegador (máquina local):
# http://127.0.0.1:8081 (SPA original, auth não configurada)
# http://127.0.0.1:9092 (Prometheus)
# http://127.0.0.1:3001 (Grafana)

# Encerrar e eliminar volumes de laboratório:
docker compose --env-file .env.official.observability \
  -f compose.official.yaml -f compose.official.observability.yaml \
  --profile observability down -v --remove-orphans
```

O login inicial do Grafana usa `admin` e a senha privada criada em `.env.official.observability`. Não publique o arquivo nem cole a senha em logs. A execução pode falhar se imagens não puderem ser baixadas, portas estiverem ocupadas ou dependências React não compilarem: registre isso como bloqueio, **nunca como validação positiva**.

## SLIs e SLOs locais propostos

| SLI (medido em todas as réplicas) | Consulta e observação | SLO proposto |
| --- | --- | --- |
| Disponibilidade por respostas HTTP | 1 − taxa(5xx) ÷ taxa(requisições de negócio) em janela de 5 minutos; rota `/health` excluída | **≥99%** dos requests sem 5xx em janela válida; alertar 5 minutos depois de ultrapassar 1% de 5xx |
| Latência HTTP p95 | `histogram_quantile(0.95, sum by (le)(rate(coursesphere_original_http_duration_seconds_bucket[5m])))` | **p95 ≤0,5 s**, alertar após 5 min consecutivos |

São metas **didáticas/operacionais propostas**, não indicadores coletados de produção ou garantias de desempenho. Em tráfego muito baixo, as janelas de taxa podem produzir vazio; `/health` não entra no SLO de negócio; a disponibilidade de cada instância é monitorada adicionalmente via `up{job="coursesphere-original"}`.

Métricas sem labels de IP, UID, token ou query: `coursesphere_original_http_requests_total`, `coursesphere_original_http_duration_seconds_bucket`, `coursesphere_original_auth_attempts_total`. NGINX não registra query string e seu `/metrics` público continua bloqueado.

## O que o teste automatizado exige antes de aprovar

1. Compose config válido, Grafana real respondendo e o dashboard `coursesphere-original-v19-8` acessível via API.
2. Prometheus com regras carregadas: `OriginalAPIAvailabilitySLO`, `OriginalAPILatencySLO` e `OriginalAPIReplicaUnavailable`.
3. **Duas séries `up=1` independentes**, uma para `official_api_a:8091` e outra `official_api_b:8091`.
4. Requisições HTTP do Flask original capturadas por Prometheus nas **duas réplicas**.
5. Nginx bloqueando `/metrics` para navegadores, sem revelar dados de telemetria.
6. Parada de uma réplica: Prometheus observa `up=0` naquela e `up=1` na outra; Nginx responde 8/8; após `compose start`, `up=1` retorna nas duas.
7. Relatório JSON em `evidence/runtime/OFFICIAL_OBSERVABILITY_V19_8.json` marcado `validated=true` **somente se todos os passos passarem**, e com SHA-256 das fontes relevantes.

A prova Flask WSGI com 8 cenários (`python3 -m integration.run_v19_8_metrics_runtime`) é separada: usa **Flask real + Firebase simulado**. Neste ambiente não havia Flask e ela foi corretamente registrada como não validada. As 25 regressões offline testam a lógica da proteção e os contratos, **não a implementação Docker**.

## Prioridades para a submissão

O monitoramento original agora está implementado como uma opção; **não** reduz a prioridade das cinco vulnerabilidades do código upstream (duas ou mais categorias), três correções com antes/depois, controles de hardening, validação Firebase Auth/RTDB e execução Docker. Credenciais de autores, revisão da licença e a definição precisa de achados ainda requerem cuidado e revisão humana.
