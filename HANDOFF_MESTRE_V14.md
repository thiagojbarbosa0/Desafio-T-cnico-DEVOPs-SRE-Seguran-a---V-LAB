# Handoff mestre — CourseSphere V14 | V-Lab AppSec & SRE

## 1. Em português simples: qual é o desafio?

O V-Lab pede uma **avaliação e modernização de segurança de um sistema existente**, não a criação de outro CourseSphere do zero. O mínimo é identificar cinco falhas reais (cobrindo duas categorias), corrigir três com explicações de causa raiz e testes, aplicar dois controles extras de segurança, medir confiabilidade com logs/SLIs/SLOs, empacotar a aplicação com Docker + Nginx + duas réplicas e entregar um relatório reproduzível. Extras como STRIDE, CI, testes de regressão, dashboard, Kubernetes e deploy são opcionais.

O edital não dá pesos matemáticos, mas prioriza **qualidade, reprodução e correção dos achados** acima dos extras. Os pesos internos que criamos servem apenas para ordenar o trabalho.

## 2. Base técnica e decisão de arquitetura

O usuário enviou o repositório `LambdaAK/CourseSphere`. O sistema original é uma ferramenta de **recomendação de disciplinas** e emprega **React/TypeScript/Vite, Python/Flask, Firebase Auth/Realtime Database e SQLite**. O edital exemplifica um CRUD de cursos/aulas; isso não bate perfeitamente com o upstream. O laboratório de cursos/aulas, com RBAC e duas réplicas, é **complementar**. Nunca deve ser vendido à banca como se fosse a funcionalidade original.

**Decisão atual:** preservar e corrigir o Flask/React originais, sem migrar de maneira cosmética para Rails. Executar apenas serviços locais ou emuladores com dados sintéticos. Infraestrutura Docker da sandbox demonstra o padrão SRE, não uma validação de deploy do Flask/Firebase original.

**Decisão visual:** interface SaaS clara, discreta, convencional, sem neon e sem estética futurista.

## 3. Linha do tempo resumida

- **V1–V4:** protótipo independente criado antes de conhecermos o upstream; não é a base oficial do pentest.
- **V5–V7:** base original recebida, inventário de falhas, correções iniciais e documentação; remoção de arquivo de credencial da distribuição.
- **V8:** revisão visual profissional.
- **V9–V10:** Nginx nativo testado, integração de Firebase preparada, frontend/chats corrigidos, testes ampliados.
- **V11–V12:** provas antes/depois HTTP Flask preparadas, fingerprint dos códigos e evidências, emuladores com 19 cenários preparados.
- **V13:** métricas Prometheus originais e gate ponderado de evidências. Marco ≈60% implementação, 15% comprovado.
- **V14:** nova segurança de mensagens (IDs duplicados/sender inválido), bloqueio explícito de token na URL mesmo havendo Bearer, resposta JSON para HTTP 413, correção do exit code do verificador Docker ao falhar o restart, quatro testes de varredura de credenciais, testes de hardening e documentação de controle.

## 4. O que foi realmente executado nesta rodada

- **151/151 testes Python offline**, rodados com `bash scripts/verify_v14.sh`. Números não devem ser confundidos com cenários HTTP independentes.
- **Nginx nativo real**: 20/20 requisições distribuídas entre as duas réplicas sintéticas e 8/8 respostas após desligar uma delas. Não substitui executar Docker Compose.
- **Verificador de Docker testado por simulação controlada**: o caso em que a réplica NÃO reinicia devolve status não-zero (antes poderia devolver zero).
- **Varredura offline preliminar de segredos:** 172 arquivos texto examinados, zero correspondências com os padrões implementados. **Não** houve análise do histórico Git nem revogação de segredo.
- **Flask original + Firebase real/emuladores, build React e Docker/Grafana:** **não executados** neste ambiente pela ausência das bibliotecas e ferramentas. HTTP simulado em funções/handlers não é HTTP Flask executado.

A prova precisa ser ancorada à versão presente em `evidence/generated/RELEASE_GATE_V14.json`, com hashes das fontes. Os artefatos antigos permanecem disponíveis apenas como histórico.

## 5. Principais achados de segurança do upstream

Ver `docs/SECURITY_MATRIX_V14.md`. Resumo: cadastro via Firebase Admin sem autenticação, consulta sem imposição de auth, token em query string, CORS aberto, divulgação de detalhes de erro, entradas sem limites robustos, debug ligado, credencial terceira no pacote original (validade desconhecida) e SQL interpolado em módulo **não registrado**. Este último NÃO é vulnerabilidade demonstrada de rota ativa.

O mínimo de cinco vulnerabilidades válidas e três correções demonstradas por **HTTP funcional com evidência antes/depois** ainda requer comprovação. Não rotular os achados como pentest concluído.

## 6. Inventário de entregáveis

| Frente | Situação V14 |
|---|---|
| Código Flask original endurecido e estrutura React | Implementado; integração não comprovada |
| Validação segura de perfil/chat/query, autenticação e restrição de token | Implementado; testes offline |
| Teste de Nginx + failover em réplicas sintéticas | Comprovado localmente |
| Configuração Docker Compose + Prometheus/Grafana | Preparada; execução pendente |
| Firebase Auth/Realtime Database local (demo-) | Preparado; execução pendente |
| Scanners/SBOM/CI | Configuração preparada; scanners completos no CI não verificados aqui |
| Relatórios de pentest/SRE/STRIDE | Documentos elaborados; evidências finais pendentes |
| Repositório público e licença | Não realizado; requer aprovação sobre upstream |

## 7. Estado e métricas de controle

**≈62% implementação estimada / 15% aceite ponderado comprovado**. As porcentagens não são oficiais, nem promessa de aprovação. A implementação melhorou um pouco (V13 ≈60%), mas o gate de aceite não aumentou porque ainda faltam execuções de integração.

Pesos do gate (internos): testes offline 7, Nginx real 8, HTTP Flask antes/depois 20, Firebase Emulator 18, React 7, Docker/Grafana 15, cinco falhas/três correções revisadas 20 e licença/segredo 5. Total 100. **Os dois primeiros passaram: 15%.**

## 8. Roadmap pela prioridade do edital

1. **P0 — Provas dos problemas reais**: rodar Flask original/corrigido com Firebase simulado no HTTP e depois Firebase Emulator oficial. Selecionar cinco achados independentes, incluir evidência e causa raiz de três correções.
2. **P0 — Resolver falhas encontradas na integração**: corrigir qualquer divergência; repetir testes e anexar JSON/log.
3. **P1 — Build e operação reais**: executar `npm ci && npm run build`, Docker Compose com duas réplicas, Grafana e métricas, verificando failover e recuperação.
4. **P1 — Relatório técnico**: anexar provas no relatório de gestão e técnico, descrever dois SLIs/SLOs, risco de disponibilidade e recomendações priorizadas.
5. **P2 — Diferenciais**: STRIDE, CI/SCA/SAST, simulação de falha, SBOM e eventual Kubernetes **somente após o P0 ser sólido**.
6. **P0 antes da publicação**: verificar licença, consentimento e comunicar/remediar qualquer segredo exposto com o proprietário.

## 9. Quando o usuário precisa participar? AGORA para integrar/testar

Ainda é possível melhorar código e documentação de forma isolada, mas **não é possível chegar honestamente a 100% de aceite sem pelo menos uma execução de integração**. Este ambiente não oferece Docker nem Flask/Firebase completos e não tem acesso ao catálogo de pacotes. O usuário não precisa examinar visualmente cada tela agora; precisa apenas **executar o fluxo automatizado no Fedora e devolver os resultados**:

```bash
bash scripts/fedora_validation_v14.sh --install-deps --with-docker
```

Esse comando **instala dependências gratuitas sob autorização explícita**, inicia sistemas locais isolados, roda verificações e deixa contêineres para inspeção; para pará-los: `docker compose --profile observability down`. Se Docker não estiver disponível, usar só `--install-deps` e enviar os resultados parciais. Se algum comando falhar, enviar a saída e `evidence/generated/RELEASE_GATE_V14.json`, sem incluir segredos.

**Outra intervenção, não automatizável:** confirmar com organizadores se CourseSphere original de recomendações atende escopo CRUD cursos/aulas e se a distribuição pública do código é autorizada; proprietário original deve revogar/rotacionar a credencial encontrada. Não pedir nem compartilhar a credencial.

## 10. Como acompanhar e controlar sem se perder

Toda nova versão deve trazer: (a) mudanças reais no código, (b) testes executados, (c) evidências verificáveis, (d) porcentagem de implementação e de aceite, (e) próximos bloqueios e quem é responsável. Não marcar 100% até estarem aprovados os requisitos mínimos, evidências integradas e licenças/permissões.

**Arquivos:** `README_V14_COMECE_AQUI.md`, `docs/PROGRESSO_V14.md`, `docs/SECURITY_MATRIX_V14.md`, `docs/CHANGELOG_V14.md` e `evidence/generated/RELEASE_GATE_V14.json`.
