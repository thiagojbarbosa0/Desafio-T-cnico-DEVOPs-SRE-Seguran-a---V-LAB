# CourseSphere R5 — o que baixar e em que ordem

**Este é o trabalho R5 sobre a V19.9 R4 recuperada; a versão principal V19.15 não está substituída.**

- ZIP completo R5: arquivamento/exame, com frontend React + backend Flask + stack SRE.
- Patch R4->R5: alterações específicas em fontes, testes e CI, validado sobre a R4 original.
- ADDON R5: patch com documentação e testes para avaliar portabilidade à V19.15; **não executar instalação automática**.
- Manifesto externo R5: SHA-256 e metadados dos artefatos.

A mudança importante é o **readiness medido no próprio scrape privado do Prometheus**, evitando alertas silenciosos quando ninguém consulta `/ready`. O monitoramento permanece apenas localhost/Docker privado, sem exigir criação de contas remotas. Ver `docs/READINESS_AUTOMATIZADA_R5.md`.

## Provas permitidas sem Docker

```bash
python3 -m scripts.record_offline_v16
python3 scripts/prove_official_nginx_contract_v19_7.py
python3 scripts/prove_nginx_native.py
python3 -m scripts.release_gate_work_v19_9
```

Nenhum desses testes comprova Firebase Auth/RTDB real. Para a integração V19.15, preserve a versão original, importe as alterações seletivamente e reconstrua e comprove as imagens exatas. Não publique a stack nem insira credenciais reais no pacote.
