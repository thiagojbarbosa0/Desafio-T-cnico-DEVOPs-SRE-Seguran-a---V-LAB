# Revisão priorizada do CourseSphere original — V16

**Escopo**: código original disponibilizado pelo usuário (`LambdaAK/CourseSphere`) versus handlers corrigidos no backend Flask. **Autorização**: execução local, sem tentativas contra sistemas dos autores, sem credenciais de terceiros. Impactos abaixo são riscos potenciais, não incidentes confirmados em produção.

| ID | Evidência do código original | Categoria | Risco para o negócio | Correção | Severidade preliminar |
|---|---|---|---|---|---|
| F01 | `POST /users/create` invoca API Firebase Admin anonimamente | Controle de acesso/autenticação | Provisionamento indevido de contas; abuso de recursos | Bloqueada (410); cadastro com SDK cliente | Alta, condicionada à implantação |
| F02 | `POST /users/query` originalmente não verifica Bearer | Autenticação | Abuso de consultas ou quota | Exige token e UID verificado | Média |
| F03 | `GET /users/info` recebia `id_token` pela query string | Gestão de sessão/exposição | Token em logs, histórico e serviços intermediários | `Authorization: Bearer`, rejeição explícita de tokens na URL | Alta/Média conforme ambiente |
| F05 | Erros internos retornavam `str(e)` | Exposição de informação | Detalhes de implementações e infraestrutura em respostas | Mensagens controladas | Média |
| F06 | Perfis, queries e mensagens sem limites homogêneos | Falha de validação / disponibilidade | Dados inválidos, custo e processamento não limitado | Validação estrita de tamanho, formato e conteúdo | Média |

**F04** — CORS amplo, corrigido por allowlist (risco contextual); **F07** — debug habilitado no `app.run` original (impacto depende da implantação); **F08** — campos de credenciais expostos em arquivo upstream (validez desconhecida; arquivo excluído da derivação, cabe ao dono rotacionar). **F09** — SQL interpolado no blueprint legado desativado: **não afirmar exploração de rota ativa**.

## Reprodução controlada

A suíte `integration.run_original_http_stubbed` executa endpoints originais e corrigidos em Flask real, com serviços Firebase e recomendações **simulados**. Na V14.1, o usuário registrou `Ran 15 tests ... OK ... validated=True` no Fedora. A matriz compara, entre outros, `200→410` para a rota privilegiada, `200→401` para consulta anônima, `200→401` para token na URL e `200→400` para entradas desproporcionais. Esses pares são comportamentos observados **nesses casos específicos**, não provas de impacto em ambiente remoto. Consulte o JSON gerado pelo runner atual para hashes SHA-256 e resultados completos.

**Três correções centrais**: F01 resolve a exposição da capacidade administrativa; F02 impõe verificação de identidade na fronteira HTTP; F03 remove o transporte inseguro do token. Testes positivos confirmam que a leitura autenticada ainda é aceita quando a credencial é enviada corretamente. É necessário registrar a execução integral da V16 e revisão manual do relatório para fechar formalmente as prioridades altas da banca.

## Prioridades pendentes

1. Gerar evidências HTTP **da fonte atual**, com hashes completos, e executar Firebase Auth/RTDB Emulator.
2. Compilar a versão React com `npm ci` + `npm run build` e verificar as funções originais, incluindo salvar o perfil.
3. Executar Compose + Nginx + duas réplicas + Grafana/Prometheus, arquivando captura ou JSON sem segredos.
4. Consolidar 5 achados distintos com reprodução e impacto; confirmar 3 correções de causa raiz; decidir o uso aceitável da aplicação recomendadora no lugar do CRUD genérico.
5. Confirmar direitos de redistribuição e rotação de qualquer segredo eventualmente exposto no upstream com os responsáveis.

Uma pontuação CVSS exata requer vetor e condições verificadas; não foi inventada nesta versão.
