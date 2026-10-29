# HANDOFF MESTRE — CourseSphere V10 | 23 de outubro de 2026

**Leia isto primeiro.** Este arquivo existe para que o candidato controle o projeto, compreenda cada mudança, decida as próximas etapas e não apresente hipóteses como provas. A V10 é uma **versão de engenharia em andamento**, não uma submissão final aprovada. O histórico anterior está em `HANDOFF_MESTRE_V9.md`.

## 1. O desafio original do V-Lab — objetivo, sem confusão

O enunciado pede **analisar a segurança de uma aplicação CourseSphere existente**, não criar uma plataforma concorrente do zero. No mínimo:

1. **Cinco vulnerabilidades reais**, em **duas ou mais categorias OWASP**, com classificação, impacto e reprodução.
2. **Três correções**, cada uma explicando causa raiz e com teste de regressão.
3. **Duas melhorias de hardening** além da funcionalidade original.
4. **Logs de requisições/erros/autenticação**, `health`/métricas, **dois SLIs** e **dois SLOs**, explicação de dashboard.
5. **Dockerfile backend/frontend**, Compose, Nginx e **duas instâncias de backend**, com evidência do balanceamento.
6. **Relatório técnico** claro para devs e gestão, README e comandos reprodutíveis.

O edital dá **prioridade alta** à qualidade das vulnerabilidades, reproduções e correções; **média** ao relatório, hardening e balanceamento; **baixa** ao grau de automação, organização Git e qualidade da instrumentação. **Não existem pesos percentuais oficiais** para calcular uma nota provável.

**Extra:** threat model STRIDE, ambiente isolado, pipeline CI, testes de autorização, Kubernetes, nuvem, arquitetura resiliente, dashboard Grafana funcional.

## 2. Qual é o sistema que estamos modificando?

**Fonte:** ZIP do repositório público `LambdaAK/CourseSphere`, enviado pelo candidato, com a aplicação de recomendação de disciplinas, não um catálogo de cursos/aulas totalmente funcional.

- `backend/`: Flask, Firebase Admin, consulta/recomendação originalmente simulada, parte de SQLite/blueprints não ativada.
- `frontend/`: React, TypeScript, Vite, Firebase Auth/Realtime Database.
- `dashboard/`: **laboratório AppSec sintético independente**, com interface **clara, corporativa, sem neon**, para demonstrar autorização e SRE.
- `ops/`: Nginx, Prometheus, Grafana, regras do Firebase Emulator.
- `audit/`: cópias sanitizadas e artefatos da auditoria original.
- `tests/` e `integration/`: regressão offline, HTTP de sandbox e testes preparados para emuladores.
- `evidence/`: provas observadas, com diferenças entre *executado*, *configurado* e *pendente*.

**Decisão arquitetural:** manter Flask + React + Firebase, porque é a stack do repositório efetivamente fornecido. **Não migrar para Rails ou PostgreSQL só para satisfazer a imagem da vaga**: o edital aceita outras stacks, e uma migração ampla retiraria tempo dos itens prioritários.

## 3. Linha do tempo resumida

- **V1–V4:** protótipo alternativo, antes de receber o ZIP original; não é prova das vulnerabilidades do upstream.
- **V5–V7:** código original incorporado, análise estática, correções iniciais e testes offline dos handlers, remoção de material com credenciais.
- **V8:** laboratório visual redesenhado em padrão SaaS sóbrio e melhorias do gateway.
- **V9:** Nginx nativo testado com duas réplicas e failover; Firebase Emulator preparado, configuração Docker/observabilidade e pipeline.
- **V10 (esta entrega):** correção do contrato React ↔ Flask para mensagens, gravação idempotente de chats no Firebase, logs de requisições em JSON, validação de namespace RTDB emulador, testes de integração mais seguros, gate automático de evidências e CI Docker/Grafana/failover.

## 4. Descobertas técnicas importantes na V10

### 4.1 O frontend original tinha um fluxo de chat quebrado

No arquivo anterior `ChatInterface.tsx`, cada `messageID` guardava **uma Promise** de `h(...)`, mas `validate_messages` no backend exige **string**. Quando serializado em JSON antes de resolver, o identificador não é texto válido. O `botMessage.content` era um **objeto**, porém o backend exige texto. O chat usava a string fixa `someUniqueChatId`, misturando diferentes conversas, e tentava salvar via `beforeunload`, que não garante execução de requisições assíncronas. Há ainda funções no cliente para rotas `PUT/DELETE /chats/.../messages/...` que não existiam no Flask.

**Correção V10:** IDs gerados com `crypto.randomUUID()`, `content` texto, identificador novo por sessão do chat, persistência imediata com `await` e feedback de falha. Rotas de edição de mensagens inexistentes deixam de ser anunciadas pelo cliente. O painel da própria aplicação é simples e legível, coerente com o design pedido.

**Importante:** isso foi testado com testes de contrato em Python e parser TS/TSX; **a comunicação browser → Flask → Firebase real ainda não foi executada**.

### 4.2 Retries duplicavam mensagens no Firebase

O código anterior salvava cada mensagem com `ref.push(message)`, criando uma entrada nova mesmo após repetir a mesma requisição. Agora `Firebase.save_chat` chama uma atualização atômica por chave `messageID`, tornando a repetição **idempotente** para a mesma mensagem.

**Prova já executada:** teste isolado usando o método verdadeiro `Firebase.save_chat` contra referência RTDB fictícia: quatro chamadas com a mesma mensagem produzem uma única entrada; também confirma isolamento por UID. **Não é prova HTTP com o Firebase Emulator**.

### 4.3 Namespace do Firebase Emulator consistente

O projeto `demo-coursesphere-vlab` usa banco `demo-coursesphere-vlab-default-rtdb` nas configurações de backend, frontend e teste de regras. Essa consistência reduz o risco de testar um namespace cujas regras não são as provisionadas pelo emulador. Configuração de loopback e `demo-` permanece obrigatória.

### 4.4 Evidências automatizadas agora podem falhar honestamente

O runner `integration/run_official_emulator_tests.py` só produz `validated: true` se todos os testes HTTP passarem; falhas de setup ou testes são registradas como **não validadas**. A suíte inclui salvamento idempotente, proteção contra `content` objeto e erro de token sem trace interna.

### 4.5 Gate de aceite explícito

`python3 scripts/release_gate_v10.py` gera `evidence/generated/RELEASE_GATE_V10.json`. **Não é porcentagem de desenvolvimento ou chance de aprovação**. São sete grupos de evidências, e até esta entrega apenas dois foram executados com aprovação: suíte offline e Nginx nativo. O projeto NÃO pode ser rotulado “pronto para entrega final” enquanto o gate sinalizar bloqueios.

## 5. Validação realmente executada na V10

| Atividade | Resultado | Onde está a prova |
|---|---|---|
| Suíte Python offline | **104/104 testes passaram** (conferir execução mais recente) | `evidence/generated/RESULTADO_TESTES_V10.txt` |
| Sintaxe dos cinco arquivos TypeScript/TSX críticos | **Parser passou** | mesmo log de testes; **não é type-check/build** |
| Nginx nativo usando config do projeto | **PASSOU** | `evidence/generated/NGINX_LIVE_V9.json` |
| Distribuição entre réplicas | **20+20** requisições | mesmo JSON |
| Failover após derrubar uma réplica | **8/8** requisições atendidas | mesmo JSON |
| Latência de health via Nginx em loopback | p95 local **~0,88 ms** (amostra de 40) | mesmo JSON — **não extrapolar para SLA real** |
| YAML GitHub Actions | **Parse válido** | arquivo `.github/workflows/ci.yml` |
| Flask/Firebase Emulator HTTP | **PENDENTE** | precisa dependências/emuladores; ainda sem JSON de aprovação |
| React `npm ci && npm run build` | **PENDENTE** | dependência ausente do cache npm offline |
| Docker/Prometheus/Grafana/failover | **PENDENTE** | runtime Docker indisponível nesta sessão |
| Cinco provas antes/depois HTTP no original | **PENDENTE** | evidência atual de funções isoladas NÃO equivale a exploração completa |

### Por que não executei os três testes restantes?

Neste ambiente, `Flask` e `firebase-admin` não estão instalados e o índice de pacotes não está disponível; `npm ci --offline` falhou numa dependência não armazenada; `docker` não existe. **Essas etapas têm scripts preparados e testes no CI, não resultados de execução**. NUNCA afirmar o contrário.

## 6. Como começar no Fedora

Extrair o ZIP e entrar em `CourseSphere_V10`:

```bash
bash scripts/verify.sh |& tee evidence/generated/RESULTADO_TESTES_V10.txt
python3 scripts/prove_nginx_native.py
python3 scripts/release_gate_v10.py
```

**Original Flask + Firebase Emulator (sem serviços reais):**

```bash
sudo dnf install -y java-21-openjdk nodejs npm python3-pip nginx
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
bash scripts/verify_official_emulators.sh
```

O script usará apenas `127.0.0.1` e o projeto `demo-coursesphere-vlab`. Firebase CLI/JAR precisam ser baixados uma vez. Prova, se aprovada, em `evidence/generated/FLASK_FIREBASE_EMULATORS_V10.json`.

**Frontend React original:**

Com os emuladores e o Flask rodando em terminais separados (`bash scripts/start_official_flask.sh`), execute:

```bash
bash scripts/verify_frontend_build_v10.sh
cd frontend
cp .env.example .env.local
npm run dev -- --host 127.0.0.1
```

O script gera prova de build somente se `npm ci` e `npm run build` terminarem com êxito. Acesse `http://127.0.0.1:5173`, crie contas **fictícias** e exercite perfil, consulta e chats sem credenciais dos autores.

**Docker + Prometheus/Grafana:**

```bash
bash scripts/start_docker.sh
docker compose --profile observability up -d
python3 scripts/verify_docker_stack.py --failover
python3 scripts/release_gate_v10.py
```

A prova Docker, quando passar, estará em `evidence/runtime/DOCKER_STACK_V9.json`. **Ela valida o laboratório sintético**, não o deploy Flask/Firebase original.

## 7. O que fazer em seguida (na ordem certa para o edital)

**P0 — Segurança da origem:** execute integração emuladores e transforme o conjunto de evidências de funções isoladas em pelo menos **cinco achados HTTP reproduzíveis** em duas categorias; selecione **três correções** com request/responses antes/depois e testes. Não invente falhas onde o código apenas parece suspeito.

**P1 — Operação:** prove build React, Compose real, múltiplas réplicas, Prometheus/Grafana, failover e SLOs; traga logs/prints para o relatório.

**P1 — Relatório e submissão:** decisões, severidade/impacto do negócio, recomendações priorizadas, patches e procedimentos. Criar commits separados no GitHub, com autorização de reutilização do código original.

**P2 — Extras:** threat model, CI, SBOM e demonstrações já existem em versões iniciais; Kubernetes ou deploy em nuvem só depois do P0. Sem custo, sem publicação da sandbox vulnerável.

## 8. Riscos e decisões que precisam do candidato

- O material upstream continha dados em arquivo com `client_id`/`client_secret`: **não copiar nem usar**; proprietário deve **rotacionar**. Excluir da árvore atual não limpa o histórico Git.
- Verificar **licença/permissão de redistribuição** antes de publicar código derivado; repositório público não significa automaticamente software com licença aberta.
- Revisar pessoalmente se os cinco achados selecionados são vulnerabilidades reais e se evidências offline cumprem critérios da banca. Se os 5 falharem na validação integrada, o edital permite aplicação equivalente devidamente explicada.
- Não conectar ao Firebase/OpenAI/rede dos autores. O Firebase Emulator cria instâncias `demo-` exclusivamente em loopback.
- Não confundir o *Security Arena* (laboratório sintético, independente) com o CourseSphere original.
- As afirmações `104 testes`, `p95 local`, `Nginx comprovado` só dizem respeito aos escopos especificados.

## 9. Onde você decide e controla

1. Inspecione `scripts/release_gate_v10.py` e `evidence/generated/RELEASE_GATE_V10.json`: aceite por prova, não por adjetivos.
2. Veja `docs/CHANGELOG_V10.md` para entender exatamente o que foi mudado.
3. Veja `docs/PLANO_PRIORIZADO_V10.md` para fases com ordem e critérios.
4. Execute os testes da seção 6 e guarde os arquivos em `evidence/runtime/` — **não inclua credenciais ou tokens em capturas**.
5. Para cada decisão grande (mudança de stack, exposição pública, banco, hospedagem), registrar ADR e pedir autorização. Para correções locais óbvias, seguir com testes.

**Frase de controle:** estamos construindo um case de auditoria, correção e operação profissional do CourseSphere **original**, apoiado por um laboratório isolado para demonstrações. A qualidade e a reprodutibilidade das provas valem mais que a quantidade de tecnologia.
