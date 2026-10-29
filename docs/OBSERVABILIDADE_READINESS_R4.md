# Observabilidade R4 — saúde do processo ≠ disponibilidade das dependências

- `GET /health`: liveness: retorna 200 enquanto o processo Flask opera, mesmo com Auth/RTDB indisponíveis. Não revela identidade.
- `GET /ready`: readiness **por réplica**: retorna 200 somente quando o SDK Firebase Admin alcança Auth e RTDB; se a dependência falha, retorna 503 e um JSON genérico. Cache por worker de 5 segundos; o marcador `server_security/readiness` precisa apenas ser legível via Admin.
- `GET /metrics`: separado, acesso interno autorizado; gateway público devolve 403.
- O healthcheck Docker permanece em `/health` por compatibilidade com `compose.official.yaml`, que pode subir sem Firebase configurado. Não alterar para `/ready` sem ajustar o fluxo de inicialização da imagem.

## Dois SLIs distintos

1. **Disponibilidade funcional de rotas do usuário:** erro 5xx / requisições, EXCLUINDO `/health` e `/ready`; objetivo configurado 99% por janela adequada (não validado operacionalmente na R4).
2. **Latência p95 funcional:** histograma do Flask das rotas reais, EXCLUINDO `/health` e `/ready`; objetivo configurado 500 ms.

O novo `OriginalAPIDependencyReadinessDegraded` observa HTTP 5xx na rota `/ready` por Prometheus. Este alerta **não substitui sondagem ativa** de readiness: scrape de `/metrics` não toca Firebase. O painel “Dependency readiness failures (5m)” dá visibilidade separada aos operadores. Se o gateway fizer fallback de uma réplica ruim para outra boa, `/ready` no gateway pode mascarar degradação parcial; para atestar todas as réplicas, testar cada container separadamente.

O arquivo `evidence/runtime/OFFICIAL_LOCAL_PROBE_R4.json` é **diagnóstico, nunca aceite**. Ele não comprova hash do container, identidade do executor, 20/21, isolamento RTDB ou observabilidade integrada.
