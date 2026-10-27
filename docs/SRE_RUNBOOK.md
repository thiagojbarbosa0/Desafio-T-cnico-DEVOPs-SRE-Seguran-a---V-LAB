# SRE — Playbook de confiabilidade local

## Visão de saúde

- Liveness: `GET /api/health` devolve JSON com `status` e `instance` no laboratório.
- Readiness: `GET /api/ready` executa `SELECT 1` no SQLite compartilhado; sem banco, retorna 500 e a réplica deve ser retirada do serviço após healthcheck.
- Métricas: `GET /metrics` diretamente em cada réplica (`api_a:8091`, `api_b:8091`), não publicado pelo gateway.
- Logs: JSON por request com `time`, `request_id`, `route` normalizada, método, classe de status, duração e instância, sem IP, queries, token ou body.

## SLI e SLOs (apenas PROPOSTOS)

| Indicador | Definição | SLO alvo | Janela |
|---|---|---|---|
| Disponibilidade | proporção de requests da API sem 5xx | ≥99,5% | 30 dias |
| Latência | p95 de `http_duration_seconds` | <300ms | 5min |

PromQL sugerido (a segunda expressão exige tráfego suficiente e serve como sintoma operacional, não como prova de satisfação por 30 dias):

```promql
1 - (sum(rate(coursesphere_http_requests_total{status_class="5xx"}[5m])) / clamp_min(sum(rate(coursesphere_http_requests_total[5m])), 0.001))
histogram_quantile(0.95, sum by (le) (rate(coursesphere_http_duration_seconds_bucket[5m])))
sum by (instance) (rate(coursesphere_http_requests_total[1m]))
sum(up{job="coursesphere-demo"})
```

### Cenário operacional controlado — falha de réplica

1. `bash scripts/start_docker.sh`; aguarde readiness de api_a e api_b.
2. Execute `python3 scripts/collect_evidence.py`; verifique os dois IDs únicos.
3. `docker compose stop api_a`; repita requests ao gateway.
4. Verifique se gateway ainda responde `200`, se existem 502 iniciais durante atualização de estado e se Grafana reflete `up=0`. **Não presumir zero downtime.**
5. `docker compose start api_a`; repita a observação, registre cronologia e a causa de eventuais falhas.
6. Ao encerrar `bash scripts/stop_docker.sh`; não use `down -v` sem querer apagar dados locais.

### Resposta a incidente

- **API 5xx alta:** verificar `docker compose ps`, logs de `api_a/api_b` sem imprimir segredos, sqlite volume, limite de memória, healthchecks. Reverter última alteração responsável se correlacionada.
- **Lentidão:** observar p95, série de requests por instância, concorrência SQLite e contenção de escrita; limitar experimento e reduzir carga, sem alterar infraestrutura no escuro.
- **Incidente de credenciais:** se `.env` ou service-account vazarem, revogar chaves imediatamente no fornecedor legítimo, rotacionar segredos, invalidar sessões e inspecionar histórico Git. Não compartilhar `.env` nem tokens em prints.
- **Uso indevido da sandbox fora do localhost:** suspender gateway, rever binds, portas, firewall, volumes; não usar endpoint `/api/demo/session` publicamente.

### Limitações técnicas

SQLite WAL em volume local não é armazenamento confiável multi-host; demo é intencionalmente mono-host. Rate limiter keyed pela origem TCP dos containers; se atrás de proxy, a origem observada pode ser o gateway, o que é *conservador* contra spoofing de header mas limita granularidade. Não usar esses números para avaliar experiência real de usuários.

## SLIs do fluxo de negócio (V7; metas, NÃO resultados)

| SLI | Query | SLO proposto | Janela |
|---|---|---|---|
| p95 de emissão de sessão de demonstração | `histogram_quantile(0.95, sum by(le)(rate(coursesphere_http_duration_seconds_bucket{route="/api/demo/session"}[5m])))` | p95 < 300ms | 30 dias, com janelas de 5min |
| Taxa de disponibilidade do CRUD de cursos (sem 5xx) | `1 - sum(rate(coursesphere_http_requests_total{route=~"/api/courses.*",status_class="5xx"}[5m])) / clamp_min(sum(rate(coursesphere_http_requests_total{route=~"/api/courses.*"}[5m])),0.001)` | >= 99% | 30 dias |

**Nota:** os contadores são apenas do laboratório sintético. Excluem 4xx da taxa de indisponibilidade porque 403 de autorização é comportamento correto. Para um SLO de produto real seria necessário definir eventos esperados, tráfego mínimo, jornada de autenticação Firebase real, armazenamento durável e histórico de 30 dias.

### Experimento sem Docker

`python3 scripts/prove_resilience_local.py` inicia duas instâncias HTTP locais, valida token compartilhado e interrompe uma delas. O resultado em `evidence/generated/LOCAL_REPLICA_FAILURE.json` comprova sobrevivência da réplica B, **não** failover automático do Nginx, que permanece pendente no Fedora.
