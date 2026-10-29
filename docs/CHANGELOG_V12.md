# Mudanças técnicas V11 → V12

## Qualidade e prova do código original

- +4 cenários Flask HTTP preparados: token no corpo da requisição de perfil, `/hash` sem header, exclusão de chat sem autenticação e limite da consulta — **13 no total**.
- O JSON da comparação antes/depois inclui códigos HTTP, tipos de resposta, indicadores seguros de exposição de erros, CORS e hashes das fontes/harness, mas **não tokens nem dados de usuários**.
- Testes Firebase Emulator ampliados de 15 para **19 casos preparados**; eliminação da dependência de ordem para fixtures dos chats; casos extras de autenticação, header e CORS.
- Runner e gate não contam testes pulados como sucesso. Gates verificam digests SHA-256 dos arquivos usados nas provas.

## Segurança

- `validate_messages` exige identificadores e timestamps como strings; deixa de converter números e objetos para string por coerção implícita. Novos testes negativos.

## Operação e documentação

- Script `scripts/verify_v12.sh` executa verificações disponíveis, declara pendências e produz `RELEASE_GATE_V12.json`.
- Handoff e relatório atualizados; escopo do aplicativo original separado da sandbox, risco de credencial e licença explícitos.
- CI aponta para evidências V12 dos runners HTTP/Firebase (o workflow precisa ser executado no GitHub).

## Provas executadas nesta sessão

- 130 testes Python offline aprovados.
- Nginx real com 20/20 requisições distribuídas, 8/8 após falha da primeira instância, proteção de métricas.
- Execução do runner HTTP sem Flask falhou corretamente e **não** gerou prova positiva.

**Não afirmar:** pentest HTTP Flask finalizado, Firebase validado, frontend compilado, Grafana rodando ou Docker testado. Os oito grupos de aceite não são pesos oficiais da seleção.
