# HANDOFF MESTRE — CourseSphere V19.6

## 1. Missão original

Desafio V-Lab AppSec/SRE: avaliar segurança de uma aplicação CourseSphere existente, demonstrar **pelo menos cinco vulnerabilidades reais** em duas ou mais categorias, corrigir **ao menos três** com causa raiz documentada, executar duas melhorias extras de hardening, instrumentar logs/métricas, especificar SLIs/SLOs, executar duas instâncias de backend balanceadas com Docker/Nginx e fornecer relatório e evidências reproduzíveis. São opcionais STRIDE, CI/SAST/SCA, Kubernetes, dashboard funcional e testes automatizados adicionais.

O repositório upstream do usuário é **LambdaAK/CourseSphere**, stack **Flask + React/TypeScript/Vite + Firebase Auth/RTDB e SQLite**. É um recomendador de disciplinas; o CRUD de cursos/aulas do enunciado não está integralmente no backend upstream. O laboratório próprio de cursos/aulas foi mantido como **componente didático isolado**, não como substituição ou prova de vulnerabilidade do upstream.

## 2. Estado acumulado e limites

V19.5: seis candidatos a achados F01–F06 (F01/F02 condicionais à regra de negócio, F04 exposição estática de material com aparência de segredo, sem testar validade); três eixos principais de correção do upstream: token no cabeçalho, tratamento seguro de erros e validação de entradas. Hardening de RTDB, quotas distribuídas, logs sem tokens, ferramentas de evidência e CI. Testes Flask e React de versões anteriores permanecem históricos até execução com hashes atuais. Nginx nativo demonstra 2 réplicas do **laboratório sintético**, não réplicas de produção. Docker/Prometheus/Grafana ainda não foram executados neste host.

## 3. Trabalho concreto V19.6

- `backend/cors_policy.py`: política CORS fail-closed para `ALLOWED_ORIGINS` (sem curinga, origem opaca, URL com path/query/fragment, credenciais, HTTP remoto, porta malformada; sem aceitar nomes ambíguos). HTTPS remoto permitido, HTTP apenas loopback de desenvolvimento. `backend/endpoints.py` carrega essa política antes de configurar `Flask-Cors`.
- `tests/test_v19_6_cors_policy.py`, `tests/test_v19_6_release_gate.py`: 13 novas regressões offline para política, compatibilidade local, evidência com hash e ausência de falsos positivos.
- `integration/test_v19_6_cors_runtime.py` + `integration/run_v19_6_cors_runtime.py`: cinco testes de **Flask real e Flask-Cors reais**, com Firebase/QueryManager simulados, executados no CI/Fedora apenas quando as dependências estão disponíveis. O runner falha ao detectar skips e não aprova resultado parcialmente executado.
- Hash novo de `backend/cors_policy.py` nas evidências/validadores `integration/run_original_http_stubbed.py`, `integration/run_official_emulator_tests.py`, `integration/run_v19_4_flask_wsgitest.py`, `scripts/prove_original_flask_nginx.py`, `scripts/release_gate_v12.py`, `scripts/release_gate_v19.py`; testes antigos de evidência atualizados para rejeitar explicitamente prova sem o hash.
- `.github/workflows/ci.yml`: executa a suíte WSGI CORS na job Flask e publica resultado junto das demais provas. `scripts/verify_local_v19_6.sh` e `scripts/release_gate_v19_6.py`: comandos atuais; o gate CORS é suplementar e **não inventa nova pontuação**.

## 4. O que foi executado nesta sessão

| Validação | Estado | Escopo |
|---|---|---|
| `bash scripts/verify.sh` via `record_offline_v16` | **294 testes Python PASS** | Offline, AST/handlers sintéticos e verificações de código |
| `python scripts/check_nginx_main_config_v19_3.py` | **PASS** | Configuração Nginx nativa |
| `python scripts/prove_nginx_native.py` | **PASS** | 40 requests distribuídos 20/20, 8/8 após desligamento, token bloqueado e log sem query |
| `node scripts/test_session_gate_v19_2.cjs`, `test_user_chats_runtime_v19_2.cjs`, `test_profile_session_runtime_v19_2.cjs` | **PASS** | Testes Node de isolamento entre sessões, **não** build React |
| Suite Flask+Flask-Cors V19.6 | **NÃO EXECUTADO** | Flask e Flask-Cors não instalados neste ambiente; pip indisponível |
| Firebase Auth/RTDB Emulator | **NÃO EXECUTADO** | Requer dependências e serviços locais |
| React build atual | **NÃO EXECUTADO** | Dependências npm incompletas aqui |
| Docker/Grafana/Prometheus | **NÃO EXECUTADO** | Docker indisponível aqui |

O gate atual registra **15% de aceite ponderado comprovado** para esta cópia, com **2 de 8 grupos** passando. A estimativa qualitativa de implementação mantém **69%** para não inflar avanço sem evidência integrada. São métricas internas, não nota ou probabilidade de aprovação.

## 5. Próximo foco obrigatório (prioridade alta do edital)

1. Executar `PATH="$PWD/.venv/bin:$PATH" bash scripts/verify_local_v19_6.sh` com Flask instalado e registrar o teste CORS WSGI, 15 HTTP antes/depois, sete Flask WSGI autenticação/quotas e Flask/Nginx com réplicas. Conferir relatórios `evidence/generated/*.json` e hashes atuais.
2. Rodar `bash scripts/verify_official_emulators.sh` com Firebase Emulator e base local `demo-`, verificando acesso por usuário, gravações proibidas no RTDB e quotas distribuídas. Sem qualquer credencial de produção.
3. `bash scripts/verify_frontend_build_v14_2.sh` com as dependências npm disponíveis, navegar fluxos de sessão com contas de teste, validar React atual.
4. Docker Compose local + Prometheus + Grafana + verificador de failover; não tratar o laboratório como prova do Flask original.
5. Revisão humana de F01/F02 como políticas funcionais (podem não ser vulnerabilidades), localização de novos achados independentes se necessário, severidades fundamentadas, causas raízes e evidências na aplicação original.
6. Confirmar licença/autorização para redistribuição. Comunicar o material exposto upstream ao proprietário em privado, sem publicar/citar valores. O script F04 não testa credenciais externamente.

## 6. Direção do produto

Manter o visual SaaS corporativo sóbrio: limpo, claro, sem neon, glow, estética cyberpunk ou efeitos excessivos. Custo zero e execução local em Fedora. Evitar refatoração de stack para Rails apenas por associação com a vaga; React/Flask é alternativa explicitamente permitida pelo desafio. Priorizar prova de segurança e operação sobre features decorativas.

## 7. Critérios de honestidade

Não confundir: configuração com serviço rodando; Python AST com HTTP Flask; serviço simulado com Firebase Emulator; Flask em teste com implantação de produção; teste Node com build React; presença de JSON de credencial com validade ativa. Não declarar 100% sem evidências das integrações e avaliação funcional dos cinco achados.

## 8. Para retomar sem perder contexto

**Base de código:** `CourseSphere_V19_6`. Antes de executar testes, conferir `sha256sum --quiet -c MANIFEST_SHA256_V19_6.txt`. Os scripts reescrevem evidências geradas e podem alterar hashes após a validação. **Primeiro arquivo:** `README_V19_6_COMECE_AQUI.md`. **Comando local:** `bash scripts/verify_local_v19_6.sh`. Arquivos anteriores V7–V19.5 são históricos. Não reintroduzir ZIP upstream nem dados de credenciais. Salvar checkpoints regulares e sempre entregar o ZIP testado.
