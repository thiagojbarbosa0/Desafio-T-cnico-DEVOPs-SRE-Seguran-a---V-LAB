# HANDOFF MESTRE — CourseSphere V19 (AppSec + SRE)

**Data:** 23/10/2026. **Objetivo:** entregar à banca do V-Lab uma análise de segurança e confiabilidade reprodutível do CourseSphere fornecido, e não criar uma plataforma independente disfarçada de original.

## 1. O que a banca pediu originalmente

**Alta prioridade:** localizar pelo menos cinco vulnerabilidades reais na aplicação analisada, descrever severidade, passos de reprodução e impacto; corrigir no mínimo três causas raízes sem regressão, com evidências reprodutíveis. **Prioridade média:** aplicar pelo menos duas melhorias de hardening; observabilidade (logs estruturados, saúde e métricas, dois SLIs/SLOs, proposta de dashboard); Dockerfiles frontend/backend; Compose + Nginx e duas réplicas; relatório compreensível a desenvolvimento e gestão. **Prioridade baixa:** SAST/SCA, histórico de commits e integração de evidências. Diferenciais opcionais: STRIDE, CI, testes regressivos, Kubernetes, cloud, Grafana real e tratamento de falhas.

O edital aceita stack equivalente. O repositório original enviado é um recomendador de disciplinas, com React/TypeScript, Flask, Firebase e SQLite; parte do CRUD descrito no edital não existe originalmente. O laboratório local de cursos/aulas é uma **extensão sintética** para demonstrações de segurança/SRE; não pode ser apresentado como falha upstream.

## 2. O caminho e por que o seguimos

A implementação inicial V1–V4 foi uma aplicação substituta. Assim que recebemos o ZIP upstream, passamos a manter e auditar a aplicação verdadeira. V5–V12 construíram correções e provas. V13–V18 acrescentaram métricas, rastreabilidade, testes, robustez de chat e rate limiting transacional por UID. Desde V8, a identidade visual é SaaS convencional e discreta, sem neon ou estética de painel de IA.

**Não migraremos para Rails só por causa da imagem da vaga.** O repositório real usa Flask; a proposta é demonstrar segurança de aplicação e operação com a stack que a banca forneceu. Trabalhamos preferencialmente offline, com dados sintéticos, no Fedora e sem depender de serviços pagos. Nunca usamos credenciais upstream para testes.

## 3. Entrega técnica feita na V19

**Correção de segurança importante:** na V18, clientes Firebase autenticados podiam gravar em `users/<uid>` diretamente pela RTDB, contornando validação e quotas aplicadas pelo Flask. V19 fecha `.write` do RTDB para clientes e mantém `.read` somente para o próprio UID. Flask/Firebase Admin segue autorizado a gravar após validação. Esse risco foi encontrado no código derivado V18, não é alegado como descoberta comprovada na origem.

**Prova preparada:** Firebase Emulator 21/21 casos (um novo, de escrita direta negada e leitura permitida). A suíte rejeita 20/21 e exige hashes de código atualizados. **Ainda não executada** neste ambiente sem Firebase Emulator.

**Avanço SRE preparado:** novo roteiro de Nginx com duas réplicas em **processos Flask reais** usando serviços de dados sintéticos; testa distribuição, autenticação, token na URL, `/metrics` bloqueado e oito respostas de sobrevivência após encerramento de uma instância. Job próprio no GitHub Actions. **Ainda não executado** sem bibliotecas Flask neste ambiente.

**Validado nesta rodada:** regressões Python, sintaxe dos 22 arquivos TypeScript/TSX, prova Nginx real com réplicas do laboratório sintético. **Não validado:** build React, runtime Docker, Firebase Emulator e Nginx/Flask original.

## 4. Números de gestão — não confundir

- **69% de implementação estimada**, calculada qualitativamente pelo escopo de código/documentação/configuração. Não é uma medida científica, nota ou probabilidade de passar.
- **15% de aceite integrado e ponderado** na cópia verificada: apenas os testes offline e o Nginx do laboratório atingem os critérios exigidos pelo gate com hashes atuais. Os outros grupos exigem provas independentes.
- A experiência do Fedora confirmou **15/15 HTTP Flask na V14.1** com Firebase falso em 23/10/2026; esses testes são um marco histórico verdadeiro, mas não podem ser promovidos automaticamente como prova atual da V19.

Os pesos internos dos oito gates são: regressões 7, Nginx nativo 8, HTTP Flask antes/depois 20, Firebase Emulator 18, React 7, Docker/observabilidade 15, revisão dos 5 achados e 3 fixes 20, licença/segredos upstream 5. Não são pesos oficiais da avaliação.

## 5. Estado dos critérios

| Item | Estado | Próximo critério de aceite |
|---|---|---|
| Testes locais e integração HTTP sintética | Executados localmente | Manter verde após mudanças |
| Nginx nativo — réplicas do laboratório | Executado localmente | Guardar JSON/hashes |
| Flask original antes/depois | V14.1 passou historicamente | Reexecutar com código V19 |
| Firebase real emulado | Pendente | 21/21, sem skips, com D01 fechado |
| Build React | Pendente | `npm ci`, `tsc -b`, `vite build` |
| Docker, Prometheus e Grafana | Pendente | Duas réplicas, scrape, dashboard e failover real |
| Achados upstream | Avaliação técnica incompleta | Revisão dos cinco achados e três correções reproduzíveis |
| Direitos/licença e credencial upstream | Externo/pendente | Confirmar licença de reutilização e rotação com responsável |

Prova adicional preparada (não substitui um gate): `scripts/prove_original_flask_nginx.py`.

## 6. Regras de governança acordadas

1. Mudanças com efeito grande na arquitetura passam pela sua aprovação. Bugfixes, testes e documentação podem avançar sem te interromper.
2. Nenhum teste pulado vira sucesso, nenhum arquivo YAML vira prova de execução e nenhum ambiente sintético vira produção.
3. Nunca inserir chaves, senhas, tokens válidos ou dados pessoais nos artefatos.
4. Evitar serviços pagos. Laboratórios e emuladores apenas locais, sempre em `127.0.0.1` quando expostos no host.
5. Projeto visual discreto e convencional; não retornar ao neon.
6. Novas versões têm README de arranque, relatório de mudanças, status e evidências vinculadas por hash.

## 7. Quando precisar agir no Fedora

Você pediu para testar depois. **Agora não é necessário fazer nada.** Quando decidir validar, extraia a V19 e siga apenas `README_V19_COMECE_AQUI.md`. Os testes integrados pendentes não podem ser concluídos honestamente neste contêiner sem Firebase/Flask/Docker. O primeiro bloco recomendável será (1) Flask antes/depois, (2) réplica Flask/Nginx, (3) 21 testes Firebase Emulator, (4) React build, (5) stack Docker/observabilidade. Guardar as saídas sem credenciais.

## 8. Riscos e próximos passos priorizados

**P0:** executar integração do Firebase para confirmar regras e quota com backend real emulado; comprovar cinco vulnerabilidades upstream e ao menos três correções; esclarecer autorização de uso do código original. **P1:** compilar React; validar Docker/Grafana/Firebase em conjunto; verificar SLOs a partir de métricas reais. **P2:** enriquecer dashboard, threat model, automações, relatórios e CI de maneira que agregue evidência. A qualidade dos achados pesa mais do que quantidade de extras.

Documentos: `docs/CHANGELOG_V19.md`, `docs/RELATORIO_APPSEC_V19.md`, `docs/MODELO_AMEACAS_FIREBASE_V19.md`, `reports/CONTROLE_V19.html`, `evidence/generated/RELEASE_GATE_V19.json`.
