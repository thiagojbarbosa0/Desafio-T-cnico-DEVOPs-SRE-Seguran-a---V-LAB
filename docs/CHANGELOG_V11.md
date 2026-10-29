# Changelog V10 → V11

**Foco:** qualidade da prova do código original, segurança do cliente e confiabilidade dos testes.

| Grupo | Arquivo(s) | Mudança | Status da comprovação |
|---|---|---|---|
| Evidência HTTP do original | `integration/test_original_http_stubbed.py`, `integration/run_original_http_stubbed.py` | 9 cenários de HTTP Flask real, comparando versão arquivada/corrigida com Firebase sintético | Implementado; execução E3 pendente neste ambiente |
| CI | `.github/workflows/ci.yml` | Job novo Flask real + upload das evidências geradas | Configurado; execução CI depende do GitHub |
| UX e tipagem | `frontend/src/api.ts` | Normalização dos campos jQuery, proteção contra Bearer indefinido, corpo de perfil normalizado | Parser TS/TSX e testes estáticos; build pendente |
| Firebase Emulator | `integration/test_official_emulators.py` | Corrigida expectativa incompatível com fixture preexistente; removida corrida da porta | 4 testes preflight aprovados; suite de integração pendente |
| Verificação local | `scripts/verify_v11.sh`, `scripts/release_gate_v11.py` | Comando único e 8 gates que não tratam mocks como produção | Execução local realizada |
| Regressão e rastreabilidade | `tests/test_v11_traceability.py`, `tests/test_emulator_suite_v11.py` | 17 testes adicionais, total 121 | Executados com Python stdlib |
| Relatório e direção | `docs/RELATORIO_PENTEST_V11.md`, `HANDOFF_MESTRE_V11.md` | Classificação de achados, níveis de evidência, prioridades, riscos e comandos | Documentos editáveis |

**Evidência operacional:** `evidence/generated/NGINX_LIVE_V9.json` é sobrescrito por nova execução do Nginx real com o mesmo gateway versionado no projeto. O identificador V9 do arquivo é histórico, não significa que esta execução seja V9.

**Não foi executado:** Flask real (dependências ausentes), Firebase Emulator, npm build, Docker, Grafana. **Não é correto dizer que os nove cenários HTTP passaram** até o runner E3 produzir JSON com `validated: true`.
