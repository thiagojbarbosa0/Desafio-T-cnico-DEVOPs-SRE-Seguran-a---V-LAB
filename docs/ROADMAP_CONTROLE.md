> **PLANEJAMENTO HISTÓRICO V6. Controle atualizado em [HANDOFF_MESTRE_V7.md](../HANDOFF_MESTRE_V7.md).**

# CONTROLE DO PROJETO — Dashboard de governança do usuário

Atualização: V6, 22/10/2026. Este documento determina prioridades e bloqueios. Não descreve desejos como entregas.

## Regras da próxima rodada

1. **Qualquer status de concluído exige ao menos uma evidência reexecutável.**
2. Fonte original ≠ sandbox: não transportar achados, prints nem percentuais entre elas.
3. **P0 antes de P1 antes de P2**, conforme a classificação do edital. Nunca gastar um dia em UI enquanto faltar evidência do P0.
4. Custo zero obrigatório. Portas localhost. Dados sintéticos.
5. Toda alteração de arquitetura deve ter ADR com motivação, alternativas, riscos e aceite.
6. Não usar credenciais pessoais, Firebase de terceiros ou produção para testes.

## Quadro Kanban

| Prioridade | Entrega | Estado | O que você deve exigir como prova |
|---|---|---|---|
| P0 | Inventário origem e referências upstream | Em execução | hash do ZIP, links e revisão técnica |
| P0 | 5 vulnerabilidades ativas, 2 categorias | **BLOQUEADO** | 5 requests/responses na origem local e provas sanitizadas |
| P0 | 3 correções demonstradas antes/depois | **BLOQUEADO** | teste falha na origem + passa corrigido, 3 causas distintas |
| P0 | hardening mínimo | Parcialmente implementado | Flask tests e inspeção de headers/CORS |
| P1 | API curso/aula de demonstração | TESTADA em sandbox | 60 testes Python + chamadas HTTP |
| P1 | logs estruturados, métricas e readiness | TESTADA em sandbox | logs/`/metrics`/`/api/ready` |
| P1 | docker + frontend + 2 backend + nginx | CONFIGURADO | `docker compose ps`, captura com 2 instâncias |
| P1 | SLIs/SLOs e relatório técnico | DOCUMENTADO | PromQL + relatório verificável |
| P2 | Grafana + Prometheus | CONFIGURADO | print de gráficos reais e série Prometheus |
| P2 | testes de CI + SAST + Dependabot | CONFIGURADO | jobs verdes e output real dos scanners |
| P2 | threat modeling STRIDE | DOCUMENTADO | `STRIDE_THREAT_MODEL.md` com suposições |
| P2 | frontend UI Security Arena | HTML renderizado | print estático e validação funcional no Fedora |
| EXTRA | Kubernetes local | PENDENTE | kind/k3d + pods ready + rollback real |
| EXTRA | Resilience Playground | PLANEJADO | relatório cronológico de failover medido |
| EXTRA | Evidence Engine com hash de evidências | PLANEJADO | script de inventário e sanitização auditada |
| EXTRA | SBOM + proveniência | PLANEJADO | CycloneDX/SPDX gerado + relatório de CVEs |
| EXTRA | assistente offline de priorização | PLANEJADO | regras testadas, sem LLM inventando vulnerabilidades |

## Próximas decisões estratégicas

- **DEC-A**: manter React/Flask + extensão separada até concluir o pentest original? Recomendado: SIM.
- **DEC-B**: emular Firebase no local ou usar fake/injeção no Flask? Recomendado: fake primeiro por reprodutibilidade; emulador depois.
- **DEC-C**: migrar dados para PostgreSQL? Recomendado: só se permitir demonstrar autenticação/queries sem duplicar o sistema original; não migrar por marketing.
- **DEC-D**: publicar o repositório do trabalho na sua conta GitHub? Requer decisão sua; verificar licenciamento/atribuição da origem antes.
- **DEC-E**: entregar ZIP do projeto + relatório e evidências? Recomendado: sim, acompanhado de README robusto e prints reais do Fedora.

## Critério de aceite da banca (sem falsos positivos)

A entrega só será “pronta para submeter” quando: ≥5 casos ativos confirmados na origem (≥2 categorias), ≥3 correções com testes demonstrados, ≥2 hardenings validados, logs/metrics/health funcionando, dois SLI/SLO claros, Docker backend/frontend + duas instâncias Nginx comprovados, relatório e README completos, SAST anexado se possível.

### O que o usuário realmente precisa fazer

1. Rodar `bash scripts/start_local.sh` para inspecionar UX e Security Arena.
2. Rodar `bash scripts/verify.sh` para ver regressões reais.
3. Rodar Compose e `python3 scripts/collect_evidence.py` no Fedora, devolver logs de erro se houver.
4. Decidir se a integração com Firebase real pode ser emulada, sem segredos remotos; escolher se publicação GitHub é autorizada.
5. Aprovar ou recusar migração de stack **somente após P0**.

A liberdade criativa do assistente se aplica a melhorias reversíveis e documentadas, não a decisões irreversíveis.
