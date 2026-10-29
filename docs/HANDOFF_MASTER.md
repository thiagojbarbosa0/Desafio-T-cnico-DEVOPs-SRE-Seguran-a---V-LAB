# CourseSphere — Handoff mestre (base oficial)

## 1. Origem e propósito
Fonte: ZIP `CourseSphere-main.zip` enviado em 22/10/2026, árvore do repositório LambdaAK/CourseSphere, conteúdo datado no arquivo em 04/08/2024. O README original descreve um aplicativo para ajudar estudantes a escolher disciplinas. NÃO é originalmente um CRUD de cursos e aulas com Rails.

**Objetivo do desafio V-Lab:** executar auditoria AppSec reproduzível da aplicação-alvo, identificar pelo menos cinco vulnerabilidades reais em pelo menos duas categorias, documentar impacto e passos de reprodução, corrigir pelo menos três causas-raiz, implementar dois hardenings, instrumentar logs/métricas, definir dois SLIs/SLOs, containerizar com Nginx e duas réplicas, e entregar relatório claro e repositório público.

**Objetivo do candidato:** entregar trabalho impressionante e verificável, combinando produto real, segurança e laboratório demonstrável; custo R$ 0, prioritariamente local no Fedora, setup simples mas controlável; estilo visual premium; diferenciais somente depois da segurança comprovada.

## 2. Decisões
- DEC-001: preservar o CourseSphere original como linha de base e trabalhar em cópia auditável.
- DEC-002: manter inicialmente Flask/Python + React/TypeScript/Firebase (stack factual); a vaga cita Rails/React/PostgreSQL, mas migração total sem motivação introduziria risco e desviaria do código avaliado.
- DEC-003: cinco achados exigidos devem referir-se ao alvo oficial, e *não* às vulnerabilidades artificiais do antigo laboratório independente.
- DEC-004: nenhum serviço pago, nenhuma exploração de Firebase em produção ou de usuários terceiros; somente mocks, dados sintéticos e laboratório local.
- DEC-005: status de cada requisito separado em 'implementado', 'testado em execução', 'documentado' ou 'pendente'.

## 3. Inventário real
- `backend/endpoints.py`: servidor Flask, endpoints de usuário, query, hashing e chat.
- `backend/firebase.py`: Firebase Auth/Admin e Realtime Database; necessita `credentials.json` não incluído.
- `backend/main.py`: cliente OpenAI e leitura de `config.json` (ausente), mais execução de consulta logo na importação — dificulta startup e isolamento.
- `backend/db.py`: SQLite com caminho relativo suspeito e cursor retornado depois de fechar conexão.
- `backend/blueprints/courses.py`: rotas SQL ainda *não registradas*, com rotas `/<string:...>` conflitantes e interpolação SQL.
- `frontend/src`: React + TypeScript + Vite, Firebase e Material UI.
- `frontend/Dockerfile`: Node 16 legado; não há prova de execução da infraestrutura.

## 4. Auditoria preliminar — achados de código e grau de certeza
| ID | Item | Evidência | Classificação | Verificação necessária |
|---|---|---|---|---|
| F-01 | CORS irrestrito | `CORS(app)` no backend original | Configuração insegura observada | Confirmar respostas preflight e superfície autenticada; autenticação por bearer limita impacto |
| F-02 | Token em query string | `GET /users/info?id_token=...` no frontend e backend | Exposição potencial em logs/histórico/telemetria | Confirmar emissão no ambiente local e revisar logs |
| F-03 | Detalhes internos em respostas de erro | `str(e)` em múltiplos endpoints | Exposição de informação em código | Reproduzir com dependências substituídas por stubs |
| F-04 | Servidor em debug | `app.run(debug=True)` | Configuração insegura condicionada à execução direta | Confirmar modo de inicialização usado |
| F-05 | SQL interpolado em blueprint desabilitado | `f"SELECT ... '{semester}'"` | Falha potencial latente, **não exploração ativa demonstrada** | Consertar consultas e ativação segura do blueprint; testar SQLite isolado |
| F-06 | Token Promise não aguardada | `const idToken = user?.getIdToken()` | Erro de integração que enfraquece/rompe autenticação do request | Teste da requisição frontend |
| F-07 | Dependência Node 16 | `frontend/Dockerfile` | Obsolescência tecnológica; vulnerabilidade específica requer scanner | Executar auditoria de imagem e npm |

**Não afirmar '5 vulnerabilidades reais reproduzidas' nesta etapa.** As linhas acima são achados de revisão estática com confirmação limitada.

## 5. Mudanças efetivamente realizadas neste pacote
- CORS restrito por `ALLOWED_ORIGINS` (padrão de desenvolvimento local).
- Token de `GET /users/info` passado no cabeçalho Authorization, não na URL.
- Correção do `await` ausente e do nome do campo `id_token` no request de recomendações.
- Respostas de erro deixam de enviar exceções brutas.
- Desativação de debug em execução direta.
- Headers HTTP mínimos anti-sniffing, anti-framing, referrer e no-store.
- Endpoint `/health` de liveness básico (não testa dependências).

**Limitações:** não executei integração real com Firebase nem frontend; `main.py` carrega `config.json` e chama OpenAI durante importação. Correções de banco de dados, UX e SRE ainda não foram validadas.

## 6. Roadmap por peso da banca
### P0 — prioridade alta
1. Desacoplar inicialização do Flask do OpenAI e da Firebase; criar app factory e injeção de dependências para testes.
2. Construir suite pytest com Firebase fake/local, dados sintéticos, testes de autenticação, autorização, sessões e tratamentos de erro.
3. Auditar cinco falhas *ativas* comprovadas e registrar request, response, impacto, severidade e regressões.
4. Corrigir >=3 falhas de causa raiz em commits pequenos, preservando comportamento.
### P1 — prioridade média
5. Relatório técnico e executivo com recomendações por risco; rate limit por identidade/IP e limites de payload.
6. Prometheus, logs JSON com correlação e sem segredos; dois SLIs/SLOs com consultas PromQL.
7. Containers backend/frontend e Nginx balanceando duas réplicas; evidências reais.
### P2 — prioridade baixa e bônus
8. GitHub Actions, Semgrep, pip-audit/npm audit, SBOM, dependency pinning, secret scan.
9. Grafana local, alertmanager, threat model STRIDE e diagrama de fluxos.
10. Kubernetes local e chaos testing seguros com recuperação, rollback e runbooks.
11. Security Arena + Evidence Engine + consultor offline + UI premium e acessível.

## 7. Controle do usuário
| Decisão | Recomendação | Status |
|---|---|---|
| Preservar app original? | Sim, comparar base e alterações | FIXADO |
| Migrar para Rails/PostgreSQL? | Não antes de testar o app original; avaliar ADR posteriormente | ABERTO |
| Rodar o laboratório sem chaves externas? | Sim, com mocks e dados sintéticos | FIXADO |
| Habilitar features ofensivas em nuvem? | Não | FIXADO |
| Priorização das entregas? | P0 > P1 > P2 | FIXADO |

**Definição de pronto:** rota demonstrável + teste automatizado + evidência armazenada + relatório atualizado + comando reprodutível no Fedora.

## 8. Indicador de conclusão
A porcentagem de 38% da versão anterior é INVALIDADA: referia-se a uma aplicação substituta. Não existe ainda estimativa estatisticamente defensável do original sem execução e checklist de aceite. Indicador atual: **auditoria inicial concluída; desafio ainda não concluído**.

## 9. Comandos de conferência
```bash
python3 -m compileall -q backend
git diff -- backend/endpoints.py frontend/src/api.ts
# Após configurar credenciais de TESTE e dependências:
# cd backend && python endpoints.py
# cd frontend && npm ci && npm run build
```
Nunca use credenciais reais de terceiros ou ataque endpoints remotos para validar o laboratório.
