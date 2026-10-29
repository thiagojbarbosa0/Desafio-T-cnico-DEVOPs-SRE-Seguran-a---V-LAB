# Matriz de achados — código upstream | V14

**Escopo:** snapshot do repositório original recebido em ZIP; rotas e dependências observadas no código, sem uso de credenciais reais nem ataques contra terceiros. Fonte original arquivada em `audit/baseline/endpoints_original.txt`.

| ID | Encontrado no original | Categoria/risco | Mudança derivada | Prova real disponível / pendência |
|---|---|---|---|---|
| F01 | `POST /users/create` usa Firebase Admin sem exigir token do requisitante | Broken access control / criação de usuários privilegiada | Devolve 410; cadastro pelo SDK cliente Firebase | Handler sintético executado; teste HTTP Flask preparado, ainda não executado |
| F02 | `POST /users/query` não exige Bearer autenticado | Auth / uso abusivo de recursos e consultas | `verified_uid()` antes de executar consulta | Handler sintético; HTTP preparado, sem execução |
| F03 | `GET /users/info` obtém `id_token` de URL | Sessão / exposição via URL, histórico e logs | Autenticação exclusivamente por header; V14 rejeita qualquer token presente na URL | Handler sintético; prova HTTP pendente |
| F04 | `CORS(app)` autoriza origens arbitrárias | Configuração inadequada; impacto depende de autenticação e CORS credential | Allowlist de origens | Revisão de fonte; prova HTTP pendente |
| F05 | Rotas devolvem `str(e)` com detalhes internos | Exposição de informação | Erros externos genéricos e status explícitos | Handler sintético; prova HTTP pendente |
| F06 | Perfil, query e mensagens sem limites/tipos consistentes | Input validation / disponibilidade | Limites e allowlist; V14 rejeita IDs duplicados por lote | Testes Python da validação; teste HTTP pendente |
| F07 | `app.run(debug=True)` no original | Configuração insegura se exposto | `debug=False`; execução loopback nos testes | Fonte; sem evidência de produção exposta |
| F08 | Snapshot continha campos de credenciais de terceiro | Gestão de segredos | Arquivo removido da derivação | Metadata sanitizada; validade desconhecida; dono deve revogar/rotacionar |
| F09 | SQL concatenado em blueprint legado | Injeção SQL **potencial** | Queries parametrizadas | Módulo não registrado no backend original: **não conta como rota ativa explorável** |

## Escolha de 5 achados prioritários para investigar, não afirmar como explorados

F01, F02, F03, F05 e F06. F04 é um sexto candidato, com risco contextual. F07 requer contexto de implantação para severidade. F08 precisa de contato com dono da credencial. **F09 NÃO deve ser usado para completar o mínimo do edital sem ativação autorizada e prova relevante.**

## Reprodutibilidade e causas raízes

- `python3 scripts/evidence_engine.py` reproduz comportamentos isolados dos handlers, com adaptadores sintéticos.
- `python3 -m integration.run_original_http_stubbed` executa as rotas com **Flask real em HTTP local**, mas dados Firebase sintéticos; 15 testes aguardando disponibilidade das bibliotecas.
- `bash scripts/verify_official_emulators.sh` usa **Firebase Auth e Realtime Database emuladores oficiais** em `demo-coursesphere-vlab`, sem acesso ao serviço dos autores.

Três correções centrais com causa raiz explicável: **F01**, API Firebase Admin exposta no fluxo público; **F02**, ausência de verificação obrigatória de identidade; **F03**, credencial colocada na URL. As correções aplicam controle na fronteira HTTP, não apenas mascaram erros. Ainda falta anexar provas de serviço real por HTTP e verificar impacto contextual para fechamento do edital.

Severidade alta/média é preliminar e condicionada ao contexto; não atribuir CVSS inventado. Os detalhes técnicos e riscos estão em `docs/RELATORIO_PENTEST_V12.md`.


## V17 — hardening adicional compartilhado (não é nova falha comprovada no upstream)

- **F02 / proteção de abuso:** a chamada autenticada de recomendações agora passa por um limitador transacional de **30 requisições por 60 segundos por UID**; a emissão de identificadores (`POST /hash`) permite **120 requisições por 60 segundos por UID**. Os contadores ficam em `server_security/rate_limits/` no Firebase RTDB, **fora do namespace editável pelos usuários**, e são compartilhados entre réplicas Flask. `429` indica quota esgotada; `503` indica falha do serviço de quotas e não libera a chamada por engano.
- **Escopo:** esse limite depende do RTDB e de permissões administrativas de acesso. Não limita cadastros anônimos nem ataques distribuídos antes da autenticação. São necessários limites na borda contra tráfego volumétrico.
- **Evidência:** 12 testes offline, incluindo simulação de 80 requisições concorrentes; um caso adicional no Firebase Emulator (total 20) **preparado, ainda não executado nesta sessão**.
- **Observação de segurança:** o teste não prova uma nova exploração do original e não deve inflar o número de vulnerabilidades encontradas.
