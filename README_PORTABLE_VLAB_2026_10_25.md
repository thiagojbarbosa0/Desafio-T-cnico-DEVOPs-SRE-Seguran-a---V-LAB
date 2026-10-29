# Adendo V-Lab — sem sobrescrever sua V19.15

Esta pasta da entrega foi desenvolvida **sobre a V19.9 recuperada**, não sobre a V19.15. O arquivo `CourseSphere_V19_15_PORTABLE_AUDIT_ADDON.zip` contém apenas três scripts novos, três arquivos de testes e um documento; use-os como melhorias incrementais à V19.15 **após comparar caminhos e dependências**. Não incorpora Docker Compose, backend, frontend, pacote npm, release gate da V19.15 ou segredos.

Após acrescentar os arquivos à raiz existente (sem tocar em versões antigas):

```bash
python3 -m unittest tests.test_evidence_integrity_vlab tests.test_npm_audit_triage_vlab tests.test_npm_lock_integrity_vlab -q
python3 scripts/npm_lock_integrity_vlab.py --output evidence/generated/NPM_LOCK_INTEGRITY_VLAB.json
```

Ao executar provas de runtime da V19.15, revalide a **versão e os caminhos exatos do checkout** com `evidence_integrity_vlab.py`. A função `verify` aceita uma lista explícita de caminhos com SHA-256 e chaves de testes exigidas. `runtime=True` exige que `deployed_source_freshness` seja `pass`; isso **não comprova sozinho** que a imagem Docker é a correta. A evidência vem da atestação V19.15 original e dos seus testes de integração.

Para triagem npm audit, gere JSONs completos e produção separadamente, sem credenciais, sem `--force`, e classifique usando `npm_audit_triage_vlab.py`. Não inclua relatórios brutos nem arquivos `.local` em um repositório público. Se `npm audit` falhar sem produzir JSON íntegro, o classificador retorna não validado. Consulte `docs/VLAB_AUDITORIA_PROFUNDA_2026_10_25.md` na entrega completa para detalhes.

**Atenção:** migração seletiva; não aplique os patches de gates V19.7/V19.8 diretamente ao release gate V19.15 sem revisão. O CI foi adaptado somente na base recuperada.
