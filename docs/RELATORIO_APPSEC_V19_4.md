# Relatório AppSec V19.4 — situação auditável

**Objeto:** `LambdaAK/CourseSphere`, código derivado fornecido pelo usuário; Python Flask, React/TypeScript, Firebase. **Teste autorizado e sintético**: não houve varredura contra serviço de terceiros.

## Escopo e metodologia

Comparação controlada de código-base original arquivado com o derivado corrigido; testes de handlers com adaptadores sintéticos; validações HTTP reais históricas do Flask; teste Nginx local nesta versão; regressões de autorização, limitação e não exposição de dados. Não foi executado pentest remoto, Firebase Emulator nem Docker nesta rodada. As capturas e resultados associados a versões antigas podem perder validade após alterações.

## Achados priorizados do upstream (não inflar quantidade)

| Identificador | Categoria | Evidência e impacto | Condição/severidade |
|---|---|---|---|
| F01 | Cadastro privilegiado exposto | A rota original usava Firebase Admin para registrar usuários sem autenticação; 200 antes, 410 depois | **Condicional**: cadastro aberto pode ser intencional; não alegar escalada de papéis sem prova |
| F02 | Recomendação anônima | A consulta chegava a `QueryManager` sem sessão; 200 antes, 401 depois | **Condicional**: requisito de autenticação precisa de confirmação; não deduzir custo/DoS |
| F03 | Token na query string | 200 antes, 401 após correção; risco de token em histórico e logs | Confirmado no caminho local sintético; não houve token real exposto |
| F05 | Detalhes internos em erros | Texto de exceção sintética vazava antes; depois apenas erro genérico | Confirmado como comportamento; impacto depende do conteúdo do erro real |
| F06 | Entradas sem limites coerentes | Perfil, consulta e lote de mensagens aceitos sem limite anterior; 400/413 após correção | Confirmado no comportamento; **não** afirmar DoS real sem teste de disponibilidade |

**Três correções com causa raiz:** credenciais apenas no Bearer (não na URL), fronteira de erros sem detalhes internos e validação de tipos/tamanhos no backend antes das chamadas privilegiadas. Corroboração e condições detalhadas em `docs/REVISAO_ACHADOS_WORK.md`.

## Mudanças V19.4 (não são novos achados upstream)

- Limitação de alterações de perfil e exclusões de conversa por transação RTDB compartilhada; 429 por excesso, 503 por indisponibilidade do limitador. Elimina bypass entre réplicas nessas mutações, **desde que** a aplicação use as regras Firebase restritivas da derivação.
- Auditoria de eventos de autenticação com rótulos seguros e sem identificação de usuário; permite monitorar falhas sem gerar material sensível em logs.
- CI corrigido: job de Flask e Nginx anteriormente executava dois comandos dobrados em uma linha; agora executa ambos separadamente, permitindo evidência reproduzível.

## Estado das evidências V19.4

- **262/262 testes Python offline** aprovados; 22 regressões novas.
- **Nginx real**: 40 requisições (20/20), failover 8/8, `/metrics` 403; proteção contra query string no gateway e 55 registros JSON conferidos sem query.
- **Três testes Node de sessão** aprovados, sem build React completo nesta rodada.
- **Sete testes Flask WSGI** preparados, mas as dependências Flask não estão instaladas aqui. Runner falhou corretamente (7 skips, `validated=false`), sem gerar falso PASS.
- **Firebase Emulator (23 casos)** e Docker/Prometheus/Grafana não executados nesta rodada.

## Prioridades da banca

P0: cinco achados independentes na aplicação original em pelo menos duas categorias; F01/F02 ainda dependem da política do produto ou substituição por problemas confirmados. P0: testar ao menos três correções antes/depois com provas recentes e classificar severidade/impacto de forma conservadora.

P1: comprovar execução integrada do Flask/Firebase, React build e duas réplicas; SLI/SLO com dashboard; CI/SAST/SCA realmente executados. P2: polimento visual SaaS sóbrio, documentação e checklist da submissão.

## Observações jurídicas e operacionais

A versão derivada exclui o arquivo de credenciais encontrado no snapshot original, mas **o responsável por eventuais segredos expostos upstream deve ser avisado para revogar/rotacionar**. A licença/direitos de redistribuição do repositório original precisam ser verificados antes de tornar a derivação pública. Escopo e impacto deste relatório não constituem autorização para testar sistemas públicos.
