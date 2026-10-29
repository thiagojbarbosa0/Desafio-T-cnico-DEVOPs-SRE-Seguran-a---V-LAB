# CourseSphere V-Lab — integração R3 na V19.15

A **V19.15** é a referência. Este trabalho modificou uma base **V19.9 + R2** recuperada, pois a fonte V19.15 não estava acessível em bytes nesta sessão. **Não substituir a aplicação V19.15 pelo ZIP completo R3**.

Passos seguros: extrair o complemento portátil; comparar `patches/R3_CHANGES_FROM_R2.patch` ao checkout atual; integrar PRIMEIRO os testes; comparar `backend/shared_quota.py` e `backend/observability.py` atuais antes de aplicar as correções; avaliar se a V19.15 já implementa request-id de Nginx. Se um arquivo diferir, resolver manualmente, jamais forçar um patch. Não portar compose/CI íntegros sem resolver overlays Docker e novos jobs V19.15.

Resultado auditável da base R3: 450/450 Python; 3 Node; Nginx nativo + gateway aprovados com upstreams sintéticos; 2 de 7 evidências históricas ainda possuem hashes compatíveis, 5 ficaram obsoletas. Gate base R3: 22/100. **Não atribuir isso à V19.15**.

O README técnico completo está em `docs/COURSESPHERE_R3_HANDOFF_2026_10_25.md` na base refinada e incluso neste complemento.
