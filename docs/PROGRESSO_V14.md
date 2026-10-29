# Progresso V14 — dois indicadores, não uma nota

**≈62% de implementação estimada:** avaliação aproximada do conjunto de código/configuração/documentação, ante ≈60% na V13. Progresso real desta versão: alterações no Flask e validação, correção do teste operacional que poderia reportar falsos positivos, testes novos, preflight de segredos e handoff.

**15% de aceite comprovado ponderado:** duas etapas com execução real e evidências associadas a esta revisão; sete por cento para regressões offline e oito para Nginx nativo. Os demais 85 pontos percentuais não contam até a execução real e revisão dos requisitos.

| Grupo | Peso interno | Comprovado? | Responsável pelo próximo passo |
|---|---:|---|---|
| Testes offline Python | 7% | Sim (151 testes) | Assistente |
| Nginx nativo e failover com réplicas sintéticas | 8% | Sim | Assistente |
| Flask HTTP antes/depois + adaptador Firebase sintético | 20% | Não | Execução Fedora / CI |
| Flask + Firebase Emulator Auth e Database | 18% | Não | Execução Fedora / CI |
| Build React Vite/TypeScript | 7% | Não | Execução Fedora / CI |
| Docker Compose + Grafana + Prometheus + failover | 15% | Não | Execução Fedora / CI |
| Cinco achados reais e três correções do original | 20% | Não (em análise; evidência insuficiente) | Revisão das provas integradas |
| Licença de uso/redistribuição e rotação de credencial do upstream | 5% | Não | Organização e proprietário upstream |
| **Total** | **100%** | **15%** | |

Os pesos são **definidos por nós**, não pelo V-Lab, que fala apenas em prioridades alta/média/baixa. Nenhuma porcentagem é previsão de aprovação. Para executar localmente use `bash scripts/verify_v14.sh`; para desbloquear integrações use `bash scripts/fedora_validation_v14.sh --install-deps --with-docker` no Fedora.
