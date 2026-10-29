# CourseSphere V11 — Comece aqui

**Em uma frase:** estamos corrigindo e auditando o CourseSphere original para cumprir o desafio AppSec/SRE; o laboratório de cursos/aulas é uma extensão isolada, não um substituto para o upstream.

1. Leia `HANDOFF_MESTRE_V11.md` para saber por que e como construímos cada parte.
2. Leia `docs/RELATORIO_PENTEST_V11.md` para ver os achados, classificações e evidências.
3. Execute `bash scripts/verify_v11.sh` para testes offline e Nginx local, quando disponível.
4. Rode `python3 -m integration.run_original_http_stubbed` depois de instalar Flask/Flask-Cors. O GitHub Actions tem um job dedicado para isso.
5. Depois, rode os testes Firebase Emulator, build React e Docker/Grafana no Fedora; não apresente itens configurados como já demonstrados.

**Design:** profissional, discreto, sem neon. **Orçamento:** zero. **Maior prioridade:** provas reais de segurança no código original e correções de causa raiz.
