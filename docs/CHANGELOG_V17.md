# Alterações V16 → V17

| Arquivo | Mudança | Risco / teste |
|---|---|---|
| `backend/shared_quota.py` | Novo débito transacional por UID + ação com fail-closed | 14 testes offline |
| `backend/firebase.py` | `enforce_quota()` grava somente em namespace administrativo | fake RTDB, emulator pendente |
| `backend/endpoints.py` | Quota no recomendador e no hash, respostas 429/503 | HTTP real requer reexecução |
| `integration/test_original_http_stubbed.py` | Adaptação de stub sintético para quota | 15 casos, execução no Fedora pendente |
| `integration/test_official_emulators.py` | Novo teste transação com HTTP 429 → 200 | total passa a 20 casos; ainda não executado |
| `integration/run_official_emulator_tests.py`, `scripts/release_gate_v12.py`, `integration/run_original_http_stubbed.py` | Contagem rigorosa + SHA-256 do limitador | invalida evidências antigas |
| `tests/test_v17_shared_quota.py` | Quotas, paralelismo, falhas e regras de acesso | 14 casos aprovados |
| `scripts/release_gate_v17.py`, `scripts/doctor_v17.py`, `scripts/verify_v17.sh`, `.github/workflows/ci.yml` | Relatório unificado, CI V17 | avaliação de arquivos vinculada ao código atual |
| `docs/RELATORIO_APPSEC_V17.md`, `docs/HANDOFF_V17.md` e `README.md` | Escopo e entregáveis transparentes | revisão humana antes da publicação |

**Nenhuma migração de framework foi feita**. As funcionalidades Flask/Firebase originais continuam preservadas, exceto o novo hardening de controle de uso. Docker e monitoramento da sandbox são mantidos. O visual permanece corporativo discreto.
