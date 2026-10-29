# Changelog V14 (desde V13)

- Backend original: rejeição explícita de `id_token`, `access_token`, `auth_token` e `api_key` em query string, inclusive quando há header Bearer válido; resposta JSON padronizada para payload 413.
- `validate_messages`: impede IDs duplicados no mesmo lote, bloqueia tipos de remetente desconhecidos sem quebrar compatibilidade legada `human`.
- Firebase Emulator: teste 16 atualizado para exigir rejeição de token na URL mesmo com bearer válido.
- Observabilidade/Infra: corrigido `verify_docker_stack.py` para retornar **erro** quando o restart da réplica falha no cleanup. Comportamento coberto por testes sintéticos de sucesso, falha e Grafana indisponível.
- Segurança de supply chain: scanner offline conservador por padrões/nomes de arquivo, sem exibir valores de segredo. Integrado ao CI e à suíte de verificação, com quatro testes unitários.
- Controle: gate V14, readme de arranque, matriz de achados, handoff e progresso em dois indicadores.

**Validação:** 151 testes Python offline, teste real de Nginx; testes Flask/React/Firebase/Docker continuam pendentes de execução real. Não reaproveitar um arquivo de evidência antigo como prova de código novo.
