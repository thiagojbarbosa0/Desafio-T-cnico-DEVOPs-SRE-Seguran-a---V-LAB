# CourseSphere V12 — comece aqui

**Objetivo:** auditar/corrigir o CourseSphere original e demonstrar segurança e confiabilidade para o desafio do V-Lab. Não é criar outro sistema.

1. `bash scripts/verify_v12.sh` — executa os testes offline, Nginx nativo (se instalado), Flask HTTP (se instalado), e o gate de evidências. Requer apenas Python para a suíte principal.
2. `HANDOFF_MESTRE_V12.md` — por que estamos fazendo isso, o que foi feito, o que foi testado, o que falta e o que depende das suas decisões.
3. `docs/RELATORIO_PENTEST_V12.md` — 9 achados preliminares no código original, categorias e severidades condicionais; não confundir achados estáticos com exploits.
4. `evidence/generated/RELEASE_GATE_V12.json` — oito critérios de aceite binários. A V12 tem **2/8 comprovados** no runtime disponível; isso não é pontuação do edital.

## Próximos testes no Fedora

Com venv ativo e dependências instaladas:

```bash
python3 -m integration.run_original_http_stubbed        # requer Flask e Flask-Cors
bash scripts/verify_official_emulators.sh              # requer Firebase CLI/Java/admin SDK
bash scripts/verify_frontend_build_v10.sh              # npm ci + build
bash scripts/start_docker.sh                            # cria ambiente local Docker
python3 scripts/verify_docker_stack.py --failover       # testa com contêineres ativos
python3 scripts/release_gate_v12.py                    # atualiza aceite
```

Todos os testes de segurança devem usar dados sintéticos em loopback, sem credenciais reais, sem testar os autores. A interface principal segue o estilo SaaS convencional, sem neon.
