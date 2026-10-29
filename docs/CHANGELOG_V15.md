# Alterações V14.3 → V15 (23/10/2026)

| Área | Arquivo | Correção / ganho |
|---|---|---|
| Resposta da API | `frontend/src/api.ts` | Não fabrica recomendação após 401, 500, erro de rede ou JSON incompatível; verifica `botResponse` e lista `newRecommendations` |
| Mensagens | `frontend/src/components/ChatInterface/ChatInterface.tsx` | Erro ao consultar e erro ao salvar ficam separados. Nunca persiste um erro de rede como resposta do bot |
| Perfil | `frontend/src/api.ts`, `frontend/src/pages/dashboard/Dashboard.tsx` | Perfil recém-criado (`null`) é válido; cabeçalho e status são checados, listener Firebase é desmontado ao sair da tela |
| Transparência | `frontend/src/pages/dashboard/Dashboard.tsx` | Remove descrição enganosa de uma IA paga/funcional; informa que o recomendador está em modo demonstrativo |
| Operação | `scripts/verify_v15.sh`, `scripts/fedora_validation_v15.sh` | Reutiliza `.venv` antes dos testes; flags do Fedora continuam explícitos |
| Entrega | `scripts/release_gate_v15.py`, `docs/HANDOFF_V15.md` | Indicadores conservadores, distinção entre log informado pelo usuário e execução desta cópia |
| Testes | `tests/test_v15_integrity.py`, `tests/test_v15_release_controls.py` | 11 novos testes estáticos de regressão e controle (não são build React) |

Não mudou o visual sóbrio introduzido na V8, nem a estrutura principal do backend Flask original. O pacote preserva histórico das versões anteriores para auditoria, mas o documento **V15** prevalece para decisões atuais.
