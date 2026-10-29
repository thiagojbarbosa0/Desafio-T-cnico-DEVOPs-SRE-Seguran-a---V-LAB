# CourseSphere V-Lab R7 — continuação da V19.9 recuperada

Esta R7 evolui a base R6 com endurecimento da **API sintética** de demonstração, em paralelo à linha principal **V19.15**. NÃO substitua o código mais recente da V19.15 com este ZIP.

## Alterações

- Tokens locais HMAC: limite de tamanho, JSON canônico, detecção de claims duplicados, expiração limitada a um dia, nonce no formato esperado.
- JSON de entrada do servidor sintético: campos duplicados e NaN/Infinity rejeitados; controles de Unicode inválido em campos textuais.
- HTTP sintético: rejeição de Transfer-Encoding/chunked, Content-Length múltiplo ou ambíguo, alvo de requisição absoluto. Exceções internas não têm stack trace potencialmente sensível em logs.
- Quota SQLite sintética: transação `BEGIN IMMEDIATE` entre instâncias; apenas grava contagem para tentativas aceitas; corrupção e relógio regressivo bloqueados.
- Prova HTTP real com dois processos de servidor Python (duas instâncias, mesma base SQLite): 30 autenticações aceitas, 11 negadas, token entre réplicas, isolamento de propriedade e contador imutável após 429.
- GitHub Actions testa contratos adicionais e preserva JSON da prova sem tokens.

## Reproduzir sem Docker ou Firebase

```bash
bash scripts/verify.sh
python3 -m scripts.prove_r7_dual_replica_auth
python3 -m scripts.record_offline_v16
python3 -m scripts.release_gate_work_v19_9
```

**Escopo**: R7 demonstra segurança no servidor de laboratório Python + SQLite, não Firebase Authentication/RTDB nem o Flask original da V19.15. Docker, integração Firebase, imagens de produção e cinco achados do upstream continuam pendentes. Não usar contas ou segredos reais.
