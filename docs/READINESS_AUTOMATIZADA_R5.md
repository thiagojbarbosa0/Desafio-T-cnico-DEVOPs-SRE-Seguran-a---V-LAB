# CourseSphere R5 — readiness observável por scrape privado

## Problema demonstrado na revisão da R4

A R4 possuía `/ready` (Flask Auth + RTDB) e uma regra `OriginalAPIDependencyReadinessDegraded` que lia contadores de requisições para `/ready`. Porém, Prometheus coletava **somente `/metrics`**. A ausência de sondagens externas em `/ready` tornava esse alerta dependente de uma atividade que não estava provisionada. Um Firebase indisponível poderia não disparar o alerta, apesar de `up==1` e do processo Flask estar funcionando.

## Alterações R5

1. `/metrics` permanece privado e **autoriza a chamada antes de consultar Firebase**. A coleta autorizada usa o mesmo cache de 5 s de `/ready`, sondando Firebase Auth e RTDB sem ler a raiz do banco.
2. `HTTPMetrics.set_firebase_readiness` aceita apenas booleanos, mantém estado separado sob lock e publica gauge sem labels: `coursesphere_original_firebase_ready 1` quando pronto e `0` quando indisponível. Um erro de dependência não causa HTTP 500 no endpoint de métricas; é apresentado como 0. Um processo ainda não consultado omite a amostra.
3. O Prometheus coleta **as duas réplicas diretamente** a cada 10 s, com token bearer armazenado em arquivo privado. A Nginx pública bloqueia `/metrics`.
4. Alerta `OriginalAPIDependencyReadinessDegraded` dispara sobre a amostra de uma réplica com valor zero, e `OriginalAPIReadinessTelemetryMissing` detecta réplicas `up==1` que não expõem essa amostra (imagem antiga/contrato quebrado).
5. Grafana recebe painel de gauge por `instance`. SLIs de tráfego do usuário continuam excluindo `/health` e `/ready`.
6. `verify_official_observability_v19_8.py` comprova a coleta por instância, registra estados separados, oferece `--require-ready` para ambientes com emuladores corretamente configurados e falha se a métrica não estiver presente. O gate de observabilidade exige a nova prova e os hashes das fontes da versão.

## Limites e segurança

- **Implementação nova validada por testes offline de lógica original de `prometheus_metrics` e `HTTPMetrics`**. As sondagens HTTP Flask reais dependem de Flask/Flask-Cors; 9 testes estão configurados no CI e não puderam rodar neste container.
- Ausência de Docker nesta sessão impede validar scrapes reais com Prometheus/Grafana, Firebase Auth Emulator ou RTDB. Não atribuir pontos de aceite à R5 por esses cenários.
- A verificação privada adiciona uma operação Auth+RTDB a cada coleta, normalmente no máximo uma por 5 s por processo; monitorar latência e custo antes de uso em ambiente autorizado. Falhas transitórias podem ser refletidas com atraso de até 5 s por cache.
- `--require-ready` é adequado **somente** quando Firebase Auth/RTDB foram provisionados; para a stack de demonstração sem Firebase, a observabilidade pode estar operacional, mas `application_ready_for_authenticated_traffic` será `false`.
- O R5 não equivale a uma prova de quotas distribuídas reais, nem atesta hashes de imagens Docker em execução.
- Esta implementação é derivada de V19.9 R4. O código-fonte oficial **V19.15** permanece a referência a integrar, preservando seus novos testes, attestation de container e adaptadores Firebase.

## Testes e execução

```bash
python3 -m unittest tests.test_readiness_scrape_r5 tests.test_readiness_slo_r4 -v
python3 -m scripts.record_offline_v16
python3 scripts/prove_official_nginx_contract_v19_7.py
python3 -m scripts.release_gate_work_v19_9
```

No CI, com Flask instalado, `python3 -m integration.run_readiness_http_r4` roda **9 casos** e falha com código 1 se qualquer um for ignorado. Em host autorizado, com o Compose já ativo, `python3 scripts/verify_official_observability_v19_8.py --failover --require-ready` exige que **ambas** as réplicas estejam aptas; não usar para auto-publicação.
