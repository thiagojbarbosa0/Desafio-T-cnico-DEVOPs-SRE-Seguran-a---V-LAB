# Mudanças V15 → V16 — 23/10/2026

1. **Proveniência forte:** fingerprints de Nginx passam a incluir `demo_store.py` e `security_core.py`; os de Docker incluem componentes backend, dashboard e configurações completas de Prometheus/Grafana. Assim, edições relevantes invalidam resultados antigos.
2. **Prova Flask HTTP:** runner e gate também exigem hashes de `backend/security_core.py` e `backend/observability.py`. O resultado V14.1 do usuário permanece historicamente válido para a fonte testada, mas não é importado automaticamente para V16 sem o novo artefato.
3. **Failover sem aprovação falsa:** o verificador Docker não considera `compose start` suficiente. Após reiniciar a réplica A, aguarda resposta HTTP atendida por ela.
4. **Firebase no Fedora:** o script de emuladores passa a reutilizar o Python instalado em `.venv`.
5. **Correção de UX:** salvar perfil agora espera o HTTP terminar para informar sucesso/erro e o botão bloqueia envios simultâneos. Mensagens externas de erro não são exibidas integralmente ao usuário.
6. **Painel de controle offline:** `scripts/doctor_v16.py` cria `reports/CONTROLE_V16.html` e `evidence/generated/STATUS_V16.json`, sem mascarar itens não executados.
7. **Regressões:** 13 novos testes de contrato para fingerprints, evidência HTTP, recuperação, dashboard e perfil. Esses testes não substituem React/Vite compilado ou integrações Firebase/Docker.

Nenhuma migração para Rails nem uso de APIs pagas nesta versão. Nenhuma validação de produção foi alegada.
