# Mudanças específicas da V9 para V10

1. `frontend/src/components/ChatInterface/ChatInterface.tsx`: fluxo de chat refeito com formulário padrão, IDs de mensagens síncronos e únicos, texto tipado, persistência imediata e erro de gravação visível. Sem neon, sem caixa de terminal fictícia.
2. `frontend/src/interfaces.d.ts`: mensagem `messageID: string`, `content: string`, alinhada com `validate_messages`.
3. `frontend/src/api.ts`: escrita de chats usando autenticação vigente, validação de ID e verificação de HTTP; removidos métodos de edição/remoção de mensagens que não tinham rota no servidor; login não revela mensagens internas do Firebase ao usuário.
4. `backend/firebase.py`: gravação atômica/idempotente por `messageID`; ambiente emulador com URL de namespace RTDB correta.
5. `backend/endpoints.py`: requests registrados como JSON sem URL de query string; headers de hardening complementares.
6. `frontend/src/firebaseConfig.ts` e `integration/test_official_emulators.py`: namespace `demo-coursesphere-vlab-default-rtdb` consistente; testes novos de retry e dados inválidos.
7. `integration/run_official_emulator_tests.py`: runner que escreve `validated` somente se a suíte HTTP real passar.
8. `scripts/prove_nginx_native.py`: prova local agora mede amostra de sucesso e p95 do health, com escopo limitado.
9. `scripts/verify_frontend_build_v10.sh`: build explícito do React original em modo de emulador, com evidência somente após sucesso.
10. `.github/workflows/ci.yml`: build V10 e job Docker/Prometheus/Grafana com failover e artifacts; job ainda requer execução real no GitHub.
11. `scripts/release_gate_v10.py`: gate por evidências, com bloqueios reais visíveis.
12. `tests/test_chat_contract_v10.py`: dez novos testes de contrato e storage, além de um teste de namespace em `test_emulator_config_v9.py`.

**Limites:** não há build completo React, testes Firebase HTTP ou Docker executados nesta sessão. A suíte offline não substitui os três.
