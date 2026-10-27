# Modelo de ameaças — RTDB e API Flask (V19)

## Dados e fronteiras de confiança

**Ator externo:** usuário com credencial válida ou inválida. **Cliente React:** código executado no navegador (não confiável). **Firebase Authentication:** emite ID tokens. **Flask:** verifica token, autorização por UID, valida entradas e aplica quotas. **Firebase Realtime Database:** guarda perfis, chats e contadores privilegiados. **Firebase Admin:** credencial de servidor com permissão de ignorar regras de cliente; deve permanecer somente no servidor.

Fluxo esperado: `navegador → Authorization: Bearer → Flask → validação/autorização/quota → Firebase Admin → RTDB`.

Fluxo perigoso identificado nas regras V18: `navegador autenticado → Firebase RTDB /users/<uid> → gravação direta`. Essa segunda via contornaria a quota `chat_write` e validações de payload impostas pelo Flask, pois o cliente tinha `.write=true` para seu UID.

## Controles implementados

- `.read` restrita ao UID autenticado; leitura de outro UID negada.
- `.write` negada a todos os clientes, inclusive ao próprio UID, sem exceções aninhadas.
- gravações server-side passam pelos endpoints com validação e quota compartilhada em transações RTDB.
- quota do servidor está em `server_security`, sem regra de leitura ou escrita do cliente.
- emuladores exigem projeto `demo-` e execução em loopback; sem chave administrativa do upstream.

## Validação e risco residual

**Já verificado:** análise de configuração, contratos offline e suite Python local. **Ainda não verificado:** regras em execução no Firebase Emulator, permissão real do token do cliente, build React e integração React/Flask/RTDB. O caso 21 deve comprovar **uma leitura permitida** antes de considerar negação de escrita prova de segurança; caso contrário, um token inválido poderia criar falso positivo.

Riscos residuais: proteção por UID não detém ataques com muitas contas; evitar autenticação anônima aberta em produção; Firebase Admin continua altamente privilegiado; conta de serviço e chaves nunca devem ser incluídas no frontend, relatório ou repositório; revisar logs e gestão de segredos antes de publicar.

**Proveniência:** a brecha de escrita direta foi observada nas regras **da derivação V18**. Não há prova de que essas mesmas regras existiam no upstream ou de que um usuário tenha efetivamente as explorado.
