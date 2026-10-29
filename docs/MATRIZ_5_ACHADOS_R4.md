# CourseSphere — cinco achados candidatos para revisão da banca (R4)

Não é uma certificação de pentest externo. Análise ancorada no snapshot original preservado em `audit/baseline` e na revisão `docs/REVISAO_SEGURANCA_WORK_V19_9.md`, mantendo as limitações documentadas. Nenhuma credencial externa foi usada.

| Achado upstream | Fronteira e causa | Reprodução e impacto observado | Correção e evidência | Limite de alegação |
|---|---|---|---|---|
| **F03 — token na URL** | Autenticação HTTP: endpoint originalmente aceitava `id_token` da query string | HTTP loopback antes 200/depois 401 com token **sintético**; URL pode alcançar histórico, logs e ferramentas intermediárias | Bearer no `Authorization`; `integration.run_original_http_stubbed`, proteção do gateway | Não provado vazamento de token real em ambiente externo; impacto depende do fluxo e logs |
| **F04-SNAPSHOT — material com formato de segredo** | Distribuição do repositório original sem higienização completa | Arquivo suspeito no snapshot, verificação **sanitizada**; material não é distribuído nem usado | Excluir da derivação; proprietário deve confirmar revogação/rotação | Existência NÃO prova credencial válida, acesso à conta nem exfiltração |
| **F05 — mensagem de exceção interna** | Tratamento de erros expunha `str(exception)` à resposta | Flask HTTP local, exceção sintética aparece antes e não aparece depois | Mensagens genéricas + logging restrito; `integration.run_original_http_stubbed` | Não foi demonstrada extração de segredo real; severidade contextual |
| **F06 — validação e limites heterogêneos** | Falta de limites em perfis/consultas/mensagens | Testes HTTP locais mostram entradas excessivas antes aceitas e depois 400 | Validação de tipos e comprimentos, teto de corpo, quotas privadas | Não foi demonstrado DoS real nem seus custos; não atribuir severidade crítica sem medição |
| **P-PROFILE — corrida de sessão no frontend** | Resultado da requisição A podia alterar estado de B após troca de login | Comparação controlada do código original com cliente corrigido; A atrasado substituía perfil em estado da interface | Guarda de geração da sessão, descarte e abort em troca/logout; `node scripts/prove_profile_race_work.cjs` | Falha do estado **no mesmo cliente**; não prova leitura cross-tenant no banco, nem exploração real em navegador |

**Atenção ao identificador F04:** documentos antigos chamam *CORS permissivo* de F04 e outros chamam *arquivo de credencial* de F04. Para a submissão, padronizar identificadores antes de listar “cinco independentes”. É incorreto somar ambiguidades ou contar o mesmo defeito duas vezes.

**Três correções de causa raiz, não só filtros:** (1) autorização no servidor em vez de token na query; (2) normalização de falhas externas sem valores internos; (3) validação/tamanho/quotas com negação por padrão. As provas HTTP usam Flask real com Firebase sintético e não equivalem a pentest remoto.

**Status formal:** REVISÃO HUMANA PENDENTE. As cinco linhas têm evidências controladas e ressalvas. P-PROFILE requer prova em navegador se a banca exigir exploração dinâmica; F04-SNAPSHOT requer contato reservado com o proprietário; F06 demanda carga controlada para quantificar disponibilidade. F01/F02 permanecem dependentes da política de negócio. Falhas da derivação R2/R3/R4 não são contadas como upstream.
