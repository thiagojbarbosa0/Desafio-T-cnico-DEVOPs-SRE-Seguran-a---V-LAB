# SLIs/SLOs — API Flask original (V13)

## Escopo

A instrumentação **nova no Flask original** está em `backend/observability.py`, integrada em `backend/endpoints.py`. Os exemplos de PromQL a seguir são **propostas**, não medições de produção. A configuração Prometheus padrão do Compose continua coletando a *sandbox* `api_a`/`api_b`; **ela não coleta automaticamente este Flask**. Uma instância Flask original pode expor métricas **somente em loopback e por ativação explícita**, com `COURSESPHERE_METRICS_ENABLED=1`.

## SLI 1 — Disponibilidade da consulta autenticada

**Definição:** proporção de requisições para `POST /users/query` que não respondem HTTP 5xx. SLO proposto: **99,5%** de respostas sem 5xx ao longo de 30 dias. Respostas 4xx por validação/autorização não são falhas de servidor, mas precisam ser monitoradas separadamente.

```promql
1 - (
  sum(rate(coursesphere_original_http_requests_total{route="/users/query",method="POST",status_class="5xx"}[30m]))
  /
  clamp_min(sum(rate(coursesphere_original_http_requests_total{route="/users/query",method="POST"}[30m])), 0.00001)
)
```

**Limitação:** consultar uma única instância não representa o serviço todo. Em múltiplas réplicas, faça scrape de cada uma. Baixo volume requer janelas maiores e alertas com condição mínima de tráfego.

## SLI 2 — Latência da consulta autenticada

**Definição:** percentil p95 do tempo de resposta de `POST /users/query`. SLO proposto: **p95 abaixo de 400 ms** em janelas de 30 minutos durante pelo menos 99% do período mensal, após validar viabilidade com tráfego representativo.

```promql
histogram_quantile(0.95,
  sum by (le) (rate(coursesphere_original_http_duration_seconds_bucket{route="/users/query",method="POST"}[30m]))
)
```

**Aviso:** o mecanismo upstream de recomendação devolve resposta simulada, não um modelo real. Portanto, sua latência medida agora **não equivale à latência de uma recomendação de IA real**.

## Privacidade e segurança

- Sem labels para UID, chat_id, tokens, mensagens, URLs ou parâmetros.
- As rotas são modelos do Flask (`/chats/<chat_id>`), não instâncias com identificadores.
- `/metrics` retorna 404 por padrão; com opt-in explícito, responde apenas a conexões cujo IP de origem é loopback. Não publicar porta do Flask sem controles adicionais.
- Métricas são por **processo**, com memória volátil; para múltiplos workers ou réplicas, coletar todos os processos (ou usar uma solução multi-processo).
- O endpoint `/health` significa apenas *liveness HTTP*, não verifica Firebase disponível. Não declarar readiness de dependências não testadas.
