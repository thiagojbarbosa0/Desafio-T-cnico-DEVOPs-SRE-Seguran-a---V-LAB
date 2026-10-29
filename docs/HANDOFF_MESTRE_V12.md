# CourseSphere V12 — HANDOFF MESTRE

**Data da revisão:** 23/10/2026  
**Base técnica:** ZIP do projeto original `LambdaAK/CourseSphere` enviado pelo usuário.  
**Objetivo:** demonstrar competência em segurança de aplicações (AppSec) e confiabilidade (SRE), **corrigindo e instrumentando o CourseSphere original** e apresentando relatório reprodutível. Não estamos criando uma plataforma totalmente nova para substituí-lo.

## 1. O que o V-Lab pediu — sem exageros

O desafio pede: (1) encontrar no mínimo **cinco vulnerabilidades reais** em duas ou mais categorias; (2) **corrigir três** com causa raiz e commits claros; (3) duas melhorias adicionais de hardening; (4) logs estruturados, métricas, **dois SLIs com SLOs**; (5) Dockerfile para front/back e Compose com Nginx balanceando duas instâncias; (6) relatório de pentest + confiabilidade; (7) preferencialmente SAST/SCA. Os adicionais opcionais incluem threat modeling, ambiente isolado, CI, testes de autorização, Kubernetes, nuvem, arquitetura resiliente e dashboard Grafana.

O enunciado dá **prioridade alta à validade dos achados, reprodutibilidade e correção da causa raiz**, média a documentação/hardening/balanceamento, baixa a ferramentas/commits/observabilidade. **Não atribui pesos percentuais nem promete aprovação**. Devemos priorizar evidências de segurança, não brilho visual nem quantidade de serviços.

## 2. O CourseSphere de verdade

- Frontend: React + TypeScript + Vite e Firebase SDK.
- Backend: Flask/Python e Firebase Admin; SQLite no módulo legado de disciplinas.
- Produto original: recomendações de disciplinas universitárias; o próprio mecanismo de recomendação contém implementação simulada/incompleta.
- Não há no upstream o CRUD completo de cursos/aulas como no exemplo do desafio. Adicionamos **separadamente** um laboratório local de cursos/aulas para testar permissões, sem apresentar isso como falhas do original.
- **Evitar migrar para Rails só por aparecer na vaga**: o edital permite outras stacks, e a arquitetura existente é a fonte legítima para auditoria.

## 3. Decisões aprovadas até aqui

- Continuar usando o CourseSphere original como base; não substituir o upstream pelo laboratório.
- Custo zero, preferência por tudo local, sem usar credenciais de autores nem IA paga.
- Interface visual de produto SaaS convencional: cores sóbrias, tipografia legível, sem neon/glow/estética futurista.
- O usuário recebe autonomia para decidir mudanças cruciais de arquitetura, deploy público e custos.
- Marcar cada avanço como **implementado**, **testado**, **configurado** ou **pendente**, nunca confundir essas classificações.

## 4. O que construímos antes da V12

- Correções nos endpoints Flask: bloqueio do registro administrativo anônimo, Bearer obrigatório, tokens fora da URL, respostas genéricas para exceções, validação de perfil/chat/query, CORS delimitado, headers e debug desativado.
- Frontend: arranjos no SDK Firebase, cadastro do usuário pelo SDK cliente, correções de ID/contrato no chat.
- Laboratório isolado, de dados sintéticos, com autenticação temporária local, CRUD de cursos/aulas, autorização por proprietário, logs JSON e métricas, interface convencional.
- Nginx nativo executado com duas réplicas sintéticas; testes anteriores e V12 demonstraram distribuição de 40 solicitações e sobrevivência após falha.
- Arquivos Compose, Prometheus/Grafana, runbook, modelagem STRIDE, CI, scripts de evidências e SBOM.
- Testes offline passaram nas versões anteriores. **Esses testes não são um pentest end-to-end do original.**

## 5. O que entrou especificamente na V12

1. `integration/test_original_http_stubbed.py`: **13 cenários HTTP previstos**, incluindo token no corpo, comportamento de `/hash`/DELETE sem autenticação e limite de tamanho da consulta.
2. `integration/run_original_http_stubbed.py`: runner estrito (13 casos, nenhum skip) com hashes SHA-256 dos três arquivos usados na prova.
3. `integration/test_official_emulators.py`: **19 cenários previstos**. Corrigimos dependência incidental da ordem dos testes; cada caso prepara sua própria fixture quando necessário.
4. `backend/security_core.py`: remove a coerção implícita de `messageID` numérico e `timestamp` objeto em mensagens recebidas.
5. `tests/test_security_core.py` e `tests/test_release_gate_v12.py`: regressão adicional de tipo e veracidade das evidências.
6. `scripts/release_gate_v12.py` e `scripts/verify_v12.sh`: gate de oito grupos com contagens e versões exatas, sem declarar sucessos na ausência de execução; também exige hashes de código/harness das provas Firebase.
7. Atualização do relatório e do plano de execução para evitar ambiguidades de escopo e de terminologia.

## 6. O que realmente foi executado NESTA rodada

- `bash scripts/verify_v12.sh`: **130 testes Python offline passaram**, incluindo gateway HTTP sintético e validações estáticas; o `node` validou a sintaxe de arquivos TS/TSX, o que **não** substitui `npm run build`.
- Nginx nativo real usando `ops/nginx/gateway.conf` com duas instâncias Python locais: **20/20 solicitações distribuídas e 8/8 respostas corretas após encerrar a primeira instância**, com restrição a `/metrics`. Os números e escopo estão no JSON, e não representam Docker/Firebase.
- Testes HTTP de Flask com Firebase falso: **NÃO executados** por indisponibilidade de Flask/Flask-Cors neste runtime (instalação indisponível sem rede).
- Firebase Emulator, `npm ci`/build React e Docker/Prometheus/Grafana: **NÃO executados**; dependem de ferramentas ausentes e/ou download de dependências.
- **Critérios de aceite: 2/8 comprovados.** Não é porcentagem concluída do projeto, nota nem chance de seleção.

## 7. Como assumir o controle no Fedora

Extraia `CourseSphere_V12_APPSEC_SRE_EVIDENCIAS.zip`, entre na pasta `CourseSphere_V12` e comece por:

```bash
bash scripts/verify_v12.sh
```

Depois, se houver rede para instalar dependências e você quiser validar as peças que mais impactam a banca:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install 'Flask>=3,<4' 'Flask-Cors>=4,<6'
python3 -m integration.run_original_http_stubbed
python3 scripts/release_gate_v12.py
```

Para testar Firebase Emulator (precisa Java, Node/Firebase CLI e libs backend):

```bash
pip install -r backend/requirements.txt
bash scripts/verify_official_emulators.sh
python3 scripts/release_gate_v12.py
```

Para a aplicação React original:

```bash
bash scripts/verify_frontend_build_v10.sh
python3 scripts/release_gate_v12.py
```

Para os contêineres, **não confundir com Flask original**: `bash scripts/start_docker.sh` inicia a sandbox local, e `docker compose --profile observability up -d` ativa Prometheus/Grafana. `python3 scripts/verify_docker_stack.py --failover` testa as réplicas e reinicia a derrubada. Rode tudo somente em ambiente de testes local.

**Importante:** qualquer execução de Firebase deve usar o projeto `demo-coursesphere-vlab`, emuladores em loopback e dados sintéticos. Nunca autorize o runtime a usar o Firebase real dos autores.

## 8. Controle e quadro de pendências

| Prioridade | Tarefa | Condição de pronto | Situação |
| --- | --- | --- | --- |
| **P0** | Provas Flask HTTP original/patch com 13 cenários | Runner `validated=true`, sem erros/skips; hashes conferem | Preparado, não executado |
| **P0** | Cinco achados ativos + três correções de causa raiz | Casos independentes, impacto e documentação reproduzíveis | Revisão estática e testes isolados; aprovação final pendente |
| **P0** | Firebase Emulator com autorização Alice/Bob | 19 testes integrados, status real e logs | Preparado, não executado |
| **P1** | Build completo do React | `npm ci` + `npm run build` sem erros | Pendente |
| **P1** | Docker + Grafana + falha de réplica | Duas instâncias, dashboard, métricas e recuperação com prints/logs | Configurado, não executado |
| **P1** | Atualizar relatório executivo e técnico | Evidências rastreáveis + severidades justificadas | Rascunho V12, falta E3/E4 |
| **P1** | Licença e exposição de credencial upstream | Autorizações de publicação e confirmação de rotação | Depende de terceiros |
| P2 | CI/CD em GitHub | Jobs executados no GitHub com artifacts | Configurado, não executado |
| P2 | Extras (K8s, chaos, SBOM, threat model) | Só marcar recursos que tenham prova em execução | Parcial; não bloquear P0 |

## 9. Questões que precisam da sua decisão

1. **Publicação do derivado:** confirmar se existe licença/permissão do upstream para publicar o código integral modificado; se não, preferir patches, diffs, relatórios e scripts próprios.
2. **Identidade do repositório:** GitHub pessoal ou organização; estrutura de commits para contar a história de cada correção. O ZIP não substitui histórico Git real.
3. **Ambiente Fedora:** confirmar Docker, Node, Java, acesso à internet e recursos de hardware, para executar o pacote de integração sem pagar serviços.
4. **Escopo funcional:** não adicionar CRUD ao Flask original se a banca aceitar o escopo de recomendação de disciplinas; a extensão de cursos/aulas pode seguir como laboratório separado.

## 10. Riscos honestos

- O repositório original não tem funcionalidades idênticas às exemplificadas pelo edital. Validar compatibilidade com o processo seletivo.
- F08: há metadados indicando credencial em pacote upstream; **remoção não implica revogação**. Não redistribuir valores.
- F09 SQL legado está em blueprint inativo; **não contar como exploração ativa**.
- Configuração de duas réplicas com SQLite compartilhado é apropriada ao laboratório, mas não a banco distribuído de produção.
- Não usar percentuais arbitrários como previsão de aprovação; os oito gates não têm o mesmo peso do edital.

## 11. Ponto de retomada

1. Executar `bash scripts/verify_v12.sh`, compartilhar apenas o resultado sem secrets.
2. Instalar Flask/Flask-Cors e executar o harness HTTP de 13 cenários; corrigir falhas específicas, se houver.
3. Rodar Firebase Emulator e depois React e Docker; coletar evidências verdadeiras.
4. Fechar relatório com pelo menos cinco falhas ativas e três correções; publicar apenas após verificar direitos e segredos.

**Conclusão:** V12 avança no que interessa à banca: cobertura, consistência de input e prova rigorosa. A próxima prioridade continua sendo **execução real e coleta das evidências de AppSec**, não novos efeitos visuais.
