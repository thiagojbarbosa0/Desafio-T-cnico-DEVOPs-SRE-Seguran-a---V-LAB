# COURSESPHERE — HANDOFF MESTRE V19.4

**Data:** 23/10/2026 (America/Recife)  
**Ponto de partida:** V19.3, baseada na V19.1 entregue no ChatGPT Work, derivada do repositório original `LambdaAK/CourseSphere`.  
**Estado:** NÃO LIBERADO PARA SUBMISSÃO. Não utilizar credenciais upstream ou publicar um serviço com vulnerabilidades propositais.

## 1. O desafio original (o que a banca realmente avalia)

Trabalhar em uma aplicação existente: identificar **no mínimo cinco vulnerabilidades reais** cobrindo pelo menos duas categorias, reproduzir cada uma e explicar gravidade/impacto; **corrigir três** com causa raiz e regressões; aplicar **dois hardenings**; observabilidade (logs JSON, métricas, dois SLIs/SLOs); Docker backend/frontend, duas réplicas atrás de Nginx com distribuição comprovada; relatório técnico com evidências e recomendações. Diferenciais incluem SAST/SCA/CI, modelagem STRIDE, Grafana, experimentos de resiliência, Kubernetes e deploy protegido.

A prioridade da banca é qualitativa (alta/média/baixa); não foram definidos pesos numéricos. Os percentuais internos abaixo servem apenas para controle de engenharia, NÃO são nota nem previsão de aprovação.

## 2. Arquitetura e limites do escopo

- **Aplicação original:** React + TypeScript + Vite no frontend; Flask no backend; Firebase Auth/Realtime Database; módulos SQLite legados não registrados; recomendador original é demonstrativo/incompleto.
- **Laboratório auxiliar:** API Python de cursos/aulas com dados sintéticos, quotas e testes de autorização; útil para demonstração de infraestrutura, mas NÃO substitui a análise de vulnerabilidades upstream.
- **Docker Compose atual:** duas réplicas do laboratório auxiliar + Nginx + Prometheus/Grafana opcionais. **Não** é uma implantação integral do Flask/Firebase original.
- Segurança do Firebase: regras RTDB negam escrita direta do cliente; mutações autenticadas passam pelo Flask/Admin. Execução com emuladores oficiais ainda necessária.
- Preferência do usuário: execução local e gratuita no Fedora, interface SaaS sóbria e convencional, sem neon ou estética futurista.

## 3. O que o Work e as versões recentes alcançaram

- **V19.1 Work:** testes HTTP Flask 15/15 com Firebase simulado, build React e duas réplicas Flask por Nginx. Resultado histórico da revisão V19.1; ao alterar arquivos posteriores, os hashes dessas evidências deixam de corresponder à versão atual.
- **V19.2:** isolamento de sessões React em chat, conversas e perfil; provas Node de respostas atrasadas entre contas.
- **V19.3:** logs JSON sem query string, bloqueio de tokens em URL no Nginx, filtragem de parâmetros codificados, 240 testes offline, prova nativa Nginx.
- Os achados upstream prioritários e suas ressalvas estão em `docs/REVISAO_ACHADOS_WORK.md`. F01 (cadastro público) e F02 (recomendações anônimas) **não são necessariamente vulnerabilidades exploráveis sem a política de negócio**. F03, F05 e F06 têm evidências mais fortes, mas ainda faltam cinco achados independentes confirmados na aplicação original.

## 4. O que efetivamente mudou na V19.4

**Correção crítica de CI:** em `.github/workflows/ci.yml`, a prova `original-flask-nginx-replication` continha dois comandos dobrados pelo parser YAML em **uma única linha shell**. Agora há bloco `run: |` com duas linhas distintas, preservando a execução da verificação de Nginx e da prova das réplicas Flask.

**Hardening distribuído:** `backend/shared_quota.py` ganhou `profile_write` (20/minuto/UID) e `chat_delete` (30/minuto/UID). `backend/endpoints.py` verifica a quota **depois de validar autenticação/entrada e antes da escrita**, usando transações Firebase compartilhadas entre instâncias. Limite excedido: HTTP **429**; armazenamento indisponível: HTTP **503** (fail-closed, sem mutação nem detalhes internos). Essas medidas são adicionais às quotas anteriores de recomendações, geração de IDs e gravação de chats. A inclusão desses limites em perfil e exclusão são ajustes da versão derivada, não achados upstream independentes.

**Eventos de autenticação sem identificadores pessoais:** as tentativas aceitas/negadas têm log estruturado com tipo de evento, resultado, rota normalizada e request ID, **sem UID/token/query/IP**. `backend/observability.py` também exporta `coursesphere_original_auth_attempts_total{result,route}` usando apenas rótulos de baixa cardinalidade. O endpoint `/metrics` continua condicionado ao opt-in local e loopback. É uma melhoria de observabilidade, não prova de monitoramento produtivo.

**Novos testes/evidências:**
- `tests/test_v19_4_auth_audit_and_write_quotas.py`: 17 regressões novas de concorrência, quotas, falha segura, autenticação e CI.
- `tests/test_v19_4_evidence_gate.py`: 5 testes adicionais impedem contar integração pulada, alterada ou com hashes inválidos.
- `integration/test_v19_4_http_auth_and_quotas.py`: **7 testes preparados** com roteamento Flask real e Firebase simulado; NÃO executados com Flask nesta sessão.
- `integration/run_v19_4_flask_wsgitest.py`: exige **7/7 sem skips** e grava SHA-256 do código testado; caso contrário, marca `validated=false` e retorna erro.
- A suite Firebase Emulator de 23 cenários recebeu provas adicionais **dentro do teste 20** para o bloqueio 429 e recuperação 200 das novas quotas; não foram executadas nesta sessão.
- O job Flask no GitHub Actions passa a executar a nova bateria WSGI e guardar seu relatório.
- `scripts/release_gate_v19_4.py`: mantém pesos internos anteriores e inclui o gate adicional de WSGI **sem inflar o score**; `scripts/verify_local_v19_4.sh` reproduz localmente o que estiver disponível, sem instalar serviços.

## 5. Execuções feitas nesta sessão (NÃO inventar outras)

| Verificação | Resultado | Limite |
|---|---|---|
| Python unittest offline | **262/262 PASS** | Firebase e Flask real não requeridos nos testes offline |
| `scripts.record_offline_v16` | PASS, evidência/hash atualizados | não é pentest integrado |
| Nginx real + configuração incluída | **PASS: 20 requisições por instância, 8/8 após falha; 55 logs sem query** | réplicas do laboratório sintético |
| Três testes Node de sessão | PASS | Node/TS simulado, não build React |
| Sintaxe Python e YAML do GitHub Actions | PASS | execução GitHub remota não verificada |
| Flask WSGI novo (7 casos) | **NOT TESTED** — dependências Flask ausentes; runner mostrou 7 SKIPs e **validated=false** | exigir Fedora ou CI |
| Firebase Emulator 23 casos | **NOT TESTED** | exigir Java, Node, Firebase CLI e Flask/Firebase Admin |
| React V19.4 build completo | **NOT TESTED** | dependências Node ausentes no host |
| Docker/Prometheus/Grafana | **NOT TESTED** | Docker ausente no host |
| Licença/permissão e rotação upstream | **PENDENTE** | exige responsáveis pelo original |

## 6. Progresso e status

- **Implementação estimada: 69%**, mantidos da V19.3 (não aumentado só por ter mais testes).
- **Aceite interno comprovado na V19.4: 15/100 pontos, 2/8 grupos**, após a regeneração das evidências locais. Este valor pode cair ao alterar fontes, porque evidências antigas ficam inválidas.
- Não é possível chamar o projeto de 100% sem integrar os serviços, executar evidências correspondentes à versão e concluir revisão dos cinco achados/três correções.

## 7. Prioridades próximas (ordem importante)

**P0 — valor para banca:** aprofundar revisão de F01/F02 e identificar, se necessário, vulnerabilidades independentes adicionais; demonstrar cinco problemas reais e três correções no upstream com passos e testes reproduzíveis. Não atribuir SQLi à rota legada desativada; não transformar falhas da nossa derivação em achados upstream.

**P1 — validação necessária:** build React atual, `integration.run_original_http_stubbed` e `integration.run_v19_4_flask_wsgitest`, Firebase Emulators 23 casos (incluindo as quotas novas), Nginx com duas réplicas Flask, docker compose observability + failover. Importar e conferir os hashes das evidências; evitar aceitar provas antigas.

**P2 — entrega:** SAST/SCA/CI efetivamente executados, imagens de dashboards reais, relatório final com severidade e impacto, direitos de publicação/rotação upstream, commits limpos. Antes de publicar, remover credenciais/artefatos locais e revisar histórico Git; não expor vulnerabilidades deliberadas na internet.

## 8. Comandos de retomada

Sem instalação, na raiz do projeto:

```bash
bash scripts/verify_local_v19_4.sh
```

Quando houver Flask/Firebase instalados no Fedora:

```bash
.venv/bin/python -m integration.run_original_http_stubbed
.venv/bin/python -m integration.run_v19_4_flask_wsgitest
bash scripts/verify_official_emulators.sh
bash scripts/verify_frontend_build_v14_2.sh
docker compose --profile observability up -d --build
python3 scripts/verify_docker_stack.py --failover
```

Executar só com dependências presentes e laboratório local. As últimas duas linhas operam o **laboratório sintético**. O script de emuladores usa somente projeto `demo-coursesphere-vlab`, sem projeto/segredos dos autores.

## 9. Instruções de continuidade para outras sessões/Work

Ler primeiro este handoff, `docs/REVISAO_ACHADOS_WORK.md` e `evidence/generated/RELEASE_GATE_V19_4.json`; ignorar status otimistas históricos. Preservar a V19.4 como base. Corrigir erros reais e executar testes, nunca aumentar percentuais por existência de arquivos ou testes pulados. **Salvar ZIP e handoff antes de encerrar o contexto**, com status do que passou e o que não foi executado.
