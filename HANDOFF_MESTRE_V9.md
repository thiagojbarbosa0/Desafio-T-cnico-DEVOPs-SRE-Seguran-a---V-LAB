# HANDOFF MESTRE — CourseSphere V9 | Integração e validação técnica

**Escopo:** desafio V-Lab AppSec & SRE sobre o repositório fornecido `LambdaAK/CourseSphere`.
**Direção visual:** continuar com a interface clara, sóbria, tradicional de SaaS da V8. Sem neon, glow ou estética cyberpunk.
**Decisão técnica:** preservar Flask + React + Firebase do original; manter o laboratório sintético separado, sem alegar que ele representa falhas descobertas no original.

## 1. O objetivo original do edital

O desafio **não pede recriar o CourseSphere**, mas examinar uma aplicação web existente ou equivalente, encontrar **pelo menos 5 vulnerabilidades reais** em **2+ categorias**, reproduzi-las, corrigir **3+** de suas causas raízes, fazer **2+ hardenings**, implementar logs JSON, métricas/health, propor **2+ SLIs/SLOs**, containerizar frontend/backend, configurar balanceamento entre **2 réplicas**, demonstrar a distribuição e documentar os riscos de segurança e disponibilidade. Extras opcionais: STRIDE, isolamento, CI, testes, Kubernetes, nuvem, resiliência e Grafana.

**Prioridade da banca:** ALTA para qualidade das falhas/reprodução/correções; MÉDIA para relatório, hardening, balanceamento e riscos; BAIXA para scanner/histórico/qualidade da instrumentação. Não há pesos numéricos definidos no edital.

## 2. Estado real, sem maquiagem

| Área | Situação | Evidência | Ressalva |
|---|---|---|---|
| Código fonte original | Incorporado ao projeto derivado | `backend/`, `frontend/`, `audit/` | Diferencia-se do laboratório didático |
| Investigação inicial de falhas do original | Identificados 9 achados/observações | `docs/RELATORIO_PENTEST_V7.md` | 6 comportamentos reproduzidos em **funções isoladas**, não 6 explorações HTTP originais |
| Correções originais | Alterações feitas nos handlers e frontend | `backend/endpoints.py`, `frontend/src/` e testes | Falta executar o Flask com Firebase real **emulador** e coletar prova final |
| Laboratório sintético | Funcional | `backend/local_server.py`, `dashboard/` | Não confundir seus cursos/aulas com a plataforma original |
| Testes Python de V9 | **93 aprovados** | Executar `bash scripts/verify.sh` | Misturam unitários, regressão por stubs e HTTP do laboratório |
| Nginx de verdade | **COMPROVADO em execução nativa** | `evidence/generated/NGINX_LIVE_V9.json` | Monta a configuração do projeto, substituindo apenas os endereços de container |
| 2 réplicas e failover Nginx | **COMPROVADOS nativamente** | 20+20 requisições; após derrubar A, 8/8 via B | Ainda não é Docker |
| Firebase Emulator Suite | Código + suíte HTTP preparada | `firebase.json`, `backend/firebase.py`, `integration/test_official_emulators.py` | **NÃO EXECUTADA** neste ambiente (faltam pacotes, Firebase CLI e rede) |
| React/Vite original | Refatorado para Firebase local e rotas reais | `frontend/src/firebaseClient.ts`, `frontend/src/components/` | **BUILD NÃO VALIDADO**: npm offline falhou por dependência ausente |
| Docker Compose e Grafana | Configuração existente + verificador em V9 | `compose.yaml`, `scripts/verify_docker_stack.py` | **NÃO EXECUTADOS**: Docker indisponível nesta sessão |
| GitHub CI | Pipelines estendidos para Nginx e emuladores | `.github/workflows/ci.yml` | **EXECUÇÃO NO GITHUB NÃO COMPROVADA** |

## 3. O que mudou da V8 para a V9

1. **Validação real de Nginx:** `scripts/prove_nginx_native.py` lê `ops/nginx/gateway.conf`, adapta DNS/portas para o host, inicia duas instâncias locais, verifica Nginx com `nginx -t`, faz 40 pedidos, derruba uma instância, faz 8 pedidos e confirma bloqueio de `/metrics` e entrega do HTML. Tudo em loopback e com banco sintético.
2. **Firebase isolado:** `firebase.json`, regras RTDB por UID, credencial `owner` *somente no emulador*, uso obrigatório de `demo-...` e portas `127.0.0.1` para impedir contato com o Firebase da equipe original.
3. **Frontend original:** `firebaseClient.ts` centraliza o Firebase e conecta Auth/Database emuladores. O config não inclui mais a ID/API key pública do projeto dos autores; o navegador falha se não for configurado para projeto próprio ou demo.
4. **Chats:** `/chats` agora é uma rota Flask autenticada, lida exclusivamente por UID verificado; o `UserChats.tsx` não aponta mais a um URL fictício. Ouvinte de autenticação com cleanup.
5. **Suíte de integração original preparada:** `integration/test_official_emulators.py` cria 2 contas artificiais no Auth Emulator e faz requisições HTTP ao Flask com verificações de token, isolamento do perfil, chat e acesso anônimo ao RTDB. Só grava códigos/status, nunca tokens.
6. **Verificador operacional Docker:** `scripts/verify_docker_stack.py` checa Nginx, duas réplicas, métricas Prometheus, Grafana e (somente com `--failover`) a queda/recuperação de uma réplica.
7. **CI:** novos jobs para teste Nginx real e Firebase Emulator Suite em runner que instala as dependências.

## 4. Como você controla o projeto agora

**Fonte de verdade:** este handoff + `evidence/generated/` + resultados de CI. Não marcar uma funcionalidade como concluída sem **prova executada e guardada**.

**Status objetivo das três pendências solicitadas nesta rodada:**
- **Nginx nativo:** FEITO e COMPROVADO.
- **Flask + Firebase Emulator:** IMPLEMENTADO/PREPARADO, **EXECUÇÃO PENDENTE**.
- **Docker + Grafana:** VERIFICAÇÃO OPERACIONAL PREPARADA, **EXECUÇÃO PENDENTE**.

### Próxima atividade no Fedora — exatamente nesta ordem

Comece no diretório onde extraiu `CourseSphere_V9`:

**Etapa A — repetir o que já foi comprovado (só Python + Nginx):**
```bash
bash scripts/verify.sh
sudo dnf install -y nginx # se necessário
python3 scripts/prove_nginx_native.py
```
Leia `evidence/generated/NGINX_LIVE_V9.json`. Nenhum serviço externo.

**Etapa B — testar o Flask ORIGINAL com os emuladores Firebase (a primeira lacuna importante):**
```bash
sudo dnf install -y python3-pip python3-devel java-21-openjdk nodejs npm
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
bash scripts/verify_official_emulators.sh
```
O script executa os emuladores sem tocar em serviços reais. Precisa instalar/baixar `firebase-tools` e o jar do RTDB na primeira vez; a internet é necessária só para obter dependências. Os testes gravarão `evidence/generated/FLASK_FIREBASE_EMULATORS_V9.json` **se o teste chegar a executar**. Em caso de erro, preserve o log e não marque como validado. **Importante:** não coloque credenciais reais no arquivo `.env` nem reutilize as contas dos autores.

**Etapa C — React original (3 terminais separados):**
- Terminal 1: `npx --yes firebase-tools@15.34.0 emulators:start --project demo-coursesphere-vlab --only auth,database`
- Terminal 2 (com `.venv`): `bash scripts/start_official_flask.sh`
- Terminal 3: `cd frontend && cp .env.example .env.local && npm ci && npm run build && npm run dev -- --host 127.0.0.1`

Acesse `http://127.0.0.1:5173`, registre **usuários sintéticos** e teste perfil/chats. Os emuladores Auth/RTDB devem escutar SOMENTE em 127.0.0.1. Não use o Firebase de terceiros.

**Etapa D — Docker + Grafana:**
```bash
bash scripts/start_docker.sh
# Iniciar Prometheus e Grafana:
docker compose --profile observability up -d
python3 scripts/verify_docker_stack.py
# Teste destrutivo controlado: para e reinicia a réplica api_a
python3 scripts/verify_docker_stack.py --failover
```
Leia `evidence/runtime/DOCKER_STACK_V9.json`. O Compose atual é do **laboratório sintético** e não do Flask/Firebase original. Os resultados não validam a infraestrutura original.

**Etapa E — entrega ao V-Lab:** revisar achados no original com emuladores (HTTP reproduzível), obter provas antes/depois e commits separados; publicar apenas depois de resolver licenciamento e credenciais.

## 5. Critérios de aceite que faltam

- Pelo menos **5 falhas reais no original ou na aplicação equivalente autorizada**, com 2+ categorias, risco, request/response e passo reproduzível — pendente de validação end-to-end.
- Pelo menos **3 correções do original**, com evidência comparativa antes/depois HTTP e teste de regressão — parcial.
- Fluxos `signup -> login -> perfil -> chats` testados no React original + Flask + Firebase Emulator em conjunto — pendente.
- Docker Compose com dois backends, Nginx real, métricas Prometheus e dashboard Grafana testados no Fedora — pendente.
- Relatório final atualizado só com provas genuínas, instruções de recuperação e SLIs/SLOs medidos/propostos — parcial.
- Permissão de republicar o código derivado confirmada — pendente (o ZIP original não demonstrou licença de redistribuição expressa).
- Credencial detectada no ZIP original revogada/rotacionada pelo proprietário — requer contato com o responsável. Não reproduzir a credencial em relatório público.

## 6. Prioridade recomendada — não gastar tempo com extras antes

1. **P0** executar a suíte de emuladores no Fedora, consertar quaisquer falhas reais de integração e coletar evidência.
2. **P0** converter as evidências de função isolada em provas HTTP reais (e fechar 5/3 conforme edital).
3. **P1** validar Docker/Nginx/Grafana e o frontend React.
4. **P1** atualizar relatório com classificação, business impact, SLIs/SLOs, prints e comandos.
5. **P2** aprimorar Security Arena, Resilience Playground e visual — apenas se P0/P1 concluídos.

## 7. Riscos importantes

- Firebase no modo emulador aceita tokens não assinados de teste; por isso **nunca** habilitar `FIREBASE_AUTH_EMULATOR_HOST` ou `COURSESPHERE_USE_FIREBASE_EMULATORS=1` em produção.
- O RTDB Admin Emulator usa o token artificial `owner`; esse token **só é válido no emulador**, nunca em Firebase real, protegido por checagens de host `127.0.0.1` e projeto `demo-`.
- O repositório upstream implementa **recomendação de disciplinas**, não um CRUD completo de cursos/aulas. O laboratório é um componente separado e não comprova falhas da origem.
- A funcionalidade de recomendações no código upstream continua simulada. Não anunciar IA real sem uma implementação de fato.
- Nenhum script deve acessar o Firebase, OpenAI ou outros serviços externos dos autores, mesmo para testes benignos, sem permissão.
- Não confundir **93 testes Python passando** com **93 vulnerabilidades exploradas** nem atribuir porcentagem de aprovação.

## 8. Evidências desta sessão

- `evidence/generated/NGINX_LIVE_V9.json`: Nginx nativo **PASSOU**; distribuição 20/20, 8/8 com instância desligada.
- `evidence/generated/HTTP_GATEWAY_V8.json`: sete cenários HTTP do gateway Python local.
- `evidence/generated/ORIGIN_BEFORE_AFTER.json`: provas offline de handlers isolados.
- `evidence/generated/FLASK_FIREBASE_EMULATORS_V9.json`: **não existe até a suíte oficial passar**.
- `evidence/runtime/DOCKER_STACK_V9.json`: **não existe até o script com Docker ser executado**.
- `scripts/verify.sh`: **93 testes Python aprovados** nesta sessão.

**Resumo para o próximo responsável:** estamos no caminho certo por trabalhar com a aplicação verdadeira, mas a prioridade continua ser demonstrar os achados e as correções end-to-end. A V9 concretizou Nginx com execução real e deixou a integração Firebase/Docker instrumentada e aguardando execução, sem prometer validação inexistente.
