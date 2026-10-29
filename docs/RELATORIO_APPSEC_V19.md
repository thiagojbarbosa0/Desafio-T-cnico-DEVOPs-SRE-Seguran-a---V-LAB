# CourseSphere V19 — relatório complementar AppSec

Leia `docs/RELATORIO_APPSEC_V18.md` para os cinco achados priorizados **no código upstream** (F01, F02, F03, F05, F06) e suas provas de handlers. Esses achados e limites de verificação **não foram substituídos** na V19.

## D01 — bypass da camada Flask por regras permissivas do Firebase na V18

- **Origem:** falha encontrada na versão derivada V18, não demonstrada no repositório upstream.
- **Severidade proposta:** Alta no cenário em que o Firebase RTDB fosse exposto a clientes com as regras V18 ativas; a gravidade real depende do projeto implantado.
- **Causa raiz:** a regra `users/$uid/.write` era `auth != null && auth.uid === $uid`, dando ao cliente direito de escrever qualquer filho de seu UID. O servidor, por outro lado, impunha `validate_profile`, `validate_messages` e `enforce_quota` antes de gravar. Um cliente poderia contornar toda essa lógica e fazer escrita direta via RTDB SDK/REST.
- **Impacto potencial:** dados inválidos, bypass de quotas, perda de integridade de perfis e chats e maior exposição a abuso de recursos.
- **Correção:** manter leitura autorizada de dados próprios, proibir escrita de todos os clientes, exigir gravação exclusiva pela API Flask autenticada com Firebase Admin. Não basta limitar apenas `server_security`, porque os dados em `users` também precisavam de proteção.
- **Evidência existente:** diff da regra + testes estáticos e comportamentais offline.
- **Evidência ainda pendente:** no Firebase Emulator real, um usuário sintético lê seu perfil, não lê o de outro usuário, não grava diretamente e ainda consegue gravar pelo Flask. `test_21_rtdb_client_cannot_bypass_flask_validation_and_quota`.
- **Limitações:** não testei regras em projetos reais e não enviei requisições a serviços dos autores. Uma regra vulnerável num arquivo não prova que estava publicada em produção.

## Avanço na confiabilidade

A V19 prepara um experimento controlado de duas **réplicas das rotas Flask originais corrigidas**, atrás do Nginx, com APIs externas simuladas. A execução em GitHub Actions/Fedora precisa validar a divisão das solicitações, autenticação por bearer e continuidade após falha de uma réplica. Mesmo aprovado, esse experimento **não comprova** que Firebase, React e Docker funcionam juntos — há gates separados para isso.

## Conclusão sobre o edital

O diferencial D01 é uma melhoria importante de engenharia, mas **não deve ser contado como um sexto achado original**. O sucesso dos oito critérios ponderados ainda depende de evidências integradas atuais e de revisão técnica dos cinco achados upstream. A implementação encontra-se estimada em 69%; o aceite ponderado atual depende da execução do gate e não representa chance de aprovação.
