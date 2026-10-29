# HANDOFF MASTER — CourseSphere AppSec & SRE V6

**Data de corte:** 22/10/2026 · **Responsabilidade:** documentação técnica de transição, não declaração de aceite · **Referência:** desafio técnico AppSec/SRE do V-Lab e repositório original LambdaAK/CourseSphere enviado por ZIP.

## 0. LEIA ISTO PRIMEIRO — resumo executivo

A V6 contém uma extensão de segurança e confiabilidade que é **executável localmente, sem credenciais e sem gasto**, com testes automáticos reais, dashboard interativo, API sintética para cenários de autorização, auditoria, métricas e configuração de duas réplicas. O backend e frontend originais foram preservados e receberam correções limitadas. **Isso ainda não é uma entrega integral do desafio**, porque falta reproduzir no *CourseSphere original* cinco vulnerabilidades reais cobrindo duas categorias, comparar antes/depois, validar as três correções em um ambiente representativo e executar o Docker real. Não confundir os achados de código com explorações confirmadas. O terminal de integração rodou 60 testes com resultado OK; a renderização do layout foi capturada; o navegador automatizado não pôde acessar a rede local devido ao bloqueio do ambiente, portanto não se fez E2E visual conectado.

**Se você só fizer três coisas agora:** (1) `bash scripts/start_local.sh` para ver o Security Arena; (2) `bash scripts/verify.sh` para confirmar os testes; (3) no Fedora, `bash scripts/start_docker.sh` e `python3 scripts/collect_evidence.py` para registrar os backends distribuindo requisições.

## 1. De onde viemos — a pergunta original

O edital determina análise manual/automatizada seguindo OWASP Top 10, no mínimo cinco vulnerabilidades reais em duas categorias, evidência + severidade + impacto, três correções de causa raiz, dois hardenings, logging estruturado, `/health`/`/metrics`, dois SLIs/SLOs, Dockerfiles backend/frontend, Nginx em frente a **duas instâncias** e relatório técnico reprodutível. SAST/SCA é recomendado; STRIDE, CI de segurança, Kubernetes, dashboard real, deploy em nuvem e testes de autorização são bônus. Os **pesos são qualitativos**, não percentuais: os critérios mais importantes são qualidade dos achados, reprodutibilidade e correções.

Sua visão declarada: produto sofisticado e impecável que impressione pela engenharia, visual impactante, plataforma real **e** laboratório de segurança, ferramentas originais quando fizer sentido, tudo local preferencialmente, custo de operação de **R$ 0**, inicialização simples porém controlável, autonomia criativa com consulta antes de decisões cruciais. A imagem da vaga cita contêineres/nuvem, Rails/React/PostgreSQL, OWASP, CI/CD, JWT/OAuth2, SRE Prometheus/Grafana, Git e automações Shell/Python. Não há obrigação de migrar tudo para Rails no desafio: a descrição do próprio desafio permite outra stack equivalente.

## 2. De qual código partimos — não confundir com o protótipo anterior

- **V1–V4:** app substituto Python/JS criado antes do repositório de referência; **não prova** vulnerabilidades da origem.
- **V5:** primeira derivação da origem, corrigindo CORS, token na URL, erros verbosos, debug e headers; apenas verificação de sintaxe, sem integração Firebase.
- **V6 (esta):** mantém o CourseSphere original; amplia hardening legado com limites/validações, corrige SQL desativado, move inicialização Firebase para lazy loading, remove chamadas OpenAI ao importar; adiciona sandbox isolado com API de cursos/aulas, autorização por dono/papel, tokens curtos assinados, limite de requisições compartilhado via SQLite, logs/métricas, dashboard, CI e infraestrutura de laboratório.

### Arquitetura factual da origem

```text
React + TypeScript + Vite
       | chamadas HTTP
       v
Flask endpoints.py ----> Firebase Admin Auth + Realtime DB
       |
       +--> query_manager.py (resposta placeholder / IA não funcional na base)
       +--> blueprint courses.py (não registrado; SQL legado)
       +--> arquivos locais de catálogo Cornell
```

O frontend original precisa de configuração Firebase legítima, o backend original espera credenciais Firebase, e a API de recomendações está incompleta. **Não alegar que a autenticação real ou o motor de recomendações foram validados.** A chave web pública no `firebaseConfig.ts` não deve ser confundida com uma chave privada de serviço; o segredo é o service account em `credentials.json` e regras/controle do banco.

### Arquitetura V6 (somente laboratório)

```text
                  http://127.0.0.1:8080/lab/
                            |
                Nginx gateway (ou proxy Python)
                            |
                        /api/*
                            |
                 ┌──────────┴──────────┐
                 |                     |
            API api_a              API api_b
            Python                 Python
                 |                     |
                 └─────────┬───────────┘
                           |
                    SQLite WAL no volume
                           |
                cursos / aulas / rate limits /
                 eventos de auditoria sintéticos

       Prometheus -> scraping API a e API b -> Grafana
```

**Limite arquitetural:** SQLite compartilhado por volume serve como demonstração didática em uma só máquina. Não atende um desenho real de múltiplos hosts/nuvem. PostgreSQL/Redis fariam sentido **depois** de validar a superfície original. Tokens HMAC com seleção pública de papéis são intencionais **somente no laboratório local**; não são login de produção nem JWT/OAuth2 industrial.

## 3. Situação verificável por área

| Frente | Entrega concreta | Evidência realizada | Limite pendente |
|---|---|---|---|
| Sandbox APIs | CRUD cursos/aulas, propriedade e papéis, read/write HTTP | 60 testes unitários/integrados | Não substitui integração real da origem |
| Segurança sandbox | token HMAC/expiração, input bounds, parametrização, rate limit DB, bloqueios BOLA | `tests/`, `evidence/TESTES_V6.txt` | Login demo aberto deliberadamente; não publicar |
| Backend Flask original | tokens movidos para Authorization, validações, lazy Firebase, errors genéricos, headers, health | sintaxe compilada e diff de código | Sem integração Flask/Firebase em execução |
| SQL legado | queries parametrizadas, materialização antes de fechar conexão e rotas únicas | revisão estática | Blueprint segue desativado; banco real ausente |
| UI Security Arena | dashboard premium com interação mock/local | print renderizado, HTML/CSS/JS | E2E navegador com API não validado |
| Observabilidade | `/metrics`, `/api/health`, `/api/ready`, logs JSON e request ID | teste HTTP | Grafana/Prometheus não executados aqui |
| Infra | compose, proxy Nginx, api_a/api_b, configs observabilidade | arquivos produzidos | Docker Compose e distribuição ainda não provados |
| Automação | unittest, CI frontend build, Bandit, Docker build; Dependabot | unittest local | CI remota, npm audit e Bandit não executados |
| Pentest origem | identificação de problemas no código | comparação de fontes (ver relatório) | **5 achados ativos comprovados NÃO concluídos** |
| Kubernetes / chaos / SBOM / tracing / cloud | backlog | nenhum | não implementados |

**Indicador numérico honesto:** 60 testes da sandbox passam; **zero** das verificações Docker/CI/Firebase devem ser marcadas como executadas neste ambiente. Nenhuma porcentagem global objetiva foi calculada; “38%” referia-se à antiga aplicação substituta e não vale aqui.

## 4. Achados de maior interesse (P0)

Fonte detalhada: `docs/RELATORIO_PENTEST.md`.

- H-01, CORS permissivo na origem (`CORS(app)`) — configuração insegura observada; impacto depende de como o browser envia credenciais/tokens.
- H-02, token Firebase enviado na URL nas chamadas do frontend original — exposição plausível a logs e infraestrutura intermediária; corrigido no fluxo V5/V6, requer reprodução local com interceptação.
- H-03, `str(e)` exposto em respostas HTTP no original — informação interna exibível mediante falha; corrigido em parte, cenário de teste local requerido.
- H-04, `debug=True` na execução direta original — modo inseguro se servido desta maneira; corrigido em V5/V6; requer prova do runtime usado.
- H-05, SQL interpolado em blueprint inativo — risco latente, não afirmar explorabilidade da aplicação em operação; agora parametrizado mas blueprint continua desligado.
- H-06, body não validado/autorização opcional em `/users/query`, exportação de mensagens insuficientemente validada — revisar intenção funcional e produzir teste de integração; não alegar exploração confirmada.

**Posição de engenharia:** o edital mede **vulnerabilidades reais, reproduzidas no alvo**. O laboratório introduz provas de que *a proteção* funciona em dados sintéticos. Ainda é necessário demonstrar vulnerabilidades verdadeiras da versão de referência sem interagir com dados externos. Não compor evidências enganosas.

## 5. Correções efetuadas vs. correções confirmadas

**Correções implementadas no código:** CORS com allowlist local, headers, ocultação de traceback, debug desativado, tokens no header, validação de entrada, auth exigida para query de usuário, token lazy Firebase, arranjo SQL parametrizado, correção de cursor de banco fechado, ausência de chamada OpenAI no import.

**Correções confirmadas em testes HTTP:** somente na sandbox local: BOLA para curso e aula, token inválido, estudante sem escrita, payload inválido, limite de requests, métricas, readiness, rota não autenticada e outras. **Não atribuir esses testes automaticamente aos endpoints Flask originais.**

**Como fechar P0:** instalar dependências em ambiente isolado, criar `test_client()` para Flask com Firebase fake (sem chamadas de rede), documentar requests/responses *antes da correção* executados em uma branch-base isolada, repetir depois da correção e coletar capturas autenticadas, incluindo contagem de testes de integração real. Fazer commits separados por causa raiz.

## 6. SRE — SLIs e SLOs propostos

1. **Disponibilidade HTTP da API (`/api/*`, excluindo health)**: SLI = `1 - (requisições 5xx / todas requisições)` numa janela deslizante de 30 dias, segmentada por instância; SLO proposto ≥ 99,5%. Nota: 401/403 esperados de políticas de acesso não devem ser classificados como indisponibilidade.
2. **Latência de resposta da API**: SLI p95 da duração de requests em janela de 5 minutos (histogramas Prometheus em `coursesphere_http_duration_seconds_bucket`); SLO proposto p95 < 300 ms. Atualmente o SLO é uma **meta**, não uma medição sustentada.

A fonte da versão de origem não possui indicadores historicamente válidos; as métricas são sintéticas. Em produção, SLOs devem usar janelas com tráfego real, alertas por consumo do error budget e etiquetas com cardinalidade limitada. Veja `docs/SRE_RUNBOOK.md`.

## 7. Como executar e conferir cada alegação (sem Docker)

```bash
cd CourseSphere_Official_AppSec_V6
bash scripts/verify.sh
GATEWAY_PORT=8088 bash scripts/start_local.sh # use 8088 se 8080 ocupado
# abrir http://127.0.0.1:8088/lab/
# selecione Alice + curso de Bob -> HTTP 403
# selecione Bob + curso de Bob -> HTTP 200 (muda título sintético)
```

`start_local.sh` escreve segredo efêmero persistente e SQLite em `.local/` (gitignored). Não copia nem toca dados reais do repositório Cornell. `/api/demo/session` deixa selecionar livremente a identidade sintética; é ferramenta de treinamento, não uma autenticação implementável em público.

**Com Docker**:

```bash
bash scripts/start_docker.sh
curl -s http://127.0.0.1:8080/api/ready
python3 scripts/collect_evidence.py
# confira evidence/runtime/operational_checks.json e dois IDs únicos
# se houver só uma instância, NÃO marque requisito de distribuição concluído
```

Com o perfil opcional de observabilidade, verificar acesso ao Grafana local e as séries reais em painel; executar `docker compose logs --tail=100 api_a api_b` para certificar a identidade de cada instância. Repetir ao derrubar temporariamente `api_a` somente no Docker local e observar falhas/recuperação: não automatizar destruição nem produzir afirmações antes de medir.

## 8. Roadmap ordenado pelo edital

### P0 (prioridade máxima — **antes de cosmética**)
1. Rodar a origem em localhost com emuladores Firebase ou stubs e database sintética.
2. Selecionar cinco falhas **de pelo menos duas classes OWASP**, com requisição mínima, resposta observada, severidade, impacto, condições e evidências com data.
3. Criar testes que falhem **na versão base** e passem na V6 para pelo menos três causas-raiz distintas; preservar a compatibilidade com o React.
4. Organizar commits: `test(security): reproduce ...` / `fix(auth): ...` / `fix(config): ...` etc., cada um com teste.

### P1 (prioridade média)
5. Operar Compose com Nginx e duas réplicas, dados persistentes, resultados coletados; testar falha de uma réplica.
6. Validar endpoints health/ready/metrics, grafana real, logs sem vazamento de tokens, SLI/SLO em consulta PromQL.
7. Refinar relatório com evidência antes/depois, limitações e recomendações executivas.

### P2 (bônus e diferenciação, somente após P0)
8. Rodar CI com GitHub Actions, npm audit, Bandit/Semgrep, SBOM CycloneDX e Dependabot.
9. Threat model STRIDE com trust boundaries e controle priorizado; DAST ZAP em ambiente isolado.
10. Kubernetes local (kind/k3d) com readiness/liveness, secrets, NetworkPolicy; não confundir YAML com operação.
11. Resilience Playground com failover programado, testes de carga, p95 real, artefatos, rollback e runbook.
12. Evidence Engine: gerar relatório automaticamente **a partir de testes reais**, assinando o inventário de arquivos e impedindo números inventados.
13. Polimento React original: integração local/auth emulator, UX e acessibilidade, performance, nova área de administração.

## 9. Principais riscos e consequências

| Risco | Criticidade | Ação |
|---|---|---|
| Aceitação de cinco achados sem exploração no alvo | CRÍTICA | Não enviar até provas de origem e regressões |
| Antiga sandbox confundida com CourseSphere oficial | ALTA | Identidade visual + README com escopo claro; origem intacta |
| Firestore/Firebase real acessado em pentest | CRÍTICA | Não usar URLs originais para testes; usar emulador/fake autorizado |
| Demo HMAC e login seletor expostos publicamente | CRÍTICA | Bind 127.0.0.1; nunca deploy público; APP_MODE demo obrigatório |
| Composição Docker não funcional no Fedora | ALTA | Executar e registrar logs, reparar permissões/volumes |
| Dependências frontend legadas e Node 16 original | MÉDIA | Node 22 + npm audit CI, atualizar sem quebrar build |
| SQL em SQLite volume compartilhado escalando em múltiplos hosts | MÉDIA | local somente; PostgreSQL para produção; RLS por recurso |
| Interface bonita sem verificações reais | ALTA | toda métrica visual com origem e status de evidência |
| Tocar no motor de recomendação incompleto | MÉDIA | tratar como legado/feature flag; não prometer IA funcional |

## 10. Decisões de arquitetura (quem controla)

| ID | Decisão | Status | Revisão |
|---|---|---|---|
| DEC-001 | Usar a origem como baseline; extensão separada | APROVADA PELO CONTEXTO | não alterar sem consulta |
| DEC-002 | Flask + React original; **não migrar tudo a Rails ainda** | PROVISÓRIA | reavaliar após P0 |
| DEC-003 | Testes contra código original com dados sintéticos | OBRIGATÓRIA | não flexibilizar |
| DEC-004 | Custo R$0, offline/localhost prioritário | FIXADA | só mudar mediante autorização |
| DEC-005 | Não publicar credenciais nem sandbox de ataque | FIXADA | não mudar |
| DEC-006 | Adicionar banco PostgreSQL e Redis em produção | ABERTA | depende do benefício e peso |
| DEC-007 | Investir em Kubernetes antes de fechar achados | **NÃO RECOMENDADO** | bônus menor que P0 |
| DEC-008 | Publicação GitHub e estratégia de licença/atribuição | PENDENTE DO USUÁRIO | confirmar condições upstream |

### Quando pedir sua autorização

Perguntar antes de: migração total de stack, custo externo/deploy, publicação de repositório, uso de dados/rede de terceiros, remoção substancial do frontend original ou mudança do objetivo do desafio. Fazer correções testáveis, ajustes de UI e documentação sem consultar a cada commit.

## 11. Plano de commits sugerido (NÃO foram feitos commits reais neste ZIP)

```text
chore: import CourseSphere upstream source and record provenance
fix(security): restrict CORS and remove bearer tokens from URLs
fix(api): validate JSON and suppress internal exceptions
fix(db): parameterize disabled course-blueprint queries
refactor(firebase): defer credentials loading until use
feat(lab): add isolated course/lesson authorization laboratory
feat(obs): add request metrics and structured audit events
feat(infra): configure dual-replica compose, nginx and dashboards
test(security): add negative authorization and token-regression suite
docs: evidence matrix, threat model, runbook and handoff
```

Commits e PRs devem refletir alterações reais, não criar histórico artificial. O ZIP é entrega de arquivos, sem `.git` intencionalmente.

## 12. Qual é o próximo passo para você, na prática?

1. Extrair o ZIP, `cd CourseSphere_Official_AppSec_V6`, ler README e executar `bash scripts/verify.sh`.
2. Abrir `bash scripts/start_local.sh`, explorar o Security Arena; confirmar que Bob pode editar o próprio curso, e Alice é bloqueada.
3. Se o Docker estiver instalado, `bash scripts/start_docker.sh` + script de evidências. Se falhar, compartilhar `docker compose ps`, `docker compose logs --tail 80`, **sem .env**.
4. Revisar `docs/RELATORIO_PENTEST.md`, classificar quais falhas da origem podem ser reproduzidas sem serviços externos e registrar gaps.
5. Só depois publicar repo com documentação, evidências reproduzidas e licença da origem verificada.

### Pergunta crucial em aberto

Você autoriza alterar o **CourseSphere original** de forma mais profunda (criar camada de persistência relacional e fluxo de cursos/aulas) se a reprodução das cinco falhas exigir, ou prefere ficar restrito às funcionalidades que já existiam? **Minha recomendação** é preservar o núcleo como alvo de auditoria e usar a extensão apenas como complemento com etiquetas explícitas.

---

**Critério de excelência:** nenhuma alegação sem teste, nenhuma ferramenta sem propósito, nenhum bônus em detrimento dos achados do edital. Isso é o caminho certo para minimizar risco técnico; aprovação depende também de fatores externos e não pode ser garantida.

## 13. Auditoria adicional da V6 — incidente detectado durante os testes

Ao repetir a suíte, a inicialização simultânea de dois bancos SQLite detectou um `sqlite3.OperationalError: database is locked` durante o `PRAGMA journal_mode=WAL` (falha intermitente). **Não foi escondida.** A correção introduziu repetição com backoff na inicialização e transação `BEGIN IMMEDIATE` para serializar a semeadura sintética. A suíte foi novamente executada e a checagem específica foi repetida 20 vezes; consultar `evidence/STRESS_CONCORRENCIA_20_RUNS.txt`. Isso melhora a demo em duas réplicas, mas ainda não prova a operação Docker.
