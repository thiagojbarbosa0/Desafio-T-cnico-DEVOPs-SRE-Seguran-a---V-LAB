# Handoff técnico — CourseSphere V17

**Projeto:** desafio AppSec & SRE do V-Lab; stack original Flask/Firebase/React/SQLite; execução preferida Fedora local, orçamento R$ 0; apresentação visual SaaS profissional, clara e sem neon.

## 1. Objetivo original

O desafio não pede outro CourseSphere por padrão: pede analisar uma aplicação web, encontrar **5 vulnerabilidades reais** de pelo menos duas categorias, corrigir **3** com causa raiz e testes, aplicar **2 melhorias de hardening**, demonstrar logs, métricas, **2 SLIs/SLOs**, Docker frontend/backend com Nginx e duas réplicas, e entregar relatório com evidência. Extras incluem SAST, CI, STRIDE, Grafana funcional e Kubernetes. O edital **não define pontos numéricos**; pesos do nosso painel são uma convenção própria.

## 2. Arquitetura atual (não confundir ambientes)

- **A fonte auditada** está em `audit/baseline/` (somente referência). **Código Flask corrigido** em `backend/endpoints.py`, `firebase.py`, `security_core.py`, `shared_quota.py`, `observability.py`; frontend original modificado em `frontend/`.
- **A sandbox demonstrativa** em `backend/local_server.py`, `backend/demo_store.py` e `dashboard/` oferece cursos/aulas sintéticos, autorização, métricas e experimentos sem Firebase. `compose.yaml` serve primordialmente **esta sandbox** em duas réplicas; não afirmar que comprovou réplica do Flask original.
- **Firebase Emulator** e regras estão em `ops/firebase/`; a aplicação real e seus testes integrados não fazem chamadas ao projeto dos autores.
- **Segredos:** a cópia derivada não deve conter a credencial identificada no ZIP original. Publicação requer verificação de licença/permissão e eventual rotação pelo proprietário.

## 3. O que a V17 acrescentou

1. Limitador **distribuído** por usuário autenticado em `backend/shared_quota.py` + `Firebase.enforce_quota`, aplicado em `/users/query` e `/hash`.
2. Transações RTDB sob `server_security/rate_limits/` fora do namespace editável pelo cliente, sem persistir IDs de usuário em texto puro nos caminhos.
3. Respostas `429` por excesso e `503` quando a quota não pode ser verificada; padrão fail-closed.
4. **14 testes** offline novos, incluindo chamadas paralelas e falha do storage.
5. **Um teste HTTP integrado adicional** no Firebase Emulator; suíte agora espera **20**, não 19 casos.
6. Hashes de evidências HTTP e emulator incluem `backend/shared_quota.py`; provas antigas não são reaproveitadas após alteração de segurança.
7. Matriz AppSec reescrita de forma adequada à banca em `docs/RELATORIO_APPSEC_V17.md`; status simples `reports/CONTROLE_V17.html`.

## 4. O que foi validado

- **Suite offline:** execute `bash scripts/verify_v17.sh`; o JSON `evidence/generated/TESTES_OFFLINE_V13.json` é escrito apenas após execução.
- **Nginx nativo:** executado com duas instâncias Python sintéticas, não Docker. 40 requests distribuídos, failover e bloqueio de `/metrics` provados. O script registra a versão/configuração testada.
- **Flask HTTP com Firebase simulado:** usuário aprovou os 15 casos na V14.1 em Fedora, mas a V17 tem mudanças nas fontes; **reexecução V17 pendente**.
- **Firebase RTDB rate limiter, React build, Docker/Grafana:** ainda não executados no stack real desta revisão.

## 5. Controle de progresso

**Implementação estimada V17:** **66%** por escopo de engenharia. **Aceite evidenciado:** consultar o painel regenerado (esperado 15% nesta sessão se suíte e Nginx estiverem corretos). Esse segundo valor resulta de pesos internos que dão mais importância aos testes da aplicação original. Nenhum deles é nota prevista, probabilidade de passar ou promessa de release.

### Próximas ações em ordem

1. **P0 / segurança:** reexecutar o Flask original com Firebase simulado; gerar hashes atuais; conferir 5 achados e 3 correções sob o escopo do edital.
2. **P1 / integração:** rodar Firebase Emulator (agora 20 casos), confirmar isolamento de contas, quota e persistência; compilar React em produção no Fedora/CI.
3. **P2 / confiabilidade:** executar Compose completo com Docker, Prometheus e Grafana, provar failover, salvar evidências/screen.
4. **P3 / entrega:** executar SAST/SCA (Bandit e npm audit), revisar severidades/impacto, commits, licença, confidencialidade e publicação de GitHub.

**Quando o usuário quiser testar:** basta extrair o ZIP, entrar em `CourseSphere_V17` e rodar `bash scripts/verify_v17.sh` para verificação gratuita sem downloads. Para testes integrados, `bash scripts/fedora_validation_v16.sh --install-deps --with-docker` pode instalar dependências e criar contêineres; execute apenas de forma intencional no Fedora. Salve os artefatos gerados e não envie segredos. **Nenhuma ação do usuário é exigida nesta rodada.**

### Riscos que impedem 100%

O Firebase Emulator e o CI de nuvem não foram executados nesta sessão, o Docker não está disponível aqui, o frontend ainda precisa de build TypeScript/Vite, e o laboratório didático não representa todas as funcionalidades do original. Não usar cenários sintéticos como prova de ataque em produção. Confirmar se a banca aceita o upstream recomendador como aplicação-alvo equivalente ao CRUD indicado no edital. Não declarar 100% até existirem evidências integradas e revisão humana.
