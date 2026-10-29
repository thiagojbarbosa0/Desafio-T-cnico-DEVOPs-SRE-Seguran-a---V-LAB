# Changelog V18 — controles de escrita e evidência

## Alterações implementadas

1. `backend/shared_quota.py`: limite transacional de gravação de chat: 60 por minuto por usuário verificado.
2. `backend/endpoints.py`: autenticação → validação → quota compartilhada → escrita. Código 429 ao exceder; 503 quando a quota indisponível (fail-closed).
3. `tests/test_v18_chat_write_quota.py`: 12 novos testes, incluindo 120 chamadas concorrentes e erros controlados.
4. `integration/test_official_emulators.py`: o cenário 20 também cobre bloqueio/liberação da quota de chats com contador do RTDB emulado.
5. `scripts/release_gate_v18.py`, `scripts/doctor_v18.py` e `scripts/verify_v18.sh`: indicadores e relatório separados para V18.
6. GitHub Actions agora executa o verificador V18.

## Limites da evidência

- Testes offline não equivalem à execução de Firebase Emulator.
- Nginx em loopback testa réplicas sintéticas; não é prova de Docker.
- React e Docker/Grafana precisam de execução integrada, sem inventar aprovações.
- Os cinco achados prioritários continuam em `docs/RELATORIO_APPSEC_V18.md`; a quota não é contabilizada como falha encontrada no upstream.
