# CourseSphere — AppSec & SRE | Versão V15

**LEIA PRIMEIRO:** [`docs/HANDOFF_V15.md`](docs/HANDOFF_V15.md) · [`docs/CHANGELOG_V15.md`](docs/CHANGELOG_V15.md)

Este repositório deriva do **CourseSphere original**, recebido para o desafio técnico de AppSec/SRE. O objetivo não é criar outra plataforma de cursos, mas demonstrar análise de vulnerabilidades, correções de causa raiz, hardening, observabilidade, balanceamento e documentação verificável. O laboratório didático `dashboard/` + `backend/local_server.py` é independente da aplicação original Flask/Firebase.

**Estado V15 (23/10/2026):** 170 testes Python offline aprovados e Nginx nativo comprovado (20/20, depois 8/8). Os 22 arquivos TypeScript/TSX passaram em validação de sintaxe, mas o build React completo permanece sem execução aqui. O usuário comprovou 15/15 testes HTTP reais do Flask contra Firebase simulado na V14.1; a V15 não importa essa comprovação para seu gate sem o artefato reproduzível da mesma cópia. Firebase Emulator e Docker/Grafana seguem pendentes.

**Sem ação necessária agora:** continue a partir do handoff. Quando quiser validar no Fedora, execute `bash scripts/fedora_validation_v15.sh --install-deps --with-docker`; os flags autorizam explicitamente instalação de dependências e execução de contêineres locais. Sem flags: `bash scripts/verify_v15.sh` (testes offline/Nginx quando disponível). Não publique credenciais ou um laboratório vulnerável na internet.

---

## Arquivo histórico das versões anteriores

> **Atualização V14.2 (23/10/2026):** correção dos 11 erros TypeScript relatados no Fedora. Abra [README_V14_2_REACT_CORRIGIDO.md](README_V14_2_REACT_CORRIGIDO.md) para o próximo comando; as provas Flask HTTP 15/15 foram confirmadas no Fedora com Firebase simulado. O build React completo da V14.2 ainda precisa ser executado no Fedora.

# CourseSphere V14

**Comece por [`README_V14_COMECE_AQUI.md`](README_V14_COMECE_AQUI.md).** Para decisões e evidências, leia [`HANDOFF_MESTRE_V14.md`](HANDOFF_MESTRE_V14.md). A V14 ainda não está liberada para submissão definitiva.

---

# CourseSphere V13 — foco em AppSec/SRE no projeto original

**Comece por:** [README_V13_COMECE_AQUI.md](README_V13_COMECE_AQUI.md) · [Handoff Mestre V13](HANDOFF_MESTRE_V13.md) · [Progresso e percentuais](docs/PROGRESSO_V13.md).

**Estado:** 139 testes offline e Nginx nativo comprovados; Flask HTTP, Firebase Emulator, build React e Docker ainda pendentes de execução neste ambiente. O gate registra 15% de aceite ponderado verificado, embora a preparação técnica esteja estimada em ~60%. **Não é uma entrega final certificada.**

---

# CourseSphere V12 — AppSec/SRE do repositório original

**Comece por [README_V12_COMECE_AQUI.md](README_V12_COMECE_AQUI.md), [HANDOFF_MESTRE_V12.md](HANDOFF_MESTRE_V12.md) e [RELATORIO_PENTEST_V12.md](docs/RELATORIO_PENTEST_V12.md).**

**Evidência V12:** 130 testes Python offline passaram e Nginx nativo passou em balanceamento/failover sintéticos. **Ainda não estão comprovados** o Flask HTTP original, Firebase Emulator, build React completo e Docker/Grafana. O quadro de aceite em `evidence/generated/RELEASE_GATE_V12.json` deve ser consultado antes de qualquer alegação de conclusão.

Abaixo preservamos a documentação histórica das versões anteriores; em caso de divergência, prevalecem os arquivos V12.

---

> **Versão V11:** comece por [`README_V11_COMECE_AQUI.md`](README_V11_COMECE_AQUI.md) e [`HANDOFF_MESTRE_V11.md`](HANDOFF_MESTRE_V11.md). O projeto principal é o CourseSphere original corrigido; a Security Arena é apenas um laboratório isolado.

# CourseSphere V10 — AppSec & SRE sobre o repositório original

**Leia antes:** [Handoff mestre V10](HANDOFF_MESTRE_V10.md) · [Guia V10](README_V10_ARRANQUE.md) · [Matriz de prioridades](docs/PLANO_PRIORIZADO_V10.md) · [Mudanças](docs/CHANGELOG_V10.md) · [Gate de evidências](evidence/generated/RELEASE_GATE_V10.json).

**Verificado nesta entrega:** 104 testes Python offline, sintaxe de cinco arquivos TS/TSX, Nginx real (20/20 réplicas, 8/8 após falha) e YAML CI parseado. **Ainda pendente:** integração completa Flask/Firebase emuladores, build React, Docker/Grafana executados, cinco vulnerabilidades HTTP antes/depois no original. O laboratório didático é distinto do aplicativo original.

> As instruções históricas abaixo documentam versões anteriores, mas para executar e avaliar esta versão **use o guia V10**. Números antigos não indicam o estado V10.

---

> **V9:** [Leia o handoff V9](HANDOFF_MESTRE_V9.md) e o [guia rápido](README_V9_ARRANQUE.md). Nginx foi validado nativamente, Firebase Emulator e Docker/Grafana ainda dependem de execução com pacotes instalados.

# CourseSphere V9 — AppSec & SRE (V-Lab)

> **LEIA PRIMEIRO:** este projeto modifica o **CourseSphere original** que o usuário forneceu (`LambdaAK/CourseSphere`). Não é um CourseSphere criado do zero. O desafio é auditar e corrigir uma aplicação existente, praticar AppSec/SRE e demonstrar tudo com evidências. O laboratório de cursos/aulas é um **componente didático independente**, não uma prova de que a aplicação original possuía as mesmas vulnerabilidades.

**Estado:** versão derivada para testes locais. **84 testes Python passaram**, incluindo execução isolada de seis comportamentos dos handlers originais e correções correspondentes. **Ainda não foram testados**: Flask/Firebase reais, build React, Docker/Nginx, Grafana em runtime, Kubernetes ou hospedagem. Evite apresentar o projeto como finalizado.

[**HANDOFF MESTRE V8**](HANDOFF_MESTRE_V8.md) · [**Design V8**](docs/DESIGN_V8.md) · [**Relatório de segurança V7**](docs/RELATORIO_PENTEST_V7.md) · [**Evidências geradas**](evidence/generated/RESUMO_EVIDENCIAS.md) · [**Runbook de SRE**](docs/SRE_RUNBOOK.md)

## Executar do zero no Fedora (sem dinheiro, sem credenciais)

**Requisitos:** Python 3.10+, bash. Nenhum pacote Python externo é necessário para a sandbox.

```bash
bash scripts/verify.sh                     # 84 testes + checks de gateway/segurança + provas offline
python3 scripts/prove_resilience_local.py  # duas réplicas locais e teste de perda de uma delas
bash scripts/start_local.sh                # interface em http://127.0.0.1:8080/lab/
```

O dashboard V8 usa visual claro e convencional, com 4 telas (visão geral, segurança, cursos e confiabilidade). Em "Testes de segurança" você pode exportar um JSON **sem tokens**. As previews em `evidence/ui` usam API mockada, **não representam navegação real até o servidor**.

No dashboard use identidades **sintéticas**; por exemplo, `alice` não pode modificar curso de `bob` (`403`). Ctrl+C encerra. O gateway e backend escutam em `127.0.0.1` por padrão. Não use dados ou credenciais reais.

## Docker Compose (ainda a validar no computador do usuário)

Requisitos: Docker Engine + Compose plugin, sem serviços pagos. Os containers da sandbox são independentes do Flask/Firebase original.

```bash
docker compose config --quiet
bash scripts/start_docker.sh
python3 scripts/collect_evidence.py
# Observabilidade opcional
 docker compose --profile observability up -d
```

- Interface: `http://127.0.0.1:8080/lab/`
- Grafana: `http://127.0.0.1:3000` — senha local gerada em `.env` (não cole a senha em screenshots).
- Prometheus: `http://127.0.0.1:9090`.
- Encerrar sem apagar dados: `bash scripts/stop_docker.sh`.

**ATENÇÃO:** executar `docker compose stop api_a` e verificar a sobrevivência do gateway após a falha **ainda depende da execução local**. O experimento `prove_resilience_local.py` já comprova duas instâncias HTTP compartilhando assinatura e disponibilidade de B após a queda de A, mas **não comprova failover de Nginx**.

## Estrutura real do projeto

| Pasta/arquivo | Papel |
|---|---|
| `frontend/` | React/TypeScript/Vite **original**; autenticação Firebase |
| `backend/endpoints.py` | handlers Flask **originais corrigidos**; execução integrada ainda pendente |
| `backend/firebase.py` | acesso Firebase Admin (somente projeto autorizado) |
| `backend/blueprints/` | módulo SQL legado, **não registrado** no Flask original |
| `audit/baseline/` | snapshots de handlers originais sem segredo + metadados sanitizados |
| `tests/`, `scripts/evidence_engine.py` | regressão e provas antes/depois em **handlers com stubs** |
| `backend/local_server.py`, `backend/demo_store.py` | sandbox sintética executável sem dependências externas |
| `dashboard/` | Security Arena, API de demonstração, indicadores de SRE |
| `ops/`, `compose.yaml` | Nginx, Prometheus, Grafana, réplicas configuradas |
| `docs/RELATORIO_PENTEST_V7.md` | achados, categorias, severidades, causas raízes e limitações |
| `evidence/generated/` | antes/depois JSON, teste de perda de réplica, SBOM, log de testes |
| `HANDOFF_MESTRE_V7.md` | **documento de controle**: objetivos, prioridades, pendências e próximos passos |

## Evidence Engine e cadeia de suprimentos

```bash
python3 scripts/evidence_engine.py
python3 scripts/generate_sbom.py
python3 scripts/check_secrets.py
```

- Evidence Engine registra **seis comportamentos de funções originais** (não testes de um Flask ao vivo) e três observações estáticas/de metadados.
- O SBOM CycloneDX relaciona **397 pacotes npm declarados no `package-lock.json`**, **sem varredura de CVEs**. Para SCA real, rode `cd frontend && npm ci && npm audit --audit-level=high` quando tiver conectividade.
- O ZIP original possuía arquivo com campos de credenciais de API de terceiro; ele **não** foi incluído no derivado. A remoção não revoga segredo: avisar o proprietário e solicitar rotação.
- As verificações da origem, os logs e as métricas são **separados** dos testes do laboratório, para impedir confusão de escopo.

## Interface React original (precisa dependências e Firebase autorizado)

```bash
cd frontend
npm ci
npm run build
```

O fluxo de cadastro agora usa `createUserWithEmailAndPassword` (SDK cliente) em vez de uma rota anônima que acionava Firebase Admin. Valide o login e a configuração de Auth **somente em um projeto próprio/Firebase Emulator** ou com autorização. Não rode scans ofensivos no Firebase externo dos autores.

## Estado objetivo para banca

**Critérios com prioridade ALTA ainda pendentes de comprovação end-to-end:** cinco vulnerabilidades efetivamente demonstradas em uma instância de teste autorizada da **aplicação original** e três correções que as bloqueiam após testes Flask/Firebase. As evidências atuais de handlers com stubs são úteis, mas **não equivalem** a isso. Compose, Nginx, Grafana e CI devem ser testados e documentados com prints/logs reais antes da entrega.

## Ética, segurança e direitos de uso

A sandbox oferece contas sintéticas escolhidas no navegador e **nunca deve ser publicada na internet**. Não reutilize dados, segredos ou contas reais dos mantenedores. Não há licença de redistribuição explícita no ZIP fornecido; confirme permissão para publicar cópia derivada do código e inclua atribuição apropriada. Caso contrário, peça autorização ou publique somente patches/documentação/testes que possam ser distribuídos legitimamente.


## Novidades da V8

- Dashboard SaaS **sóbrio e claro**, sem neon/glow, responsivo e acessível; código em `dashboard/`.
- Nova exportação de evidências de autorização por request ID, sem tokens e com escopo de sandbox explícito.
- Gateway local com validação de framing HTTP, CSP sem `unsafe-inline` e headers de privacidade.
- **84 testes Python**, incluindo integração HTTP real do gateway e verificações de UI (não 84 exploits).
- `evidence/generated/HTTP_GATEWAY_V8.json`: **7 de 7** cenários passaram pelo gateway local.
- `HANDOFF_MESTRE_V8.md`: decisões, próximos passos e lacunas não comprovadas.
