# CourseSphere V9 — retomada em 2 minutos

**Objetivo:** identificar/reproduzir 5 vulnerabilidades do CourseSphere original, corrigir 3, reforçar a segurança e demonstrar observabilidade, Docker e balanceamento, com evidências reais.

**A V9 comprovou:** 93 testes Python (unitários + funções originais isoladas + sandbox) e Nginx nativo com a configuração de produção adaptada, distribuindo 40 requisições (20/20) e mantendo 8/8 após falha de uma réplica.

**Ainda falta:** executar o original Flask + Firebase Emulator Suite; compilar React; validar Docker/Grafana em execução. Nenhum desses está marcado como aprovado.

## Testar já (Python + Nginx)
```bash
bash scripts/verify.sh
python3 scripts/prove_nginx_native.py
```

## Executar o original com Firebase Emulator (Fedora)
```bash
sudo dnf install -y java-21-openjdk nodejs npm python3-pip nginx
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
bash scripts/verify_official_emulators.sh
```

## Docker/Grafana (Fedora)
```bash
bash scripts/start_docker.sh
docker compose --profile observability up -d
python3 scripts/verify_docker_stack.py --failover
```

**Leia:** [`HANDOFF_MESTRE_V9.md`](HANDOFF_MESTRE_V9.md) antes de publicar ou mudar stack. **Não conecte aos serviços Firebase/OpenAI dos autores.**
