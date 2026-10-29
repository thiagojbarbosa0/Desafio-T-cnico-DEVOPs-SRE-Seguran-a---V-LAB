# CourseSphere V13 — Handoff de engenharia

**Data:** 23/10/2026  
**Entrada original:** `CourseSphere-main.zip` enviado pelo usuário (upstream LambdaAK/CourseSphere)  
**Objetivo:** desafio técnico do V-Lab, AppSec + SRE.

## 1 — Qual é a missão?

Não se trata de criar outro CourseSphere: trata-se de **analisar, provar falhas, corrigir e tornar confiável o CourseSphere original**. O edital exige no mínimo cinco vulnerabilidades reais de pelo menos duas classes OWASP, três correções com causa raiz, duas melhorias extras de hardening, logs estruturados, `/health` e métricas ou equivalente, dois SLIs/SLOs, Dockerfiles, duas réplicas atrás de Nginx, evidências do balanceador, relatório técnico e README. Extras: threat model STRIDE, automação CI, SAST/SCA, Kubernetes, Grafana etc. A banca dá **prioridade alta à qualidade dos achados, reprodutibilidade e correções**, prioridade média a relatório/hardening/escalabilidade, e baixa a scanners/commits/observabilidade.

**Não existe peso oficial numérico.** Nossos pesos no relatório de progresso são uma ferramenta interna de gestão, nunca suposta nota da banca.

## 2 — O que é o CourseSphere original?

- React/TypeScript/Vite no frontend; Firebase Auth + RTDB; Flask/Python no backend; SQLite legado.
- É principalmente um sistema de **recomendação de disciplinas**. O código upstream não contém o CRUD completo de cursos/aulas descrito apenas como exemplo no edital; o mecanismo de recomendação original está simulado/incompleto.
- O laboratório de cursos/aulas introduzido pela nossa equipe é independente e serve para mostrar boas práticas e controle de acesso. **Nenhum achado de lá conta automaticamente como uma falha real do upstream.**
- Mantemos Flask/React em vez de migrar para Rails, porque o edital aceita outras stacks e a análise deve focar o código fornecido.

## 3 — Decisões do usuário

Custo **zero**, preferir execução **local** no Fedora, interface SaaS **tradicional e sóbria**, sem neon, brilho ou estética artificial; tecnologia criativa apenas quando agrega prova/valor; autonomia para trabalhar, mas envolver o usuário em decisões irreversíveis como publicação, stack e despesas.

## 4 — Arquitetura e ambientes

**Aplicação original:** React/Vite → Flask HTTP → Firebase Auth/Realtime DB; SQLite histórico para certas consultas. Credenciais originais não são usadas. Emuladores de Firebase (`demo-coursesphere-vlab`) isolam os testes em loopback.

**Sandbox independente:** dashboard HTML/JS convencional → Nginx → duas instâncias Python com banco SQLite local e tokens sintéticos compartilhados. Prometheus + Grafana em Docker monitoram **esta sandbox**, não o Flask original.

**Instrumentação original V13:** o Flask agora possui contador por rota/status/método e histogramas cumulativos Prometheus com rótulos de cardinalidade restrita; `/metrics` somente com `COURSESPHERE_METRICS_ENABLED=1` **e acesso em loopback**. São métricas por processo. Ver `docs/SLOS_FLASK_ORIGINAL_V13.md`.

## 5 — Trabalho feito até V12 (resumo)

- Hardening Flask: desativar cadastro privilegiado anônimo e `debug`, exigir token Bearer válido, não permitir tokens na URL, erros padronizados, validações/limites, CORS restringido e headers.
- Correções frontend: unificar SDK Firebase, cadastrar pelo cliente, normalizar valores, corrigir salvamento de chats e duplicações de mensagens.
- Laboratório sintético com cursos/aulas, papéis/permissões e teste de controle de acesso Alice/Bob; suporte offline, logs JSON, health, métricas e painel discreto.
- Nginx real comprovou duas réplicas e failover em loopback. Docker, Prometheus/Grafana e emuladores foram configurados mas não comprovados em execução.
- Suíte Python, CI configurado, scanners configurados, threat model, relatório de achados e SBOM inicial. Removemos de pacotes derivados arquivo com campos de credenciais upstream (o proprietário precisa rotacioná-las).

## 6 — Exatamente o que V13 acrescentou

1. **Instrumentação do Flask original** em `backend/observability.py` + `backend/endpoints.py`: contador total por rota/status, histograma de latência, labels sem tokens/IDs/queries, `/metrics` privado e desativado por padrão.
2. **Quatro testes de observabilidade** em `tests/test_original_metrics_v13.py`, incluindo corrida com oito threads.
3. **Dois novos cenários HTTP planejados** (13 → 15) verificando que métricas não vazam por padrão e que só respondem com ativação local. Ainda exigem execução com Flask instalado.
4. **Integridade de release mais forte:** `scripts/source_fingerprint.py`, `scripts/release_gate_v13.py`, mudanças no runner de build React, Nginx e Docker. Artefatos de fontes antigas, Grafana não verificado e reinício de réplica falhado não passam o gate.
5. **Cinco testes novos de integridade de evidências**, exigindo hashes atuais e resultados completos. A suíte offline da V13 passou em 139/139.
6. **Novo controlador de validação para Fedora**, `scripts/fedora_validation_v13.sh`, que não instala nada sem `--install-deps` e não inicia Docker sem `--with-docker`.
7. Documento com **dois SLIs/SLOs da aplicação original**, `docs/SLOS_FLASK_ORIGINAL_V13.md`.
8. Critério numérico de progresso claro em `docs/PROGRESSO_V13.md`.

## 7 — Evidências executadas nesta rodada

- `bash scripts/verify_v13.sh`: **139/139 testes offline aprovados**, ver `evidence/generated/TESTES_OFFLINE_V13.log/json`.
- Nginx nativo usando configuração do repositório: **20/20 requisições distribuídas** entre `api-a`/`api-b`; após parar uma, **8/8 respostas válidas da restante**. Métricas não expostas no gateway público. Ver `evidence/generated/NGINX_LIVE_V9.json` (nome histórico do artefato; fonte é V13, SHA registrado).
- A estrutura e sintaxe de arquivos Python foi verificada.
- **Não executados**: os 15 cenários Flask HTTP (Flask/Flask-Cors indisponíveis); 19 cenários Firebase Emulator; `npm ci` + build React; `docker compose` e dashboards reais. Não confundir preparação com validação.
- **Bloqueio externo:** não é possível declarar o upstream redistribuível sem licença/autorização verificada; também não se pode afirmar que a credencial encontrada no ZIP original já foi revogada.

## 8 — Quanto está pronto?

O projeto tem dois números deliberadamente diferentes:

- **~60% de implementação preparada (estimativa subjetiva, pesos internos explícitos).** Abrange código e configuração que ainda faltam validar.
- **15% de aceite ponderado comprovado (cálculo automático, conservador).** São 2 de 8 gates aprovados. Segurança real HTTP e emuladores têm grande peso; não se pode aumentar isso só criando arquivos.

Leia `docs/PROGRESSO_V13.md` para todas as ponderações e seus limites. A porcentagem **não** é probabilidade de aprovação.

## 9 — Caminho crítico ordenado por impacto no edital

**P0-A** Executar 15 casos HTTP Flask original/corrigido com serviços sintéticos, garantir que passaram e registrar SHA dos três arquivos. Revisar cada caso para separar problema de segurança real de desvio sem impacto.

**P0-B** Executar 19 testes do Firebase Emulator local, observar regras por UID e fluxos reais de perfil/chats. Nenhuma credencial de terceiros pode ser usada.

**P0-C** Fechar 5 casos de vulnerabilidades reais ativos no upstream, com duas classes OWASP e pelo menos 3 correções de causa raiz; gravar requests/responses sanitizados, status e limitações. F09 SQL não entra enquanto o blueprint estiver desativado.

**P1-A** `npm ci` + `npm run build` no React com emuladores e teste visual real, para confirmar experiência ponta a ponta.

**P1-B** Docker Compose + Nginx + duas réplicas + Prometheus/Grafana + controle de falhas, coletando screenshot e logs verdadeiros. Distinguir claramente sandbox de Flask original.

**P1-C** Completar relatório, método, evidências, severidades contextualizadas, SLIs/SLOs, recomendações e requisitos de documentação.

**P2** CI/SAST/SCA gerando outputs no GitHub; retomar extras (K8s, SBOM, threat model) apenas depois dos P0. Publicação só se licenciamento permitir.

## 10 — Como retomar (Fedora)

```bash
bash scripts/verify_v13.sh
```

Para instalar dependências gratuitas **localmente e mediante consentimento explícito** e rodar integrações:

```bash
bash scripts/fedora_validation_v13.sh --install-deps
```

Com Docker autorizado e instalado:

```bash
bash scripts/fedora_validation_v13.sh --install-deps --with-docker
```

O último comando deixa contêineres iniciados para inspeção. Terminar com `docker compose --profile observability down`. A conexão Firebase usa **somente** projeto fictício `demo-coursesphere-vlab`, emuladores em loopback e dados sintéticos.

## 11 — Controles do usuário / decisões pendentes

- Confirmar com a banca o requisito de CRUD, já que o upstream é sobre recomendações de disciplinas.
- Decidir sobre publicar código derivado e obter autorização/licença quando necessário.
- Não colocar segredos originais em arquivos públicos. Solicitar ao proprietário revogação/rotação dos expostos.
- Escolher como hospedar o repositório Git público (fork legítimo vs patch set), após verificar o direito de redistribuição.
- Conferir execução real do Docker/Flask/Firebase no Fedora, porque este ambiente não oferece todas as dependências.

## 12 — Ponto de atenção sobre "só testar aos 100%"

A validação integrada é parte inseparável dos 100%. Não é possível honestamente afirmar 100% com o Flask, Firebase Emulator, React e Docker ainda sem execução. O melhor caminho é continuar preparando e automatizando o máximo e realizar as provas restantes em ambiente capaz de rodá-las. Não há testes ou credenciais de produção necessários.
