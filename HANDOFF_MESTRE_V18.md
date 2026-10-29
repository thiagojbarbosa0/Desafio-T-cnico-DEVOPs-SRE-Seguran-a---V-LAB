# CourseSphere V18 — Handoff mestre de controle

**Data de referência:** 23/10/2026. **Estado:** trabalho em andamento, não liberado para submissão.

## 1. Objetivo original do V-Lab

O desafio **não é construir um CourseSphere do zero**. É analisar um aplicativo existente, identificar pelo menos **cinco vulnerabilidades reais**, comprovar o problema, corrigir ao menos **três causas raízes**, implementar **duas melhorias de hardening**, observabilidade (logs, saúde, métricas, 2 SLIs/SLOs), Docker com duas instâncias + balanceador Nginx, e produzir relatório reproduzível. Extras opcionais: threat modeling, testes automatizados, CI/SAST, Kubernetes, cloud e dashboard funcional.

O repositório fornecido usa **React/TypeScript + Flask + Firebase Authentication/Realtime Database**, além de SQLite para dados auxiliares. O fluxo original de recomendação tem partes incompletas/simuladas e não coincide totalmente com o CRUD de cursos/aulas descrito no edital. Preservamos o código upstream e adicionamos um **laboratório sintético separado** com CRUD para demonstrar estruturas e decisões de engenharia. *O laboratório não serve como prova de vulnerabilidade da origem.*

## 2. Visão de entrega desejada

Uma demonstração técnica original, excelente e honesta, que um avaliador consegue reproduzir: relatório antes/depois das falhas, testes de regressão, arquitetura de dois servidores monitorados, boa UX, execução local, sem serviços pagos ou uso de credenciais do upstream. UI convencional de SaaS: cores contidas, sem neon ou efeitos de ficção científica.

## 3. O que está implementado

- **Auditoria de código e evidências:** cinco achados prioritários nas rotas upstream; comparações com handlers e HTTP local sob Firebase sintético. Referência: `docs/RELATORIO_APPSEC_V18.md`.
- **Correções de causa raiz:** cadastro admin anônimo desativado; autenticação obrigatória e token em Bearer; rejeição explícita de token na URL; erros internos ocultos; validação de campos e mensagens; allowlist de CORS; desativação de debug.
- **Proteções extras:** métricas Flask com rótulos de baixa cardinalidade, headers de segurança, limites de tamanho, quotas transacionais no Firebase para `recommendation` (30/min/UID), `message_id` (120/min/UID) e, na **V18**, `chat_write` (60/min/UID).
- **Experimentos de SRE:** Nginx verdadeiro em loopback distribuindo solicitações entre duas instâncias **sintéticas** com failover; arquivos Docker Compose, Prometheus e Grafana preparados para validação separada.
- **Qualidade e rastreabilidade:** suíte offline com testes funcionais + contratos, fingerprints por conteúdo, CI com jobs de Flask HTTP, Firebase Emulator, React, SAST e Docker; relatórios HTML/JSON com critério de aceite.
- **Segurança de dados:** houve menção a credencial potencialmente sensível no ZIP original; o arquivo foi excluído da derivação. O autor da credencial precisa verificar sua validade e revogá-la/rotacioná-la se necessário.

## 4. Avanço específico da V18

| Alteração | Comprovação |
|---|---|
| Rate limiting distribuído de gravação de chats no Flask original | 12 novos testes offline passando, incluídos nos 209 totais |
| HTTP 429 após exceder quota; 503 quando armazenamento falha, sem gravar | Testes de handler executados isoladamente, sem Flask real |
| 120 gravações simultâneas disputando uma quota | Teste offline com armazenamento transacional sintético |
| Extensão do teste Firebase Emulator para quota `chat_write` | **Preparado, não executado**; continua dentro dos 20 cenários |
| Pipeline e relatórios de controle da V18 | Arquivos atualizados; CI remoto ainda não executado nesta rodada |
| Nginx nativo, duas instâncias sintéticas e failover | **Executado:** 20/20 distribuição, 8/8 respostas após desligamento |

**Resultado desta rodada:** `209/209` testes Python aprovados; teste Nginx `PASSED`. Não há alegação de teste Firebase real ou Docker executado aqui.

## 5. Progresso sem propaganda

- **67% — implementação estimada**, baseada em nossa avaliação qualitativa de escopo. Não é nota, porcentagem calculada por arquivos ou chance de aprovação.
- **15% — aceite ponderado com evidência válida para a V18 neste ambiente** (2 de 8 grupos). Os pesos são definidos internamente para gestão do projeto e **não** são os pesos da banca, que só indica prioridade alta/média/baixa.
- Os **15 testes HTTP Flask da V14.1 executados no Fedora** são uma evidência histórica válida daquele snapshot. Como os arquivos relevantes foram alterados até a V18, eles **não** satisfazem automaticamente o gate atual.

### Oito grupos de validação

1. Regressões offline — **provado** (7 pontos internos).
2. Nginx real com duas réplicas sintéticas/failover — **provado** (8 pontos).
3. Flask HTTP original antes/depois com Firebase falso — **pendente para V18** (20 pontos; 15 casos).
4. Firebase Auth/RTDB Emulator — **pendente** (18 pontos; 20 casos, incluindo as quotas).
5. Build React de produção — **pendente** (7 pontos).
6. Docker Compose, Prometheus, Grafana e failover — **pendente** (15 pontos).
7. Validação de 5 achados ativos e 3 correções de causa raiz em escopo aceito — **revisão humana pendente** (20 pontos).
8. Licença de redistribuição e contato com o proprietário da credencial original — **pendente** (5 pontos).

## 6. Como usar / quem faz o quê

**Agora:** o usuário não precisa executar nada. O pacote V18 tem código, testes e relatórios completos para essa rodada.

**Quando o usuário quiser testar no Fedora:** extrair o ZIP, abrir terminal na pasta `CourseSphere_V18` e executar, sem instalar dependências:

```bash
bash scripts/verify_v18.sh
```

Posteriormente, para integrações locais com possível instalação de dependências e containers, com autorização explícita:

```bash
bash scripts/fedora_validation_v16.sh --install-deps --with-docker
```

Se algum comando falhar, guardar logs e enviar apenas trechos sem tokens, credenciais ou dados pessoais. Os emuladores devem usar o projeto `demo-coursesphere-vlab` no loopback, **nunca o Firebase dos autores**. Não publique portas de laboratório na internet.

## 7. Caminho recomendado (prioridade real do edital)

**P0:** executar e revisar novamente as 15 provas HTTP da V18, confirmar 5 achados ativos e 3 correções independentes; documentar risco de negócio e evidência antes/depois.

**P1:** emuladores oficiais Auth/RTDB (incluindo quota e regras), build React e uma jornada real de login, perfil e chats.

**P2:** subir Docker localmente, demonstrar 2 servidores, Grafana provisionado, Prometheus saudável e recuperação após desligar um servidor.

**P3:** concluir documentação executiva, SBOM/SAST/SCA, licenciamento, GitHub e vídeo/prints finais. Extras avançados somente se não competirem com P0/P1.

## 8. Decisões em aberto (não inventar aprovação)

1. Confirmar se a banca aceita o repositório oficial de **recomendação de disciplinas** como equivalência ao CRUD descrito no edital ou se precisa de extensão funcional destacada.
2. Confirmar licença/permissão para um repositório público derivado e procedimento responsável para a credencial encontrada no ZIP upstream.
3. Escolher estratégia de publicação: código sem nenhuma credencial e sem disponibilização pública do laboratório intencional.
4. Definir se deve existir demonstração extra Kubernetes depois de P0/P1/P2. Não declarar implementado como teste real até executar.

## 9. Onde localizar informações

- `README_V18_COMECE_AQUI.md`: comandos e visão rápida.
- `docs/RELATORIO_APPSEC_V18.md`: achados e causa raiz, com advertências sobre grau de prova.
- `docs/CHANGELOG_V18.md`: mudanças e justificativas desta rodada.
- `reports/CONTROLE_V18.html`: painel de status estático, legível sem serviços.
- `evidence/generated/TESTES_OFFLINE_V13.json`: prova de testes offline da versão corrente, com hash do código (nome histórico).
- `evidence/generated/NGINX_LIVE_V9.json`: prova Nginx nativo atual, com hash (nome histórico).
- `evidence/generated/RELEASE_GATE_V18.json`: aceite desta cópia.

**Regra de ouro:** teste verde não significa projeto 100%; cada afirmação de conclusão precisa corresponder a uma evidência verificável e à versão exata do código entregue.
