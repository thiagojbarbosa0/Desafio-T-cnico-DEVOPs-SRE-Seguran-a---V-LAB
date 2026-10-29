# Architecture Decision Records (resumo)

## ADR-001 — preservar o repositório original
**Status:** aceito. Alternativa descartada: continuar no produto substituto V1–V4. **Consequência:** manter frontend React e backend Flask como alvo factual, comparar alterações, adiar reescrita.

## ADR-002 — sandbox com Python stdlib
**Status:** aceito como componente didático. **Motivo:** rodar sem chaves Firebase/OpenAI, sem pip nem dinheiro, e reproduzir autorização/testes em localhost. **Não é** substituição de Firebase em produção. **Limite:** auth demo pública local, SQLite WAL mono-host.

## ADR-003 — duas réplicas + Nginx + SQLite local
**Status:** configuração criada; execução não aceita como concluída. Alternativa: Kubernetes local e PostgreSQL agora. Escolha atual: Compose como etapa intermediária mais barata/reprodutível. Critério: demonstrar duas instâncias por header `X-CourseSphere-Instance`, métricas e logs.

## ADR-004 — prioridade P0 acima de diferencial visual
**Status:** aceito. O edital premia em primeiro lugar achados reais e correções. O design Security Arena é de apoio; não comprova que a origem contém cinco vulnerabilidades.

## ADR-005 — proibir deploy público do ambiente de demonstração
**Status:** obrigatório. Laboratório permite solicitar identidade de `admin`, logo não pode ser hospedado abertamente. Publicação seria falha grave; rede local, firewall, bind 127.0.0.1 e dados sintéticos são indispensáveis.
