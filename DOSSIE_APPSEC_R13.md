# CourseSphere V-Lab — Dossiê AppSec e SRE | R13

**Estado:** implementação derivada da base V19.9 → R12 → R13. **Não é** o checkout V19.15.

**Regra de evidência:** provas de execução isolada do *handler* original não equivalem à exploração de produção. Provas sintéticas Nginx/SQLite não equivalem a Docker + Firebase Auth/RTDB. O projeto não está formalmente liberado para submissão.

## Escopo e origem dos achados

A linha de base da aplicação original está preservada em `audit/baseline/endpoints_original.txt`. O código corrigido está em `backend/endpoints.py`, `backend/security_core.py`, `backend/strict_request_json.py` e no frontend. `evidence/generated/ORIGIN_BEFORE_AFTER.json` contém reproduções offline isoladas, reconstruídas pelo `scripts/evidence_engine.py`. Cada achado abaixo é uma hipótese vulnerável **confirmada no comportamento local do código-fonte original**, sujeita aos limites de implantação e de requisitos do produto.

| ID | Categoria e causa raiz no upstream | Reprodução local | Mitigação na derivação | Limite de evidência |
|---|---|---|---|---|
| CS-01 | OWASP A07 — endpoint `/users/create` anônimo invocava **Firebase Admin** para criar conta, contornando o fluxo de cadastro cliente | handler original 200, corrigido 410 | Rota privilegiada desativada, signup no Firebase Client SDK | Não provado em produção nem como escalada de privilégio |
| CS-02 | OWASP A02/CWE-598 — recebia `id_token` por query string em `/users/info`, potencialmente acessível em histórico e logs | original 200, corrigido 401 | Somente `Authorization: Bearer` e bloqueio global de chaves sensíveis em URL | Não demonstrada exfiltração real de token |
| CS-03 | OWASP A05/CWE-209 — retornava `str(e)` em erros de backend | original 400 com detalhes, corrigido 500 genérico | Erros genéricos, telemetria sem URL/token/UID | A gravidade depende do conteúdo das exceções |
| CS-05 | OWASP A04/CWE-770 — mensagens sem limite quantitativo/tamanho do corpo | original aceitava lote excessivo, corrigido 400 | `validate_messages`, limite de 100 itens, corpo máximo de 32 KiB e quota compartilhada | Ensaio isolado, não exaustão real de recursos |
| CS-06 | OWASP A04/CWE-20 — campos de perfil sem limites coerentes de tamanho/tipo | original 200, corrigido 400 | `validate_profile`, parser JSON estrito e quota de 20/gravações/minuto | Ensaio isolado; quota integrada ainda precisa ser comprovada |

Os cinco achados cobrem pelo menos **quatro enquadramentos** OWASP (A02, A04, A05, A07). A identificação está vinculada aos trechos e às respostas do repositório, sem inferir grau de exposição público ou nível de acesso inexistente.

### Três correções de causa raiz priorizadas

1. **Cadastro e autenticação (CS-01):** desativar operações administrativas anônimas no Flask; exigir Firebase Client Auth e verificar tokens no backend. Prova local: retorno 410 e 401 para clientes não autenticados.
2. **Transporte seguro de token (CS-02):** rejeitar credenciais em URL e padronizar cabeçalho `Authorization`; no frontend, não persistir token em query string. Prova local: 401 para query token e testes de isolamento de sessão.
3. **Ingressos seguros e falhas controladas (CS-03/CS-05/CS-06):** normalizar exceções, validar esquema e limites, rejeitar chaves duplicadas/NaN e integrar limitador RTDB. Prova offline: respostas genéricas e validação estrita; prova integrada quota pendente.

### Achados que exigem cautela antes de apresentação

- **CS-04 (recomendação anônima):** depende de requisito de negócio sobre permitir consulta sem login. Não o usar como achado incondicional.
- **CS-07 (arquivo com campos de credencial):** campos `client_id`/`client_secret` foram observados no pacote original, mas valores foram suprimidos da derivação. Não testar se são válidos, não publicar a credencial e solicitar revogação ao responsável se aplicável.
- **CORS:** configuração originalmente permissiva não equivale, isoladamente, a bypass de autenticação; registrar como defesa complementar.

## Evidências e comandos já preparados

Em pasta extraída, no Fedora:

```bash
bash EXECUTAR_NO_FEDORA.sh
# Diagnóstico completo, se quiser permitir instalações online:
bash EXECUTAR_NO_FEDORA.sh --full
# Prova real emulador + dois processos Flask, sem qualquer conta externa:
bash scripts/verify_official_emulators.sh
```

A última opção requer Java 21, Firebase CLI e bibliotecas Python do backend, além de Internet para obtenção das dependências em uma instalação inicial. O script de emuladores executa **23 testes reais sobre o Flask + Firebase Emulator**, depois cria um usuário local adicional para validar **20 gravações intercaladas e rejeição da 21ª em ambas as réplicas**; retorna falha se algum passo não passar.

### Gate de aceite e honestidade

- `scripts/release_gate_r12.py`: a base derivada continua com gate bloqueado até novas evidências vinculadas ao código implantado.
- `scripts/verify_official_replica_quota_r11.py`: emite relatório `R11_OFFICIAL_FLASK_TWO_REPLICA_QUOTA.json` apenas após prova **real** bem-sucedida.
- `integration/run_r13_two_replica_quota.py`: orquestra o teste anterior, não inventa resultado quando o Firebase Emulator não existe e encerra as duas instâncias iniciadas.
- Ainda faltam: integrar no checkout **V19.15**, renovar atestados de origem/container, build frontend com dependências locais, SCA atualizada e execução Docker/Prometheus/Grafana da versão integrada.

**Política de publicação:** antes de disponibilizar o repositório, confirmar licença e direitos sobre os dados Cornell no pacote, revisar segredos reais e remover relatórios/logs privados ou de teste que não devam ser divulgados.
