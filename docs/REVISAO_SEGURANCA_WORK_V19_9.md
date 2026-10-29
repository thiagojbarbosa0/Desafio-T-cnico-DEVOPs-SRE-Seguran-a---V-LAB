# Revisão atual — V19.9 Work sobre V19.8

Esta entrega não atribui problemas da derivação ao upstream. O snapshot original foi identificado pelo SHA-256 `1ba5268f5fcfddd9c87cb550e807a36d3eabf7ef91be97d829a6cca8b8659a2d`. Nenhuma credencial foi usada ou validada externamente.

| Achado upstream | Categoria | Prova atual | Limite / gravidade contextual |
|---|---|---|---|
| F03: token em URL | exposição de autenticação | 15 testes HTTP antes/depois; Bearer exigido na correção | Token sintético; não comprova vazamento em produção. Moderada, dependente de acesso a logs/histórico. |
| F04: segredo no snapshot | gestão de segredos | analisador sanitizado reexecutado contra o ZIP original | Presença confirmada; validade, privilégios e rotação desconhecidos. Gravidade externa indeterminada. |
| F05: detalhes internos em erros | divulgação de informação | HTTP local com exceções sintéticas, resposta genérica após correção | Não demonstra extração de segredo real. Baixa a moderada conforme conteúdo. |
| F06: entradas sem tipos/limites | validação e disponibilidade | HTTP antes/depois e suíte de limites | Ausência de validação confirmada; DoS não demonstrado. Gravidade depende de recursos consumidos. |
| P-PROFILE: resposta de sessão anterior aplicada ao perfil atual | isolamento de sessão no cliente | `node scripts/prove_profile_race_work.cjs`: fonte upstream byte a byte versus API atual | Mesmo cliente, troca de conta e requisição pendente. Firebase/fetch controlados; sem navegador real e sem leitura não autorizada no servidor. Moderada em dispositivo compartilhado. |

P-PROFILE: A inicia leitura do próprio perfil; B autentica e seu perfil é aplicado; a resposta atrasada de A substitui o estado de B no upstream. Na API atual, a geração da sessão e o cancelamento descartam a resposta de A. São causas distintas do transporte do token em URL: o teste mantém a sequência e os dados iguais, alterando somente a implementação avaliada. A fonte exata e os hashes estão em `audit/baseline/profile_api_*`; a prova em `PROFILE_RACE_WORK.json`. O callback original usa uma rota `/users/info` existente. Não contamos o comportamento de UserChats contra uma rota ausente no upstream como exploração ativa.

F01 (cadastro público) e F02 (consulta anônima) continuam condicionais à política do produto. Não são promovidos para completar uma contagem. Há agora cinco itens tecnicamente sustentados, mas isso não equivale a cinco explorações externas confirmadas: o critério formal de revisão permanece PENDENTE, sobretudo pelas limitações de F04, F06 e da prova de cliente.

Três causas raiz revalidadas: token em URL → Bearer; exceções divulgadas → erros genéricos; entradas irrestritas → tipos e limites. Isolamento de perfil já corrigido na base, agora com nova comparação upstream. Os novos reparos de logs INFO, cardinalidade de métodos e empacotamento são melhorias da derivação e não novos achados upstream.
