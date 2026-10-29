# Atualização R14 (derivada da V19.9; não substitui V19.15)

Leia primeiro **[COMECE_POR_AQUI_R14.md](COMECE_POR_AQUI_R14.md)**. A R14 adiciona limpeza segura de fixtures Firebase e gate com atestado estrito; veja [HANDOFF_R14_2026_10_27.md](HANDOFF_R14_2026_10_27.md).

---

# CourseSphere AppSec/SRE — versão V19.8

**Início:** [README_V19_8_COMECE_AQUI.md](README_V19_8_COMECE_AQUI.md) — [Handoff V19.8](HANDOFF_V19_8.md) — [Observabilidade do Flask original](docs/OBSERVABILIDADE_ORIGINAL_V19_8.md).

A camada original Flask/React e a sandbox didática são independentes. Provas Docker/Flask/Firebase não executadas permanecem pendentes.

---

# CourseSphere — V19.6 (ponto de entrada atual)

**Leia primeiro [`README_V19_6_COMECE_AQUI.md`](README_V19_6_COMECE_AQUI.md) e [`HANDOFF_V19_6.md`](HANDOFF_V19_6.md).** O texto abaixo documenta versões anteriores; não representa o estado de validação de V19.6.

---

# CourseSphere — V19.4 (AppSec & SRE)

**Estado atual:** versão derivada do repositório oficial, para análise e hardening em laboratório autorizado.

**Comece por [`HANDOFF_V19_4.md`](HANDOFF_V19_4.md)** e [`COMECE_AQUI_V19_4.txt`](COMECE_AQUI_V19_4.txt). Os relatórios e handoffs de V7–V19.3 continuam como material histórico, não substituem o estado atual.

V19.4 corrige um bloqueio real do GitHub Actions, protege gravações adicionais com quotas distribuídas e adiciona auditoria de autenticação sem PII. A suíte offline testa funções com Firebase sintético; Flask, Firebase Emulator, React build e Docker/Grafana exigem provas próprias.

```bash
bash scripts/verify_local_v19_4.sh
```

O laboratório independente de cursos/aulas NÃO deve ser confundido com o backend Flask original. Não copiar credenciais upstream, não publicar a aplicação vulnerável e não alegar exploração real de serviços externos.

---

# CourseSphere — V19.3 (continuação V-Lab AppSec/SRE)

**Comece por [`HANDOFF_V19_3.md`](HANDOFF_V19_3.md) e [`COMECE_AQUI_V19_3.txt`](COMECE_AQUI_V19_3.txt).**

O trabalho continua do CourseSphere oficial (Flask/React/Firebase) e do laboratório AppSec/SRE sintético separado. Não é um sistema novo substituto. **A entrega ainda não tem todas as provas integradas para submissão.**

A V19.3 acrescenta logs Nginx JSON sem query string, bloqueio de tokens por URL e novas provas locais. A decisão técnica está em [`docs/ADR_NGINX_LOG_PRIVACY_V19_3.md`](docs/ADR_NGINX_LOG_PRIVACY_V19_3.md).

---

> **Continuidade V19.2 (após ChatGPT Work):** leia primeiro [`docs/HANDOFF_WORK_V19_2.md`](docs/HANDOFF_WORK_V19_2.md). O frontend recebeu proteção contra respostas antigas após troca de usuário/logout. O build React V19.2 ainda precisa ser executado, e os testes adicionais estão no CI. O relatório antigo de 42% vale para V19.1, não para a V19.2 alterada.

> **Versão corrente: V19.** Comece por [README_V19_COMECE_AQUI.md](README_V19_COMECE_AQUI.md) e [HANDOFF_MESTRE_V19.md](HANDOFF_MESTRE_V19.md). Material V7–V18 é histórico, não roteiro atual.

# CourseSphere — V-Lab AppSec & SRE (V18)

Esta entrega deriva do **CourseSphere original**, não substitui sua identidade nem demonstra ataques a um serviço em produção.

**Início rápido:** leia [`README_V18_COMECE_AQUI.md`](README_V18_COMECE_AQUI.md) e [`HANDOFF_MESTRE_V18.md`](HANDOFF_MESTRE_V18.md).

- **Aplicação upstream:** React/TypeScript + Flask + Firebase Auth/Realtime Database e SQLite.
- **Laboratório:** Python padrão + SQLite sintéticos e dashboard convencional.
- **Objetivo de avaliação:** cinco falhas reais/reproduzíveis, três correções de causa raiz, hardening, observabilidade e infraestrutura com evidências.
- **Estado:** V18 ainda NÃO está aprovada para submissão; as integrações com emuladores, React e Docker necessitam de testes em ambiente completo.

`bash scripts/verify_v18.sh` executa o que é testável offline, sem instalações externas.

## Atualização V19.5 — evidências de exposição de segredo upstream

Foi acrescentado o achado **F04** (material de credenciais presente no snapshot original), reproduzível por inspeção **local** e documentado em `docs/RELATORIO_APPSEC_V19_5.md`. Nenhum segredo foi copiado para o pacote; sua validade externa não foi testada. O comando `bash scripts/verify_local_v19_5.sh` executa os testes disponíveis, sem chamar serviços reais dos autores. **O projeto ainda não está pronto para publicação ou submissão definitiva.**

## V19.7 — optional ORIGINAL Flask/React Docker stack

This project provides **two distinct stacks**. `compose.yaml` runs the separate,
synthetic teaching sandbox. `compose.official.yaml` instead runs **two Gunicorn
instances of the patched original Flask API**, the React frontend, and a local
Nginx gateway. Read `docs/STACK_FLASK_ORIGINAL_V19_7.md` before using the latter.
The original Compose profile serves health and frontend without production
credentials, but Firebase-backed account operations require a separate authorized
emulator/integration setup. It is **not** a substitute for those tests or the
Prometheus/Grafana demo profile.

Native gateway contract validation (needs only Python standard library and Nginx):

```bash
python3 scripts/prove_official_nginx_contract_v19_7.py
```

To attempt the real original Docker stack, on a host with Docker and network
access for first builds:

```bash
docker compose -f compose.official.yaml up -d --build
python3 scripts/verify_official_docker_v19_7.py --failover
docker compose -f compose.official.yaml down --remove-orphans
```

All processes/ports bind to localhost by default. Never provide the upstream
authors' credentials to this demonstration. `docs/STACK_FLASK_ORIGINAL_V19_7.md`
explains the scope, limits, expected evidence and recovery.
