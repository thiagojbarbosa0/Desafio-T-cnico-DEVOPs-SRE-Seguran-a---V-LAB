# CourseSphere V10 — arranque e controle

**Projeto real do V-Lab:** análise e correção do CourseSphere original, apoiadas por laboratório local demonstrável. Não é criação de outro CourseSphere para substituir a origem.

**Resultado local desta versão:** 104 testes Python de sandbox/harness, validação sintática TS/TSX, Nginx real com 20/20 nas duas réplicas e failover 8/8. **Pendentes:** Firebase Emulator integrado, React compilado, Docker/Grafana executado, cinco provas HTTP antes/depois originais.

```bash
bash scripts/verify_local_v10.sh
```

Para o original, sem credenciais reais:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
bash scripts/verify_official_emulators.sh
bash scripts/verify_frontend_build_v10.sh
```

Para o Docker (instale Docker/Compose no Fedora):
```bash
bash scripts/start_docker.sh
docker compose --profile observability up -d
python3 scripts/verify_docker_stack.py --failover
```

Leia **`HANDOFF_MESTRE_V10.md`** antes de publicar ou fazer mudanças importantes. A publicação exige revisar licenciamento e credenciais no upstream.
