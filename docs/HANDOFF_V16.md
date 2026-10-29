# Handoff mestre — CourseSphere V16

**23/10/2026 | Projeto V-Lab AppSec & SRE | Ambiente-alvo: Fedora, custo zero, preferencialmente local.**

## O objetivo original (sem ambiguidades)

Não é criar um CourseSphere novo. O desafio exige inspecionar um sistema web, identificar **5 vulnerabilidades reais** em ao menos 2 categorias, documentá-las com severidade/impacto/reprodução, corrigir **3 causas raízes** sem quebrar os fluxos legítimos, implantar **2 medidas adicionais de hardening**, instrumentar logs/métricas, **2 SLIs e 2 SLOs**, Docker para frontend/backend, Nginx com **2 réplicas**, provar distribuição e gerar relatório de pentest e confiabilidade. CI/SAST, STRIDE, Kubernetes, Grafana funcional e testes extras são diferenciais.

O edital indica *prioridade alta/média/baixa*, **sem pesos numéricos oficiais**. Nossa distribuição de 100 pontos é ferramenta interna para não confundir código escrito com entrega provada.

## O que é o código que estamos alterando?

O ZIP upstream `LambdaAK/CourseSphere` é um recomendador de disciplinas: **Flask + Firebase Auth/Realtime Database + React/TypeScript + SQLite**, com parte do recomendador originalmente simulada. Foi fornecido pelo usuário e é a base principal da auditoria. Não migrar para Rails só por estar citado na vaga; isso desviaria das vulnerabilidades reais.

A sandbox que criamos em paralelo (`backend/local_server.py`, `dashboard/`, `backend/demo_store.py`) existe para ilustrar autorização, CRUD de cursos e SRE sem Firebase. **Não afirmar que as falhas didáticas existiam no CourseSphere upstream.** A stack Docker atual comprova o laboratório, não o Flask original em duas réplicas.

## Como chegamos aqui

- V5: inventário inicial e correções básicas no upstream.
- V6–V8: sandbox segura e visual corporativo convencional, sem neon.
- V9–V13: Firebase Emulator preparado, evidência HTTP antes/depois, balanceamento Nginx e métricas.
- V14–V15: testes de integridade, hardening, correções da interface e 15 testes HTTP **executados pelo usuário no Fedora na V14.1**. O build React reportou erros, reparados posteriormente mas ainda não executados novamente pelo usuário.
- **V16:** fingerprints mais amplos, recuperação Docker realmente verificada por HTTP, salvamento de perfil esperando o servidor, reutilização de `.venv`, painel de status offline e 13 testes de regressão a mais.

## Estado de validação (verifique `reports/CONTROLE_V16.html`)

O índice de implementação foi estimado qualitativamente em **64%** (V15: 63%), não é uma nota ou chance de aprovação. O aceite é calculado do zero a partir dos oito critérios e das provas atuais; **a porcentagem exata está no painel gerado**. Os 15 casos Flask foram executados no Fedora V14.1, mas o artefato originário não veio anexado, e o novo gate exige hashes dos módulos auxiliares — por isso seu sucesso histórico **não se torna aprovação automatizada desta V16**.

O que já foi demonstrado nesta sessão: a suíte Python local e o Nginx com duas instâncias **sintéticas**, incluindo distribuição e failover. O que falta executar aqui: Flask HTTP completo (Flask indisponível), Firebase Emulator, npm/Vite build (pacote ausente no cache) e Docker/Grafana (Docker indisponível). Em particular, a etapa atual **não autoriza declarar 100%**.

## Mudanças da V16

Veja `docs/CHANGELOG_V16.md` (lista por arquivo e critério). Diferença operacional crucial: provas antigas de Nginx/Docker agora invalidam-se quando mudam segurança, banco sintético, dashboards, alertas ou configuração. Uma réplica Docker não é considerada recuperada até responder depois do restart.

## Controle e como retomar sem pressa

1. Para somente ler o status, abra **`reports/CONTROLE_V16.html`** ou rode `python3 -m scripts.doctor_v16`. Não há downloads nem contêineres.
2. Para rodar a suíte local offline e a prova Nginx se disponível, use `bash scripts/verify_v16.sh`.
3. **Quando o usuário quiser testar no Fedora**, use `bash scripts/fedora_validation_v16.sh --install-deps --with-docker`. As flags permitem baixar dependências e iniciar contêineres. Guarde os JSONs em `evidence/generated` e `evidence/runtime`, não envie tokens ou senhas.
4. Ao revisar o relatório de segurança, comece por `docs/RELATORIO_PRIORIZADO_V16.md`, `docs/SECURITY_MATRIX_V14.md` e os arquivos `audit/baseline/`.

### Próximos marcos (prioridade do edital)

- **P0: Segurança real** — fechar 5 achados distintos e 3 correções, com reprodução HTTP Flask da fonte V16 e rastreabilidade.
- **P1: Integração** — executar Auth/RTDB emuladores e React produção, corrigindo incompatibilidades.
- **P2: SRE** — Compose com duas réplicas, Nginx, Prometheus, Grafana, alertas, health/failover e screenshots.
- **P3: Entrega** — CI em GitHub, logs de ferramentas, revisão de README, licenças, remediação/rotação upstream e publicação autorizada.

## Riscos e limites que não devemos esconder

- O upstream não implementa integralmente o CRUD de cursos/aulas descrito como exemplo no edital; o laboratório local é uma extensão didática. A interpretação desse requisito deve ser confirmada.
- A recomendação original retorna texto demonstrativo; não apresentar como IA funcional nem comprar APIs.
- Os testes Flask com Firebase simulado provam o comportamento dos handlers, **não o serviço original em produção**, nem teste de autenticação real.
- Varredura de segredos é preventiva e parcial; não verifica Git histórico nem revoga chave. O segredo identificado no upstream deve ser avaliado/rotacionado **pelos mantenedores**.
- Direitos de redistribuição do upstream precisam ser confirmados antes de publicar nosso ZIP num GitHub público.

## Decisões sob controle do usuário

Visual corporativo discreto; custo zero; execução prioritariamente local; não trocar a stack sem justificativa; exigir demonstrações reais antes de contar itens como concluídos. Você pediu para deixar os testes Fedora para depois; **nenhuma ação sua é necessária agora**.
