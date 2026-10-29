# CourseSphere V15 — handoff mestre e estado verificável

**Data:** 23/10/2026 · **Responsável por decisões:** proprietário do projeto · **Escopo:** V-Lab AppSec/SRE

## 1. Qual é o desafio, afinal?

O V-Lab pede uma análise de segurança e confiabilidade de uma aplicação web: encontrar **pelo menos 5 vulnerabilidades** de **2 ou mais categorias**, demonstrar passos de reprodução e risco; corrigir **pelo menos 3** explicando causas raízes; incorporar **2 melhorias extras de hardening**; registrar logs, métricas, **2 SLIs e 2 SLOs**; executar backend/frontend em Docker e demonstrar Nginx entre **2 réplicas**; produzir relatório reproduzível. CI, STRIDE, Kubernetes e dashboard operacional são diferenciais **opcionais**. Os pesos são apenas **alta, média, baixa prioridade** no edital; nossas porcentagens são internas.

### Nosso alvo, não confundir!

- **CourseSphere original** (`LambdaAK/CourseSphere` recebido por ZIP): React/TypeScript, Flask, Firebase Auth/Realtime Database e banco local SQLite. É um recomendador de disciplinas incompleto, não necessariamente um CRUD de cursos e aulas como no enunciado genérico.
- **Versão corrigida:** alterações em `backend/endpoints.py`, `backend/firebase.py`, `frontend/` etc. Devemos provar a diferença antes/depois no **código original**.
- **Laboratório separado:** `backend/local_server.py`, `backend/demo_store.py`, `dashboard/` e `compose.yaml`. Demonstra boas práticas e SRE de forma segura **mas não prova que vulnerabilidades dos cursos sintéticos existiam no upstream**.
- Não migrar para Rails apenas por sugestão da vaga; o edital permite stacks equivalentes. Não publicar nem atacar credenciais, bancos ou URLs dos autores.

## 2. Caminho seguido

1. V5: leitura e primeiras correções do CourseSphere original.
2. V6–V8: laboratório local, autorização, observabilidade, Nginx e interface convencional (sem neon).
3. V9–V12: testes HTTP preparados, integração com emuladores, rastreabilidade de evidências.
4. V13–V14: métricas Flask, verificador de Docker mais rigoroso, varredura preliminar de credenciais e testes offline.
5. V14.1: o usuário executou 15/15 testes HTTP em Flask com Firebase simulado **no Fedora**, após corrigirmos uma expectativa incorreta do teste.
6. V14.2/V14.3: correções de erros de TypeScript relatados no Fedora; V14.3 ajustou a ordem `npm ci → parser → npm run build`. Ainda falta **compilação completa confirmada**.
7. **V15:** correção de tratamento de falhas de recomendação, integridade do chat, perfil recém-criado, listeners de autenticação e validação por `.venv`.

## 3. Mudanças concretas nesta versão

**Frontend, original:**

- `frontend/src/api.ts`: erro de autenticação, falha HTTP e formato inválido de `/users/query` agora são **erros verdadeiros**, nunca mensagens falsas que seriam salvas como recomendações. Checa resposta antes de usar os campos.
- `frontend/src/components/ChatInterface/ChatInterface.tsx`: separa falha de consulta de falha de persistência. Mostra aviso adequado, não inventa resposta; caso a API retorne uma resposta válida mas Firebase não a persista, sinaliza apenas erro de salvamento.
- `frontend/src/api.ts` e `frontend/src/pages/dashboard/Dashboard.tsx`: o listener `onAuthStateChanged` agora pode ser limpo no `useEffect`, evita tratar perfil novo (`null`) como erro e verifica status HTTP antes de ler perfil.
- `frontend/src/pages/dashboard/Dashboard.tsx`: texto descreve corretamente que o recomendador neste ambiente é demonstrativo, sem prometer IA paga funcionando.

**Operação:**

- `scripts/verify_v15.sh` e `scripts/fedora_validation_v15.sh`: preferem `.venv` existente, se houver, e geram nova avaliação do gate; o segundo só instala dependências ou utiliza Docker conforme flags explícitas.
- `scripts/release_gate_v15.py`: novo resumo de implementação **estimada** e aceite, sem aprovar execução que não ocorreu.
- `tests/test_v15_integrity.py` + `tests/test_v15_release_controls.py`: regressões offline específicas para as melhorias. Esses testes de contrato **não são um build TypeScript nem pentest de produção**.

## 4. Comprovação — números de naturezas diferentes

| Etapa | Evidência disponível | Limitação |
|---|---|---|
| Testes Python | **170 testes offline aprovados** nesta V15 (ver `evidence/generated/TESTES_OFFLINE_V13.log`, regenerado no pacote) | Parte dos testes apenas inspeciona contratos de fonte |
| Nginx nativo | 20 requisições para cada réplica, 8/8 após derrubar uma; `/metrics` bloqueado, executado aqui | Réplicas sintéticas, **não Docker nem Flask/Firebase** |
| Flask HTTP antes/depois | 15/15 aprovados no **Fedora com a V14.1**, conforme log informado pelo usuário | No pacote V15 falta o JSON da execução Fedora; não transformar relato em resultado CI automático. `backend/endpoints.py`, teste HTTP e snapshot original são idênticos entre V14.1 e V15 |
| React produção | Arquivos TS/TSX parseados com o TypeScript disponível localmente | `npm ci --offline` falhou por pacote ausente no cache, portanto **Vite/tsc não executados** nesta sessão |
| Firebase Emulator, Docker, Prometheus, Grafana | Scripts e configurações disponíveis | Testes de execução **pendentes**; não contar como aprovados |
| 5 achados e 3 correções | Matriz com F01–F09, 6 comportamentos reproduzidos por handler + 15 testes HTTP anteriores | Revisar cinco achados **independentes, reais e relevantes** e ao menos três causas raízes sem exagerar gravidade |
| Redistribuição e segredo upstream | Segredo removido do pacote derivado; preflight local | Proprietário precisa confirmar licença/permissão de publicação e providenciar rotação de credencial eventualmente exposta |

**Estimativa de implementação V15: ~63%.** Subiu cerca de um ponto pela robustez do frontend e operações; estimativa subjetiva, **não porcentagem de chances de passar**. **Aceite comprovado nesta sessão:** pelo menos os grupos offline e Nginx (15 pontos dos 100 internos). A execução HTTP que o usuário reportou, se incorporada com o relatório de origem e verificada pelo gate, agregará mais 20 pontos. Não se deve somar manualmente à saída atual do gate se o artefato ainda não está no pacote.

## 5. Critérios da banca: ordem de prioridade

**Prioridade ALTA (não flexibilizar):** inventário de ≥5 achados com cenários reproduzíveis e impacto; ≥3 correções que resolvem a causa raiz; testes negativos e positivos que não quebram o fluxo legítimo. É o principal bloqueio para submissão.

**Prioridade MÉDIA:** relatório claro, hardening, SLOs/SLIs, containers, Nginx real e resiliência. Demonstrar logs, comparação entre réplicas e alertas.

**Prioridade BAIXA e diferenciais:** CI real, SAST/SCA, inventário de dependências, STRIDE, Grafana operacional, documentação de incidentes. Evitar adicionar Kubernetes ou IA sofisticada só para impressionar sem conseguir comprovar.

## 6. O que você precisa fazer? (não agora)

**Nenhuma ação agora.** Você pediu para testar depois; o pacote inclui os comandos de retomada. Quando estiver disponível e aprovar a execução no Fedora:

```bash
# Na pasta do projeto V15 extraído
bash scripts/verify_v15.sh
# Quando quiser permitir downloads e containers locais:
bash scripts/fedora_validation_v15.sh --install-deps --with-docker
```

O script de build isolado continua `bash scripts/verify_frontend_build_v14_2.sh`. Em caso de erro, guardar as últimas linhas do log e os JSON de `evidence/generated` e `evidence/runtime`, removendo qualquer token ou senha. Não publicar os emuladores vulneráveis.

## 7. Pendências e responsáveis

- **Assistente:** ajustar erros que aparecerem em CI/build, revisar relatório para ter 5 achados independentes e 3 correções claramente demonstradas, validar SLO/SLI, organizar o README, reduzir duplicação documental.
- **Ambiente Fedora / CI, quando autorizado:** build React com dependências completas, testes Flask + Firebase emuladores, Docker Compose com 2 réplicas, Nginx, Prometheus e Grafana. Só os resultados podem elevar o aceite nesses grupos.
- **Você e os mantenedores:** confirmar prazo, permissão de redistribuição do código original e revogação/rotação de credenciais potencialmente expostas. Não há como provar rotação de um segredo de terceiros no nosso ambiente.

## 8. Critério de '100%'

Não basta que o código exista. **100%** significa requisitos mínimos implementados, evidências reproduzíveis e testes de integração executados sem falhas, relatório e autorização de distribuição regularizados. O gate nunca deve declarar 100% enquanto itens obrigatórios/decisões externas permanecerem pendentes. A entrega pode estar funcional antes disso; não confundir os dois estados.
