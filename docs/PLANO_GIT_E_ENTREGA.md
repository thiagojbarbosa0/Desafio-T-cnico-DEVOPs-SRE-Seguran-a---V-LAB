# Plano de commits, GitHub e entrega

**Importante:** este ZIP foi gerado sem o histórico Git upstream; não inventamos commits retroativos nem afirmamos que GitHub Actions rodou. Histórico organizado deve existir no repositório que você criar/autorizadamente utilizar. Os diffs verificáveis entre fonte original e V7 ficam em `audit/DIFF_*.patch`.

## Antes de publicar

1. Confirmar autorização/licença de redistribuição do código original; **o ZIP recebido não tem `LICENSE` explícita**. Usar fork quando permitido ou pedir autorização do mantenedor.
2. Verificar secrets: `python3 scripts/check_secrets.py`; os campos reais `client_id`/`client_secret` do ZIP original não estão no derivado. Avisar proprietário para rotação.
3. Conferir todos os artefatos, remover `.env`, sqlite local, arquivos privados e certificados; `.gitignore` contém padrões preventivos.
4. Garantir evidências sem tokens reais e sem dados identificáveis.

## Sugestão de PRs/commits lógicos (não alegar que já existem)

- `docs: estabelecer baseline e matriz de riscos da aplicação original`
- `fix(auth): remover cadastro anônimo por Admin SDK e exigir Bearer`
- `fix(security): restringir CORS, suprimir erros e validar entradas`
- `test(appsec): reproduzir casos antes e depois com dados sintéticos`
- `feat(sre): adicionar métricas, health, duas réplicas e ensaio de falhas`
- `ci: introduzir SAST, SCA, SBOM e evidências de testes`
- `docs: finalizar relatório, STRIDE, runbook e instruções de execução`

Dividir commits/PRs de acordo com mudanças **reais**, não criar histórico enganoso só para parecer retrospectivamente mais elaborado. Recomendo PR de correções legadas separado do laboratório sintético, com o relatório explicando essa distinção.

## Critérios de GitHub Actions

Exigir `stdlib-regression` verde; depois revisar `frontend-build` (precisa acesso npm), `python-sast` (precisa Bandit) e `docker-build`. Capturar URLs de execuções e anexar no relatório. Corrigir advisory de gravidade alta que efetivamente afete a aplicação; exceções precisam justificativa específica.

## Entrega final mínima

Repositório legítimo com código corrigido, commits coerentes, `README.md`, `HANDOFF_MESTRE_V7.md`, relatório de achados com cinco provas válidas, três correções testadas, Dockerfiles, Compose com Nginx e duas instâncias, SLIs/SLOs e evidências de runtime. Extras devem demonstrar valor sem esconder pendências da análise original.
