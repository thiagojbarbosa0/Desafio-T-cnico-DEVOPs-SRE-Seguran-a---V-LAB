# ADR V19.3 — URLs de autenticação, logs Nginx e evidências

**Status:** Aceito em ambiente local; implantação Docker ainda precisa de teste.

## Contexto

O Flask corrigido recusa `id_token` pela query, mas proxies costumam registrar o pedido **antes** de a aplicação responder. Se o acesso Nginx incluir `$request` ou `$request_uri`, a URL inteira pode conter um token de um cliente antigo, mesmo que a aplicação devolva 401. Na versão anterior, `gateway.conf` confiava no formato de log herdado da imagem; isso não garante privacidade.

## Decisão

- Montar `ops/nginx/nginx.conf` no contêiner; o formato `coursesphere_json` registra `$uri` **sem** query string, método, status, ID de requisição, upstream e duração. Não registrar `$args`, `$request_uri`, Referer, Authorization ou `$request`.
- No gateway, retornar 401 para quatro chaves usuais de credenciais por query. Na API `/api/`, retornar 400 para **toda** query string (inclusive parâmetros codificados). O backend Flask oficial não necessita de parâmetros de query para suas rotas legítimas.
- Preservar logs estruturados de observabilidade sem incluir dados pessoais ou tokens.
- Testar o gateway com marcador sintético, inspecionar o arquivo real de log e confirmar que o marcador não é emitido.

## Consequências e limites

- O controle de qualquer query string é deliberadamente restritivo e impedirá filtros/paginação HTTP futuros até adoção de allowlist explícita, auditada e testada.
- O Nginx pode registrar o **caminho** solicitado, incluindo identificadores no path. Projetos com IDs pessoais em rotas devem revisar política de redaction adicional.
- Registros e históricos de serviços *antes* do gateway (CDN/host/proxy externo) não são cobertos.
- A prova nativa Nginx passou. O `nginx.conf` da imagem foi verificado sintaticamente no host, mas o serviço Docker completo não foi iniciado neste ambiente.
- Tokens reais não são utilizados nas provas. A proteção do original sob Nginx real com Firebase simulado continua pendente de nova execução após essa mudança.
