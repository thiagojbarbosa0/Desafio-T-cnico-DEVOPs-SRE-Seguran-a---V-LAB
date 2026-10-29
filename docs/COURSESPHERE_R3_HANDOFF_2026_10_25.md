# CourseSphere AppSec/SRE V-Lab — Handoff R3 (25/10/2026)

## Identidade e origem da base

**Base editada:** V19.9 Work recuperada do ZIP histórico, sucessivamente refinada em R1 e R2. **Não é o checkout V19.15.** O CourseSphere original (Flask, React/TypeScript, Firebase Auth/RTDB, SQLite) permanece; a aplicação de cursos sintética é separada. Nenhuma publicação, conta real, transação Firebase real ou comando Docker foram executados nesta sessão.

O ZIP V19.15 exato não estava disponível em bytes no ambiente; os ZIPs V19.13/V19.14 da Biblioteca foram encontrados, mas o mecanismo de materialização recusou o conteúdo. Portanto **não se deve sobrescrever arquivos V19.15 com o ZIP R3**. O complemento portátil e o patch são para revisão e aplicação seletiva.

## Trabalho material — R3

1. **Quota compartilhada (`backend/shared_quota.py`)**: rejeita relógios inválidos (NaN, infinito, booleanos, valores negativos, datas fora do limite) *antes* de consultar o banco; indisponibilidade do relógio da máquina vira `QuotaUnavailable`, não libera quota. Contador RTDB corrompido é rejeitado mesmo ao avançar a janela, impedindo uma restauração silenciosa de contadores inválidos. Mantida transação atômica e quota de 20 gravações por 60 s para `profile_write`. Implementação testada com banco transacional sintético, não com Firebase real.
2. **Correlação Nginx/Flask (`backend/request_correlation.py`, `backend/endpoints.py`, `compose.official.yaml`)**: o gateway já sobrescrevia `X-Request-ID`; Flask agora pode conservar apenas 32 caracteres hexadecimais se `COURSESPHERE_TRUST_GATEWAY_REQUEST_ID=1`. Fora dessa situação gera identificador aleatório novo. `replica` nos logs é validada em allowlist (`official_api_a`, `official_api_b`, `unknown`), nunca derivada de URL, UID ou header arbitrário. Docker Compose original define trust somente em ambiente de rede privada; containers Flask não publicam portas no host.
3. **Métricas (`backend/observability.py`)**: tempos impossíveis ou valores não numéricos não contaminam a série Prometheus com NaN/+Inf; a contagem de requisições permanece consistente. Tempos reais continuam normais.
4. **Diagnóstico de procedência (`scripts/review_evidence_freshness_r3.py`)**: confere hashes atuais de sete evidências prioritárias, rejeita JSON malformado/duplicado, identificando provas obsoletas ou ausentes sem reivindicar que foram executadas. Resultado atual: **2 consistentes / 5 obsoletas**. Consistência de hash NÃO implica execução real, e o script nunca acrescenta pontos ao release gate.
5. **CI (`.github/workflows/ci.yml`)**: substitui verificação obrigatória obsoleta de WSGI por relatório de diagnóstico histórico; roda suites regressivas novas de quota, correlação e fontes; publica JSON sanitizado como artefato. O CI preserva jobs de build, Auth/RTDB emuladores, Nginx nativo, Docker e auditoria npm já existentes.
6. **Testes novos:** `tests/test_quota_r3_failure_modes.py`, `tests/test_request_correlation_r3.py`, `tests/test_observability_finite_r3.py`, `tests/test_evidence_review_r3.py`: **31 casos adicionais** (R2: 419 → R3: 450).

## Evidências executadas nesta sessão

| Categoria | Nova execução R3 | Ressalva |
|---|---|---|
| Python | **450/450** via `python3 -m scripts.record_offline_v16` e descoberta direta | Offline, sem dependências Flask/Firebase Admin locais |
| Node | 3 verificações de sessão A→B, Chat e Profile | Com mocks controlados, não navegador real |
| TypeScript/TSX | Checagem sintática passou | Não é `npm ci && npm run build` |
| Nginx nativo | 40/40, failover 8/8, métricas protegidas, logs sem query; contrato original A/B 21/20, sobrevivência 8/8 | Upstreams sintéticos, sem Docker/Flask/Firebase |
| Segredos | Preflight local em 350 arquivos texto, 0 alertas; scanner de caminhos conhecidos passou | Sem histórico Git nem validade de credenciais upstream |
| npm lock | 412 entradas, 3 com script de instalação, sintaxe SRI/URL válida | Não é SCA, não substitui `npm audit` real |
| Evidência atual | 2/7 com fontes ainda correspondentes, 5/7 obsoletas | Classificador estático, 0 pontos extras |
| Gate **desta cópia** | **22/100, 3/8**, `ready_for_submission=false` | É R3/V19.9, **não V19.15** |

## Matriz upstream — prioridade da banca

- **F03**: token de autenticação transportado em URL (reprodução HTTP anterior). Causa corrigida via Authorization Bearer; novas mudanças em `endpoints.py` invalidam evidência HTTP antiga até repetir.
- **F04 (segredo em snapshot)**: arquivo com campos de credencial no material upstream. A evidência de presença é histórica. Não foi testado se o segredo é válido ou utilizado. Alguns documentos antigos usam F04 para CORS permissivo; usar a definição exata da matriz escolhida e NÃO contar duas instâncias de F04.
- **F05**: retorno de erro interno bruto; causa corrigida via respostas genéricas. Nova prova HTTP ainda requerida.
- **F06**: entradas sem limites/tipos; controles de tipos, limites e quotas adicionados. Não há comprovação de DoS.
- **P-PROFILE**: callback atrasado de sessão A aplicado à UI da sessão B no upstream; prova Node anterior ainda tem hashes de fontes consistentes. Não é vazamento server-side demonstrado.
- **F01/F02** permanecem dependentes da política de negócio: cadastro público e recomendação anônima podem ser previstos pelo produto. Não atribuir impacto de escalada de privilégio nem cobrança indiscriminadamente.

Três correções de causa raiz reconhecidas historicamente: Bearer no lugar do token na URL; erro genérico externo no lugar de detalhe interno; validação/limites na fronteira HTTP. A banca ainda precisa das reproduções e regressões com o código EXATO da entrega. As melhorias de quota/correlação/observabilidade R3 são da derivação, não falhas upstream.

## Bloqueios P0 e recomendações para V19.15

1. **Compare** os arquivos do complemento R3 à base V19.15. Transplante testes primeiro; só aplique alterações se o módulo exato continuar vulnerável. Não sobrescreva `backend/firebase.py` nem as novas regras de namespace/atestação da V19.15.
2. **Rebuild explícito** das imagens V19.15; `official_runtime_attestation_v19_15.py` deve provar imagens A/B, configuração Nginx e regras Firebase ativas, além do hash do frontend. Não reutilize contêineres antigos.
3. **Reexecute** Auth/RTDB Emulator com identidades sintéticas, isolamento, 20/21 via gateway, negação de escrita direta e failover. Faça a observabilidade Prometheus/Grafana em duas réplicas; não exponha `/metrics`.
4. **Reexecute** HTTP Flask original/corrigido com versões de fonte atuais e novo teste de correlação de `X-Request-ID` em duas réplicas reais.
5. Triagem CVE `npm audit` full/production na mesma revisão do lockfile sem `npm audit fix --force`; depois reexecutar release gate V19.15.
6. Revisão humana das 5 vulnerabilidades independentes, 3 correções de causa raiz, autorização de publicação e eventual rotação de credencial do snapshot.

Comandos seguros da R3:

```bash
python3 -m scripts.record_offline_v16
python3 -m scripts.review_evidence_freshness_r3 --output evidence/generated/EVIDENCE_REVIEW_R3.json
python3 -m scripts.release_gate_work_v19_9
python3 scripts/prove_nginx_native.py
python3 scripts/prove_official_nginx_contract_v19_7.py
```

**Não publique o ZIP completo da V19.9 sem análise de licença/histórico.** O complemento portátil foi feito para preservar a V19.15 e não inclui contas reais, credenciais reais, arquivos `.env` nem dependências instaladas.
