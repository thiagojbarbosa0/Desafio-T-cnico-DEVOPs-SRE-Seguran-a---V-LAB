# SRE — SLIs/SLOs, segurança de observabilidade e riscos (V19.4)

## Serviço e escopo

A aplicação original Flask usa Firebase Auth/Realtime Database; o Compose entregue ainda monitora o **laboratório sintético**. Os números obtidos pelo Nginx loopback **não podem ser extrapolados** para SLO de produção.

### Instrumentação no Flask original

- Requisições: `coursesphere_original_http_requests_total{route,method,status_class}`.
- Latência: `coursesphere_original_http_duration_seconds_bucket`, `_sum`, `_count`.
- Autenticação: `coursesphere_original_auth_attempts_total{result,route}` (V19.4).
- Logs JSON com evento HTTP ou autenticação, método, rota normalizada, código/classe, tempo e ID de requisição. **Não registrar** UID, Bearer, parâmetros de URL, corpo das mensagens, e-mail ou IP em logs de autenticação.
- `/health`: liveness do processo, **não** garantia de funcionamento do Firebase.
- `/metrics`: apenas com `COURSESPHERE_METRICS_ENABLED=1` e `REMOTE_ADDR` loopback; não habilitar scraping externo sem redefinir autenticação/rede. Cada processo tem métricas próprias.

## SLIs e SLOs propostos (não atingidos nem avaliados ainda)

**SLI 1 — sucesso das consultas de recomendação:** fração das requisições `POST /users/query` sem erro HTTP 5xx, janela deslizante de 30 dias. **SLO proposto: ≥99,5%**. Códigos 400, 401 e 429 indicam erro/limite de cliente e devem ser analisados separadamente. HTTP 503 por armazenamento de quotas fora do ar deve contar como indisponibilidade.

PromQL (após configurar scraping apropriado de todas as réplicas Flask):

```promql
1 - sum(rate(coursesphere_original_http_requests_total{route="/users/query",status_class="5xx"}[5m]))
  / clamp_min(sum(rate(coursesphere_original_http_requests_total{route="/users/query"}[5m])), 0.001)
```

**SLI 2 — latência p95 da consulta:** histograma agregado de `POST /users/query` para requisições respondidas, janelas de 5 minutos. **SLO proposto: p95 < 500 ms em ≥99% das janelas de 5 min ao longo de 30 dias**. É um objetivo inicial a calibrar com dados reais de hardware/carga.

```promql
histogram_quantile(0.95, sum by (le) (
  rate(coursesphere_original_http_duration_seconds_bucket{route="/users/query",method="POST"}[5m])
))
```

**Sinal de segurança adicional:** aumento de `rate(coursesphere_original_auth_attempts_total{result="denied"}[5m])` pode indicar ataques, erros de sessão ou clientes incompatíveis; **não é** SLO de disponibilidade. Criar alerta com threshold após estabelecer baseline local, evitando alertas sem calibração.

## Riscos conhecidos / próxima arquitetura

1. **Firebase RTDB indisponível:** falha de gravação e quota retorna 503; instrumentar readiness dependente do backend em um ambiente seguro e monitorar quedas. `/health` atual não cobre dependências.
2. **Quotas distribuídas:** dependem de transações RTDB válidas. Os testes unitários da V19.4 provaram lógica concorrente em memória; a nova cobertura adicionada ao teste 20 do Firebase Emulator **ainda não foi executada**.
3. **Múltiplos processos:** contadores de latência HTTP são por processo; Prometheus precisa coletar cada réplica individualmente. O endpoint `/metrics` do Flask original é restrito a loopback; planejar um sidecar autenticado ou scraping por rede privada e não simplesmente liberá-lo publicamente.
4. **Limitações do Compose atual:** Nginx, Grafana e Prometheus operam sobre o laboratório de cursos/aulas independente, não sobre o Firebase/Flask original. Não declarar observabilidade da aplicação original como demonstrada pela stack sintética.
5. **Teste de failover:** a prova Nginx executada nesta sessão usa réplicas Python locais do laboratório; a prova com Flask verdadeiro continua condicionada a Flask instalado e Firebase simulado, seguida de integração com Firebase Emulator.
6. **Capacidade e custos:** antes de escolher limites definitivos de 20 alterações de perfil/min e 30 exclusões/min, testar carga e verificar transações sob erro/retry para evitar bloqueio indevido de tráfego legítimo.

## Dashboard recomendado

Grafana pode exibir a taxa de erros da rota de recomendação, p95 de latência, disponibilidade das réplicas, contagem de autenticações aceitas/negadas e falhas de quotas. **Não existe captura executada desse dashboard para o Flask original na V19.4.** Registrar prints somente de instâncias realmente operantes, com origem e data.
