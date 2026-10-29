# CourseSphere V19 — comece aqui

Este repositório deriva do ZIP original CourseSphere fornecido para o desafio técnico do V-Lab. A aplicação original é uma recomendadora de disciplinas (React/TypeScript + Flask + Firebase), enquanto o laboratório local separado adiciona cenários de cursos/aulas e infraestrutura SRE. **Não confundir as funcionalidades do laboratório com as da origem.**

## Sem instalar nada — verificação local

```bash
bash scripts/verify_v19.sh
python3 -m scripts.release_gate_v19
```

Este roteiro executa regressões offline, tenta a prova Nginx nativa se existir, testa a sintaxe TypeScript com parser instalado e publica o status em `reports/CONTROLE_V19.html`. Não instala pacotes nem inicia Docker. O teste Flask/Nginx é pulado explicitamente se Flask não estiver instalado.

## Próximos testes integrados, quando você decidir executar

**Flask corrigido × original (Firebase simulado):**
```bash
.venv/bin/python -m integration.run_original_http_stubbed
```

**Nginx com duas réplicas Flask originais (Firebase simulado):**
```bash
.venv/bin/python scripts/prove_original_flask_nginx.py
```

**Firebase Emulator Suite real, projeto `demo-` (agora 21 testes):**
```bash
bash scripts/verify_official_emulators.sh
```

**Build React:**
```bash
bash scripts/verify_frontend_build_v14_2.sh
```

**Docker, Prometheus, Grafana (laboratório sintético):**
```bash
bash scripts/start_docker.sh
python3 scripts/verify_docker_stack.py --failover
```

Os testes de emulador requerem Python (`Flask`, `Flask-Cors`, `firebase-admin`), Java e Firebase CLI. O teste Nginx original também exige Nginx; scripts de build podem baixar pacotes gratuitos. As verificações da aplicação original **não usam credenciais do proprietário upstream**.

**Arquivos principais:** `HANDOFF_MESTRE_V19.md`, `docs/CHANGELOG_V19.md`, `docs/RELATORIO_APPSEC_V19.md`, `reports/CONTROLE_V19.html`.

**Pendências críticas:** prova Firebase Emulator 21/21, Flask HTTP atualizado, React build, Docker stack real, revisão manual de cinco achados/ três correções, direitos de redistribuição e rotação de credencial potencialmente exposta no material original.
