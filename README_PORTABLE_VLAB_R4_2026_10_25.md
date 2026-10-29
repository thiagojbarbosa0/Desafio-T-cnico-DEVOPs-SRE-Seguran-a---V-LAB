# CourseSphere R4 — engenharia executada em 25/10/2026

**Base recuperada:** `CourseSphere_V19_9_R3_CODIGO_COMPLETO.zip`; R4 é uma derivação auditável da V19.9, **não** a V19.15 principal. A arquitetura original React/TypeScript/Vite + Flask + Firebase Auth/RTDB e laboratório sintético separado foram preservados.

## Mudanças efetivas

1. **Readiness distinta de liveness:** `/health` continua 200 se o processo responde; `/ready` executa leituras mínimas e privilegiadas de Firebase Auth (`list_users(max_results=1)`) e RTDB (`server_security/readiness`), sem fazer download da raiz do banco. Se não puder acessar ambos, devolve 503 com JSON genérico sem detalhes internos. Cache sincronizado de 5 s reduz sondagens repetidas. Uma falha do cache ou relógio inválido não gera um falso 200.
2. **Roteamento real:** Nginx envia `/ready` ao Flask e continua negando `/metrics` na borda, impedindo tokens na query string. O verificador Nginx original também comprova que `/ready` foi encaminhado às instâncias sintéticas.
3. **SLIs não inflados por sondagens:** disponibilidade e latência de cliente no Prometheus/Grafana agora excluem `/health` e `/ready`. Novo alerta `OriginalAPIDependencyReadinessDegraded` e painel específico capturam falhas observadas da dependência. **Importante:** o alerta depende de requisições periódicas a `/ready`; scrape de `/metrics` por si só não executa o probe.
4. **Prova HTTP Flask no CI:** novo runner `integration.run_readiness_http_r4` verifica status 200/503, cabeçalhos sem cache, não vazamento de erros, independência do liveness, cache e rejeição de token via URL. O runner reprova quando Flask não está disponível ou há testes ignorados, não gera falso sucesso.
5. **Sondagem operacional local sem credenciais:** `scripts/probe_official_local_runtime_r4.py` verifica os contratos `/health`, `/ready`, `/metrics` e query com token sintético em `127.0.0.1:8081`; não executa ações mutáveis, não aceita URLs de terceiros, não concede pontos do gate.
6. **Release report conservador:** `scripts/release_gate_work_v19_9.py` não descreve prova Firebase histórica como atual se os gates com hashes atuais não aprovam. Gera arquivo derivado próprio, sem sobrescrever o gate V19.15.
7. **Cobertura:** 28 novos casos offline; regressão 478/478, testes Node e Nginx reais (upstreams sintéticos) executados. Sem confirmação local do HTTP Flask por ausência de dependências; sem Docker/Firebase Emulator integrado nesta sessão.

## Execução local segura

```bash
# Uma vez extraída a pasta da R4:
python3 -m scripts.record_offline_v16
node scripts/test_session_gate_v19_2.cjs
node scripts/test_user_chats_runtime_v19_2.cjs
node scripts/test_profile_session_runtime_v19_2.cjs
python3 scripts/prove_official_nginx_contract_v19_7.py
python3 -m scripts.release_gate_work_v19_9

# Somente quando a stack ORIGINAL com Firebase Emulator LOCAL já estiver rodando:
python3 scripts/probe_official_local_runtime_r4.py --require-ready

# Com Flask/Flask-Cors instalados, sem Firebase externo (serviços simulados):
python3 -m integration.run_readiness_http_r4
```

**Limite fundamental:** nem R4 nem seu addon devem ser anunciados como versão V19.15. Não copiar `backend/firebase.py`, `backend/endpoints.py`, `compose.official.yaml` ou `gateway.official.conf` indiscriminadamente da R4 para a V19.15. Conferir diffs e manter suporte DNS Docker Firebase/atestação da V19.14/V19.15. A soma das evidências é determinada pelo **código exato** e pelo **runtime exato**, não pelo nome do ZIP.

## O que ainda está pendente

- Reexecutar o teste real Firebase Auth/RTDB, quota HTTP 20/21, isolamento de usuários, atestação de imagens, dois Flask reais, failover, Prometheus/Grafana e release gate sobre a fonte exata da V19.15.
- Revisar manualmente as cinco vulnerabilidades upstream e três correções (matriz em `docs/MATRIZ_5_ACHADOS_R4.md`). Não afirmar validade de credenciais upstream nem demonstrar DoS sem provas.
- Confirmar direitos de redistribuição, revogação de eventuais segredos históricos e revisão de histórico Git com o proprietário.
- Examinar as dependências npm vulneráveis por severidade e exposição de produção: sem `npm audit fix --force` ou atualização cega.
