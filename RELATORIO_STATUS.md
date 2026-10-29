# R15 Work — estado de entrega

Base R14, sem integração comprovada à V19.15. Evidências geradas em 27/10/2026.

| Requisito | Estado | Evidência/limite |
|---|---|---|
| Segurança upstream, cinco achados | PENDENTE | RELATORIO_SEGURANCA_ATUAL.md: categorias e limites; cadastro depende de política, validação de perfil/mensagem não conta automaticamente duas vezes |
| Três correções antes/depois | PASS local | 15 HTTP reais com adapters sintéticos; perfil TypeScript original/corrigido; não exploração em produção |
| Flask/Firebase e quota distribuída | PASS | 23 testes + 8 critérios, cleanup restrito confirmado; dois processos reais na nova prova |
| Nginx + failover autenticado | PASS nativo | 8/8 leituras durante falha; perfil recuperado; Firebase real em emuladores |
| Logs/SLIs/SLOs | PASS parcial | Prometheus real; 6 cenários promtool; nenhuma prova de janela de SLO em produção |
| Docker + Grafana completo | NOT_RUN | Docker ausente; provas nativas não substituem containers |
| Frontend | PASS parcial | npm ci, TypeScript/Vite, três scripts Node; navegador NOT_RUN |
| Dependências produção | FAIL parcial | 24→14 alertas; 0 críticos, 5 altos, 9 moderados após atualização compatível; major upgrades pendentes |
| Instalador/rollback | PASS em testes locais | ZIP adversarial, atualização, preservação 0600, rollback e falha sem trocar versão; Fedora do usuário não acessado |
| CI | NOT_RUN remoto | Job acrescentado; comandos equivalentes executados no Work |
| Offline | PASS | 811 testes; logs sanitizados e hashes |

Aceite do gate existente: **60/100**, ready_for_submission=false; era 22/100 histórico da linha R14. Nenhum ponto extra inventado para nova prova nativa. Sem percentual novo de implementação: o número histórico 73% da linha anterior não foi recalculado para R14.

Próxima ação de maior impacto: executar a stack oficial Docker completa, mantendo identidade do projeto e preservando outros containers/volumes; resolver as atualizações npm de maior impacto. Fontes e comandos em CONTINUIDADE_ATUAL.md. Dados anteriores sem hash/execução atuais são STALE.
