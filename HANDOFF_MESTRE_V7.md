# HANDOFF MESTRE — CourseSphere AppSec & SRE V7

**Data:** 22 de outubro de 2026  
**Autor da direção do projeto:** candidato ao V-Lab (o usuário)  
**Estado:** desenvolvimento em andamento; testes locais concluídos, integração Firebase/Docker pendente.  
**Documento de comando:** este arquivo controla o objetivo, o escopo, os resultados, as decisões e o que fazer em seguida.

---

## 0. Resposta em 30 segundos

**Não** estamos criando um CourseSphere novo para substituir o oficial. Estamos pegando o **repositório CourseSphere que o usuário forneceu**, encontrando problemas, corrigindo-os e mostrando segurança + SRE com evidências. Também construímos um laboratório isolado de demonstração que **não** é a aplicação original nem comprova falhas da aplicação original.

**Status verificável em V7:** 70 testes Python passaram, seis comportamentos problemáticos dos handlers originais foram executados com stubs e comparados ao código corrigido, um arquivo contendo credencial foi removido da distribuição derivada, duas réplicas locais foram testadas (uma continuou funcionando após derrubar a outra). A **integração real Flask/Firebase, builds React, Docker/Nginx, Grafana, npm audit e deploy NÃO foram validados aqui**. Isso impede declarar desafio totalmente concluído.

## 1. O que foi pedido originalmente pelo V-Lab

Fonte: `Desafio_Tecnico_AppSec - DEVOPS.pdf`, três páginas, enviado pelo usuário. Avalia bolsista AppSec/SRE: analisar uma aplicação com autenticação, CRUD e API; **pelo menos 5 vulnerabilidades em 2 ou mais categorias**, com descrição, severidade, reprodução e impacto; corrigir **3** com causa raiz e commits; **2 hardenings**; logs estruturados, `/health`, `/metrics`, **2 SLIs/SLOs**; Docker frontend/backend, Compose com **2 backends + Nginx**, provas de balanceamento; relatório compreensível para engenharia e gestão; SAST/SCA recomendado. Diferenciais opcionais: STRIDE, ambiente isolado, pipeline CI, testes de autorização, Kubernetes, nuvem, padrões de resiliência e dashboard Grafana funcional.

**Hierarquia de avaliação sem pesos numéricos inventados:**
- **ALTA:** verdade dos achados, capacidade de reprodução, correções que resolvem causa raiz.
- **MÉDIA:** relatório, hardening, balanceamento, prioridades de risco.
- **BAIXA:** scanners, Git/commits, instrumentação (ainda relevantes, mas não na frente das provas).

A imagem da vaga preferia contêineres, Rails, React, PostgreSQL, OWASP, JWT/OAuth2, Prometheus/Grafana, GitHub Actions, TDD. O **repo verdadeiro já usa Python/Flask, React/TypeScript, Firebase e SQLite** e o edital permite stack equivalente. **DEC-01: não migrar tudo para Rails só para listar tecnologias.**

## 2. Visão de produto que o usuário escolheu

- Sofisticado **e** impecável, aparência visual impactante, mas evidência técnica real antes de cosmética.
- Produto CourseSphere genuíno + experiência de auditoria/laboratório AppSec, sem misturar vulnerabilidades reais com falhas encenadas.
- Operação local no **Fedora**, custo zero, preferencialmente um comando de inicialização com controle manual disponível.
- Dashboard, métricas, logs, testes de falha, automação e recursos extras originais **quando efetivamente úteis**.
- O usuário quer controle das decisões arquiteturais e aviso em pontos que dependem dele; evitar consultá-lo para tarefas triviais.

## 3. Arquitetura: dois ambientes diferentes

```text
                      CAMADA ORIGINAL (alvo real da auditoria)
  React / TypeScript / Vite   -->   API Flask (backend/endpoints.py)
           |                                     |
      Firebase Auth SDK                    Firebase Admin SDK
                                         Firebase Realtime Database
                                              SQLite legado (blueprint desativado)

                  CAMADA DIDÁTICA (nova, independente e sintética)
  dashboard HTML/CSS/JS   -->   Gateway local ou Nginx
                                      |
                                +-----+-----+
                                |           |
                             API demo A  API demo B
                                +-----+-----+
                                      |
                               SQLite compartilhado
                           (somente demonstração local)
                            Prometheus + Grafana (Compose opcional)
```

A sandbox tem tokens HMAC **não Firebase**, usuários sintéticos selecionáveis (`alice`, `bob`, `student`, `admin`), CRUD de cursos/aulas, regras de autorização e logs/Prometheus. **Não é produção. Não publicar a sandbox.**

## 4. Histórico para não perder o fio

| Versão | O que ocorreu | O que reaproveitamos |
|---|---|---|
| V1–V4 | Aplicação equivalente criada antes do usuário fornecer o repo verdadeiro | Ideias de UX, SRE e testes; **não** entregar como auditoria original |
| V5 | Recebido `CourseSphere-main.zip`; correções iniciais de origem | CORS, tokens URL, erros, debug, consulta SQL legada |
| V6 | Projeto híbrido oficial + sandbox; muitos testes locais | Dashboard, CRUD sintético, métricas, Compose, Grafana, CI, STRIDE |
| **V7** | Auditoria reproduzível de funções originais, correções adicionais e evidências padronizadas | **Este pacote é a base corrente** |

## 5. O que a V7 comprovou

| Requisito/entrega | Realizado? | Evidência e limite |
|---|---|---|
| Código oficial preservado na derivação | SIM | `backend/`, `frontend/` + snapshots de handlers para comparação |
| Auditoria inicial | SIM | `docs/RELATORIO_PENTEST_V7.md`, 9 observações |
| Pelo menos 5 comportamentos problemáticos demonstrados no handler original | SIM | 6 casos sintéticos em `scripts/evidence_engine.py` |
| Cinco vulnerabilidades **exploradas em Flask/Firebase real** | **NÃO** | Nenhuma execução no Firebase original; ainda pendente |
| Três correções de causa raiz | **SIM no código**, integração pendente | Admin signup, token URL, erros internos; mais input/auth hardening |
| Testes automatizados | SIM | **70 testes Python passaram**, `evidence/generated/test_suite_v7.log` |
| Credenciais de terceiro no repo original | OBSERVADAS | Campos `client_id`, `client_secret` no ZIP original; valores nunca utilizados nem redistribuídos |
| Remoção de arquivo secreto do derivado | SIM | `scripts/check_secrets.py`, `.gitignore`, template sem valor |
| Hardening extra | PARCIALMENTE VALIDADO | CORS, headers, tamanhos, validações, tokens; Flask real pendente |
| Logs estruturados e métricas | SIM, sandbox | `backend/local_server.py`, Prometheus exposition |
| 2 SLIs e SLOs | PROPOSTOS | `docs/SRE_RUNBOOK.md`, sessão p95 e erros CRUD |
| Duas réplicas, mesma assinatura e banco | SIM, stdlib em loopback | `evidence/generated/LOCAL_REPLICA_FAILURE.json` |
| Nginx distribuindo requisições | NÃO TESTADO | `compose.yaml`, `ops/nginx/gateway.conf` configurados |
| Grafana funcional no Compose | NÃO TESTADO | dashboard e provisioning escritos, precisam runtime Docker |
| Frontend React compilado | NÃO TESTADO | `npm ci && npm run build` no Fedora |
| SAST/SCA | CONFIGURADO; RESULTADO PENDENTE | GitHub Actions Bandit/npm audit, sem execução CI comprovada |
| SBOM de lockfile | SIM | CycloneDX com **397** componentes npm bloqueados, não um scan CVE |
| Execução Firebase original | NÃO | precisa credenciais próprias / emulator / regras de acesso |
| Kubernetes/nuvem pública | NÃO | opcionais e de baixo retorno antes de fechar P0 |

**Proibido confundir “há arquivo” com “funcionou”.** Por essa razão não atribuo porcentagem de aprovação, nem “100% do edital” à versão atual.

## 6. Achados prioritários no original

Ver relatório técnico para todos os detalhes, gravidades condicionais e provas antes/depois:

- **CS-01 (P0):** `/users/create` invocava Firebase Admin sem autenticação; agora 410; frontend usa Firebase Client SDK para criar contas.
- **CS-02 (P0):** `/users/info` aceitava `id_token` em query string; agora somente `Authorization: Bearer`.
- **CS-03 (P0):** erro interno exposto com `str(e)`; agora erro genérico e status apropriado.
- **CS-04 (P1):** `/users/query` permitia anônimos; agora exige token (mecanismo de IA original era simulado).
- **CS-05/06 (P1):** chats e perfil não tinham limites eficazes; agora há validação e limites.
- **CS-07 (P0 operacional):** arquivo com credencial de serviço no ZIP original; excluído do derivado, mas **só o proprietário pode revogar a credencial**.
- **CS-08/09 (P1):** CORS aberto e execução Flask com `debug=True`; alterados no código, execução real ainda a verificar.
- **SQLi legado:** SQL f-string em rotas **inativas**; V7 parametrizou consultas, não alegamos SQLi explorável na API em uso.

## 7. As seis ações aprovadas pelo usuário — estado e próximos critérios

### Ação 1 — Analisar profundamente o CourseSphere original

**Feito, revisão inicial ampliada.** Escopo cobriu endpoints, chamadas frontend, Firebase, SQL legado, dependências e arquivo de credencial. **Próximo aceite:** revisar Realtime Database Rules no Emulator e verificar configuração de autenticação com permissão do responsável.

### Ação 2 — Encontrar e demonstrar cinco vulnerabilidades

**Feito em lógica de handler, não em app end-to-end.** Seis casos automatizados antes/depois + três estáticos/metadados. **Próximo aceite (máxima prioridade):** provas HTTP do Flask original numa instância de teste autorizada com identidade e dados fictícios. Não contornar o escopo/autorizações.

### Ação 3 — Corrigir pelo menos três

**Alterações no código efetuadas e testadas em isolamento.** Na V7: signup administrativo desabilitado, frontend passou ao SDK cliente, verificação de bearer, mensagens genéricas, validação e controles de entrada. **Próximo aceite:** integração Flask + React + Firebase Emulator, documentação de commits separados por causa raiz.

### Ação 4 — Melhorar segurança e infraestrutura

**Segurança:** implementada parcialmente no código + sandbox verificada. **Infra:** Compose e Nginx escritos; duas réplicas realmente exercitadas com servidores HTTP stdlib no localhost, mas **sem failover Nginx validado**. **Próximo aceite:** Docker, balanço, Grafana e SAST.

### Ação 5 — Documentar tudo

**Feito em V7:** relatório de segurança, Evidence Engine JSON + resumo, threat model STRIDE (herdado), SRE playbook, SBOM, changelog/handoff, tests; atualização contínua necessária após testes Fedora.

### Ação 6 — Diferenciais

**Entregues e verificáveis:** Evidence Engine original-versus-corrigido, execução isolada sem conta, ensaio de perda de réplica com token compartilhado, SBOM offline, dashboard Security Arena, logs e métricas da sandbox. **Próximos candidatos:** pipeline completo com artefatos e DAST local, GitHub branch protection, backend de produção com regras de acesso testadas; Kubernetes só após Compose aprovado.

## 8. O que você faz no Fedora (ordem segura e verificável)

Extraia a V7, abra terminal na pasta e rode:

```bash
bash scripts/verify.sh
python3 scripts/prove_resilience_local.py
bash scripts/start_local.sh
```

No navegador: `http://127.0.0.1:8080/lab/`. Confira os dados sintéticos, escolha `alice`, tente alterar curso de `bob` e observe `403`; altere curso da própria Alice e observe `200`. Não use dados pessoais nem servidores reais. Ctrl+C para parar.

Depois, para validar Docker instalado no Fedora:

```bash
docker compose version
docker compose config --quiet
bash scripts/start_docker.sh
python3 scripts/collect_evidence.py
docker compose --profile observability up -d
```

Cheque `http://127.0.0.1:3000` (Grafana, senha de `.env`) e `http://127.0.0.1:9090` (Prometheus). **Depois faça teste controlado:** `docker compose stop api_a`, acesse a API pelo gateway, registre o resultado, `docker compose start api_a`. Entregue prints dos dashboards e logs *sem tokens*. Para parar: `bash scripts/stop_docker.sh` (preserva volumes).

Para validar o React original (necessita internet para dependências):

```bash
cd frontend
npm ci
npm run build
npm audit --audit-level=high
cd ..
```

**Importante:** o React/Firebase original depende do projeto/configurações de terceiros. NÃO aponte esse build a serviços remotos para testes de invasão. Use projeto próprio ou Firebase Emulator Suite, com autorização.

## 9. O que NÃO devemos fazer

- Não subir a sandbox na internet; há selector de `admin` sintético e seus tokens não são autenticação Firebase real.
- Não usar credenciais do ZIP original nem tentar validá-las em serviços reais; avisar dono sobre potencial vazamento e rotação.
- Não dizer que o sistema real tem SQL injection ativa no blueprint desregistrado.
- Não considerar 70 testes da sandbox como 70 exploits do original.
- Não migrar às pressas para Rails/Kubernetes/IA paga sacrificando os requisitos de maior peso.
- Não publicar os arquivos dos autores sem verificar direitos de redistribuição/licença ou autorização no edital. Prefira fork quando permitido e dê atribuição.

## 10. Decisões que precisam da sua aprovação (somente cruciais)

1. **Direito/escopo de teste:** você confirma que podemos testar uma cópia local do CourseSphere e eventualmente um projeto Firebase Emulator **próprio**, sem usar credenciais da conta original? **Recomendado SIM**.
2. **Repositório da entrega:** será fork privado/local primeiro e publicação somente após revisar licença/autorização e eliminar secrets? **Recomendado SIM**.
3. **Acesso às evidências Docker:** quando você executar no Fedora, enviar `docker compose ps`, saídas sanitizadas e screenshots de Grafana / Prometheus. Sem senhas ou tokens.

Nada disso bloqueia estudo de código e testes sintéticos locais, já executados.

## 11. Próxima rodada objetiva (P0 → P2)

- **P0 — primeira:** ambiente Firebase Emulator e Flask para coletar provas HTTP da origem sem terceiros; fechar cinco achados e três correções com testes.
- **P0 — segunda:** revisar `/users/create` client signup e regras Firebase em runtime; revisar taxas e proteção de sessão.
- **P1 — terceira:** rodar build React/npm audit, Bandit, Compose/Grafana/Nginx; reparar bugs encontrados e guardar artefatos.
- **P1 — quarta:** capturar provas de balanceamento `api_a` e `api_b`, repetir perda de instância no Nginx, documentar degradação.
- **P2 — última:** aprimorar interface, rodar scans locais autorizados, criar commits e relatório final (executivo + técnico), checklist público.

## 12. Mapa dos arquivos

- `README.md`: como rodar e o que é cada parte.
- `docs/RELATORIO_PENTEST_V7.md`: achados, severidades, evidências, causas e ressalvas.
- `scripts/evidence_engine.py`: produz provas automáticas `evidence/generated/ORIGIN_BEFORE_AFTER.json`.
- `audit/baseline/`: original de handlers frontend/backend e metadados **sanitizados** do arquivo de credencial.
- `tests/test_original_regression.py`: executa funções originais e corrigidas com stubs sintéticos.
- `tests/test_resilience_v7.py`: experimento de réplica local.
- `scripts/prove_resilience_local.py`: prova resiliência básica stdlib, não Nginx.
- `scripts/generate_sbom.py`: CycloneDX offline do package-lock.
- `scripts/check_secrets.py`: verifica arquivos sensíveis conhecidos (não substitui secret scanner completo).
- `backend/endpoints.py` e `frontend/src/api.ts`: alterações de produção que necessitam teste de integração.
- `dashboard/`, `backend/local_server.py`, `backend/demo_store.py`: sandbox totalmente independente.
- `ops/` e `compose.yaml`: Nginx, Prometheus e Grafana **configurados**.
- `.github/workflows/ci.yml`: pipeline escrito; só considerar executado quando GitHub registrar job verde.

## 13. Definição final de pronto

**Pronto para banca** somente quando há: 5 falhas reais comprovadas em escopo autorizado, 3 correções com provas antes/depois em runtime, 2 hardenings, logs/health/metrics/SLIs/SLOs, Compose com 2 réplicas e Nginx mostrando distribuição, relatório com prints/requests e README reproduzível, CI sem falhas críticas conhecidas e repositório com histórico organizado. Extras são diferenciais **depois** do aceite central.

**Conclusão:** estamos no caminho certo porque saímos da simulação solta e passamos a testar código original com rastreabilidade; mas ainda não é correto chamar o desafio de concluído sem a comprovação HTTP real em Flask/Firebase e infraestrutura Docker. Não precisamos inventar uma porcentagem de prontidão para enxergar claramente as pendências.
