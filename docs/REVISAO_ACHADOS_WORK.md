# Revisão crítica dos achados upstream — Work

Escopo: snapshot fornecido; HTTP loopback, Flask verdadeiro, Firebase e QueryManager sintéticos. Nenhum teste em projetos dos autores. O requisito de cinco vulnerabilidades independentes continua pendente. A matriz não transforma comportamento de cadastro público em escalada de privilégio.

| Achado | Evidência atual | Força e condição de exploração |
|---|---|---|
| F01 cadastro administrativo público | HTTP 200 no baseline, 410 corrigido; chamada create_user sem autenticação | Condicional. Uso do SDK Admin não concede papel de administrador ao usuário criado. Cadastro público pode ser intencional. É preciso demonstrar bypass de política concreta (cadastro fechado, verificação, antifraude ou quota). Não alegar escalada de privilégios nem classificar Alta sem essa condição. |
| F02 recomendação anônima | HTTP 200 baseline, 401 corrigido; caminho sem token alcança QueryManager | Condicional. A implementação permite perfil opcional; confirmar requisito de acesso restrito. Serviços pagos e exaustão não foram demonstrados. Sobrepõe-se a F06 quanto a consumo de recursos; não contar duas vezes o mesmo impacto. |
| F03 credencial na URL | HTTP 200 baseline, 401 corrigido; Bearer válido continua 200 | Comportamento confirmado. O teste usa marcador sintético. O access log do Werkzeug durante a reprodução inclui a query: demonstra o canal local de exposição, não vazamento de token real. A rejeição da URL protege o fluxo válido, mas não elimina o registro de um cliente que ainda envie tokens indevidamente. Proxies e access logs precisam de política própria. |
| F05 detalhes internos no erro | Exceção sintética com marcador aparece apenas na resposta baseline | Comportamento confirmado. Demonstra fluxo de exposição, não obtenção de segredo real. A severidade depende do conteúdo da exceção em operação. As mensagens genéricas corrigidas preservam a fronteira externa. |
| F06 entrada sem limites consistentes | Perfis, lotes de mensagens e consultas aceitos no baseline e rejeitados após validação | Falta de limite confirmada. Não comprova DoS nem custo financeiro. Separar integridade (tipos/conteúdo) de disponibilidade; não inferir indisponibilidade a partir de um 200. |

Correções de causa raiz verificadas em HTTP: (1) retirar autenticação da URL e usar Bearer validado; (2) impedir detalhes internos nas respostas; (3) validar entradas e limites antes de acessar serviços privilegiados. Bloqueios de cadastro e consultas anônimas também estão cobertos, com as ressalvas acima.

D01 é defeito da derivação V18: regras RTDB permissivas. Não conta no mínimo upstream; execução oficial do emulador permanece requisito separado.

D02 (Work): exceção HTTP 413 engolida por except Exception nas rotas /users/query, /hash e /chats/<chat_id>/messages. Reprodução real retornou 500; após preservar HTTPException, as quatro rotas testadas retornam 413 com JSON genérico e no-store. Não conta como vulnerabilidade upstream nem como sexto achado. Logs antes/depois: evidence/generated/WORK_BODY_LIMIT_{BEFORE,AFTER}.log.

Próximo passo para o mínimo: confirmar as políticas que tornam F01/F02 violações ou identificar outros achados independentes no snapshot. Não usar SQL interpolado de blueprint inativo como SQLi explorável. Não usar debug=True sem demonstrar o modo de execução. Direitos de redistribuição e eventual rotação de credencial exigem confirmação do responsável.
