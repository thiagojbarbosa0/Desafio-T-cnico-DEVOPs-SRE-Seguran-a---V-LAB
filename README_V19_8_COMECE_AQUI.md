# CourseSphere V19.8 — Início rápido

A aplicação original é Flask + React + Firebase. O laboratório sintético CRUD é independente.

- **Validado aqui:** 337 testes offline, 3 testes Node de sessão, Nginx real com upstreams sintéticos e failover. **Não** foram validados Docker, Flask WSGI, Firebase Emulator, build npm completo ou Grafana nesta máquina.
- **Novo nesta versão:** endpoint privado para Prometheus na aplicação Flask original e overlay opcional com 2 Flask originais + Nginx + React + Prometheus + Grafana. Secret local obrigatório para scrapes de rede. SLOs: 99% sem 5xx, p95 até 500 ms.
- **Um comando offline:** `bash scripts/verify_local_v19_8.sh`
- **Docker opcional:** `bash scripts/start_official_observability_v19_8.sh` e `python3 scripts/verify_official_observability_v19_8.py --failover`.
- **Handoff detalhado:** `HANDOFF_V19_8.md`.
- **Arquitetura, SLOs e segurança:** `docs/OBSERVABILIDADE_ORIGINAL_V19_8.md`.

Confirme `MANIFEST_SHA256_V19_8.txt` ANTES de testes que regeneram evidências. Nada no pacote contém segredos de terceiros ou senhas da instalação; a geração de segredos locais exige ambiente apropriado.

**Progresso estimado de engenharia: 73%. Aceite com evidência nesta cópia: 15%.** Esses percentuais são heurísticas internas, não avaliação externa ou prontidão para publicação.
