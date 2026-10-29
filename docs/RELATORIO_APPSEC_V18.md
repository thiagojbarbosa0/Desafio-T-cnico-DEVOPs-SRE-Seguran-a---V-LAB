# CourseSphere — análise AppSec e correções (V17)

**Escopo autorizado:** snapshot do repositório CourseSphere fornecido pelo candidato; comparações executadas somente em loopback. A aplicação principal usa **Flask + Firebase Auth/Realtime Database + React/TypeScript + SQLite**. O laboratório local que implementa cursos/aulas é uma **extensão sintética**, não a origem das vulnerabilidades abaixo.

**Metodologia:** levantamento das rotas, revisão de autorização e entradas, comparação de código antes/depois, testes Python e HTTP local com Flask verdadeiro e Firebase simulado. O script de reprodução é `python3 -m integration.run_original_http_stubbed`; ele exige Flask/Flask-Cors. Para integração com autenticação e banco de dados reais *emulados* (nunca produção), usar `bash scripts/verify_official_emulators.sh`. Não foram feitas requisições ao ambiente dos autores nem testes com credenciais reais.

## Achados prioritários, ordenados pelo risco de negócio

### F01 — criação de conta através de função administrativa exposta (Alta, contextual)
- **Categoria:** controle de acesso quebrado / autenticação.
- **Raiz:** a rota `POST /users/create` no snapshot upstream invocava `Firebase.create_user()` por uma API administrativa antes de verificar identidade/permissão do chamador.
- **Reprodução controlada:** enviar `POST /users/create` com email/senha sintéticos, sem header de autenticação; comparar com a aplicação corrigida via `integration.test_original_http_stubbed.test_anonymous_privileged_signup`.
- **Antes/depois observado no Fedora V14.1:** HTTP `200 → 410` com Firebase falso, sem criar contas de produção.
- **Impacto potencial:** cadastros arbitrários e abuso de recursos Firebase se implantada dessa forma.
- **Correção:** desabilitar definitivamente a rota privilegiada e mover o cadastro para o SDK Firebase Auth do cliente, que aplica controles do provedor. A API Admin deixa de estar disponível ao público.
- **Limite:** resposta `200` simulada não prova que uma conta real foi criada ou que o ambiente upstream está exposto.

### F02 — consultas anônimas sem verificação da identidade (Média/Alta, contextual)
- **Categoria:** falha de autenticação / consumo não autorizado de recursos.
- **Raiz:** `POST /users/query` aceitava requisições sem exigir token Firebase.
- **Reprodução:** `test_unauthenticated_user_query` envia uma consulta sem credencial.
- **Antes/depois observado:** `200 → 401` (Firebase e QueryManager simulados).
- **Impacto:** uso indevido do recomendador; caso conectado a serviços pagos, custo/abuso de quota.
- **Correção:** o servidor exige Bearer e verifica o UID antes de consultar qualquer recurso. A V17 acrescenta quota distribuída por UID depois da autenticação para reduzir abuso por contas válidas.
- **Limite:** o upstream estava com o mecanismo de recomendação real parcialmente simulado; **não** alegar cobranças reais.

### F03 — token de sessão enviado na URL (Alta/Média, contextual)
- **Categoria:** gestão de sessão / exposição de segredo.
- **Raiz:** `GET /users/info?id_token=...` aceitava credenciais na query string, que pode aparecer em históricos e logs.
- **Reprodução:** `test_token_accepted_from_query_string` com token sintético; caso positivo `test_backend_happy_path_preserved` mostra o novo fluxo válido.
- **Antes/depois observado:** `200 → 401` para token na URL. Com `Authorization: Bearer`, a versão corrigida responde **200**, preservando a funcionalidade.
- **Impacto:** possível vazamento de credenciais de acesso através de intermediários.
- **Correção:** rejeitar parâmetros de token e autenticar somente por header; alterar as chamadas frontend correspondentes.
- **Limite:** não foi observado vazamento real em logs de produção.

### F05 — retorno de detalhes internos em erros (Média)
- **Categoria:** exposição de informações sensíveis.
- **Raiz:** respostas do upstream incorporavam `str(exception)` no corpo HTTP.
- **Reprodução:** `test_invalid_token_leaks_internal_detail` injeta erro sintético contendo `SYNTHETIC_INTERNAL_AUTH_DETAILS`.
- **Antes/depois:** o teste confirmou o marcador somente no corpo original; a versão corrigida retorna erro HTTP 401 sem conteúdo interno.
- **Impacto:** facilita reconhecimento da arquitetura, causas de falha e caminhos internos.
- **Correção:** mensagens de erro externas previsíveis e registro interno estruturado sem segredos.
- **Limite:** o marcador é deliberadamente fictício; não foram obtidos erros ou segredos dos autores.

### F06 — ausência de limites e validação homogênea de entradas (Média)
- **Categoria:** validação de entradas / disponibilidade.
- **Raiz:** campos e listas eram recebidos sem limites uniformes antes de operações de armazenamento/processamento.
- **Reprodução:** `test_unbounded_profile_input`, `test_unbounded_chat_messages` e `test_query_size_is_bounded`.
- **Antes/depois:** perfis grandes `200 → 400`; lotes de mensagens acima do limite `200 → 400`; consultas grandes `200 → 400`.
- **Impacto:** amplificação de processamento e dados malformados, potencial indisponibilidade em certos volumes.
- **Correção:** schemas e limites de tamanho, formatos, IDs e tipos no backend, antes da operação privilegiada.
- **Limite:** demonstra falta de controle; não comprova indisponibilidade real ou exaustão de recursos.

## Achados complementares, sem inflar o mínimo

- **F04 — CORS irrestrito:** política corrigida por allowlist; severidade dependente de como credenciais/cookies são usados. O header original permitia origem não confiável; o corrigido não.
- **F07 — `debug=True` no servidor original:** removido na versão derivada; a gravidade depende de como o servidor seria publicado.
- **F08 — campos de credenciais no snapshot original:** removidos da derivação; **não** foi comprovada validade da credencial. Proprietário deve verificar e, se necessário, revogar/rotacionar.
- **F09 — SQL concatenado:** módulo legado de rotas não estava registrado no servidor original; **não apresentar como injeção SQL comprovada em rota ativa**.

## Hardening da V17: rate limiting distribuído (diferencial)

O Flask principal agora aplica quota de **30 recomendações/minuto/UID** e **120 emissões de IDs/minuto/UID**. Implementação transacional em `backend/shared_quota.py` usando Firebase RTDB Admin em `server_security/rate_limits/<sha256(uid)>/{action}`. Os clientes Firebase não podem escrever nesse namespace, pois a regra raiz é deny-by-default. O limite é compartilhado por réplicas; usa janela fixa por UID/ação, sem acumular histórico infinito. Exceder resulta em `429`; erro no storage resulta em `503` (fail-closed).

**Evidências nesta sessão:** 14 testes offline, incluindo concorrência e falhas no armazenamento, com resultado aprovado. **Não comprovado ainda:** integração desse limite com transações reais do Firebase Emulator. O caso `test_20_rate_limit_shared_via_firebase_admin_transaction` foi adicionado, mas só pode ser aprovado após execução no Fedora ou CI.

Esse hardening é complementar, **não é uma sexta vulnerabilidade comprovada**. O limite por UID também não substitui proteção na borda para tráfego anônimo ou ataques distribuídos.

## Evidências e critérios de submissão

- **Fedora V14.1, 23/10/2026:** o usuário executou 15 testes HTTP com Flask real e Firebase simulado: `Ran 15 tests ... OK; validated=True`. A execução é **histórica** e deve ser repetida com as fontes V17 para o gate atual.
- **Nesta sessão V17:** testes unitários/HTTP da sandbox e teste Nginx nativo. Não confundir com execução Docker ou serviço Firebase real.
- **Ainda obrigatório:** confirmar os achados em escopo aceito pela banca, anexar o JSON atualizado `ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V13.json`, executar Firebase Emulator com 20 testes, React production build, Docker/Prometheus/Grafana e comprovação de duas réplicas. Uma revisão de autoria/licenciamento é necessária antes de publicar.

**Conclusão:** há evidência controlada de cinco classes de falhas nos handlers originais e de suas correções. Ainda não há base para declarar exploração em produção, comprovação completa das integrações nem aprovação garantida pela banca.


## Adendo V18 — quota de escrita de chats (defesa adicional, não achado upstream)

- **Código:** `backend/endpoints.py` aplica `Firebase.enforce_quota(uid, "chat_write")` após verificar a identidade e validar as mensagens, mas **antes** de gravar dados.
- **Armazenamento:** `backend/shared_quota.py`, chave transacional por UID e ação, 60 gravações/minuto.
- **Comportamento:** quando excede o limite retorna HTTP `429`; quando Firebase não aceita contabilização, retorna `503` sem gravar; requisições inválidas não são contabilizadas.
- **Prova offline executada:** `tests/test_v18_chat_write_quota.py`, incluindo 120 concorrentes, separação entre usuários e respostas de erro. Esse teste utiliza banco de dados sintético em memória, **não valida Firebase real**.
- **Prova integrada preparada, NÃO executada nesta sessão:** `test_20_rate_limit_shared_via_firebase_admin_transaction` testa ambas as ações (`recommendation` e `chat_write`) no Firebase Emulator. Continua sendo um cenário dentro do total de 20 testes da suíte.
- **Limitação:** limitar pelo UID não protege autenticação anônima nem evita ataques distribuídos de muitas identidades. Isso precisa de limitação na borda (Nginx/proxy) e regras de proteção complementares.
