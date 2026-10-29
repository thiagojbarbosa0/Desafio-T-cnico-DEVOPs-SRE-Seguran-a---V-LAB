# HANDOFF MESTRE — COURSESphere V8

**Data:** 22 de outubro de 2026  
**Versão de trabalho:** V8 — interface profissional + gateway verificado  
**Base:** V7, derivada do repositório oficial `LambdaAK/CourseSphere`, e não um CourseSphere refeito do zero.

## 1. Leia isto primeiro (um minuto)

**Objetivo real:** cumprir o Desafio Técnico de AppSec & SRE do V-Lab. Na aplicação original CourseSphere, investigar pelo menos 5 vulnerabilidades reais, corrigir ao menos 3 e provar isso. Também fazer hardening, observabilidade, Docker com duas réplicas + Nginx, relatório reproduzível e, depois, diferenciais.

**Nova decisão visual do usuário:** interface limpa e profissional, sem neon/glow/estética de IA. A V8 altera o **dashboard da sandbox**, não a interface React original.

**Estado técnico:** **84 testes Python passam** (incluindo novos testes reais de gateway HTTP). O script `collect_gateway_evidence_v8.py` executou 7 de 7 verificações sintéticas via proxy local e registrou os resultados em JSON. A auditoria de handlers originais da V7 permanece, mas **Flask/Firebase real, Docker/Nginx, Grafana, React build e CI remoto ainda não foram validados no ambiente atual**.

**Não confundir:** 84 testes NÃO significam 84 vulnerabilidades, e evidências sintéticas NÃO constituem um pentest da produção dos autores.

## 2. Como chegamos aqui

| Fase | O que mudou |
|---|---|
| V1–V4 | Protótipo equivalente, criado antes de receber o repo oficial. Não usar como auditoria do original. |
| V5 | Recebimento do ZIP verdadeiro, revisão inicial e primeiras correções. |
| V6 | Extensão local com cursos/aulas sintéticos, backend stdlib, observabilidade e dashboard. |
| V7 | Evidências antes/depois da lógica original, remoção de segredo no pacote derivado, 70 testes, CI e SBOM. |
| **V8** | Design sóbrio refeito, interface responsiva e funcional, coleta de evidências do laboratório pela UI, 14 novos testes, proteção adicional do gateway, 7 provas HTTP de ponta a ponta **dentro da sandbox**. |

## 3. Arquitetura — não misturar os dois mundos

```
[ALVO ORIGINAL] React/Vite + Firebase Auth  ->  Flask endpoints -> Firebase Realtime Database
                                       \-> SQLite legado (blueprint inativo)

[LABORATÓRIO] dashboard HTML/CSS/JS -> gateway local ou Nginx -> API demo A/B
                                                                  |
                                                       SQLite SINTÉTICO
                                                   /metrics, health, audit
```

O original é alvo de análise/correção. O laboratório tem API própria para demonstração, e **nunca deve ser publicado com contas selecionáveis (`admin`, etc.)**. `backend/local_server.py` não é o Flask de origem.

## 4. O que V8 implementou

**Produto/UI:** design padrão de SaaS claro; navegação acessível; tabela; páginas separadas; diagnóstico em tempo real; exportação de evidência em JSON sanitizado; mobile sem overflow; sem fonts/CDNs externos. Consulte `docs/DESIGN_V8.md`.

**Segurança:** gateway rejeita request body com Transfer-Encoding não suportado, Content-Length inválido e request-target absoluto; mantém `/metrics` inacessível externamente; remove `unsafe-inline` da CSP do dashboard local e configura headers adicionais. Testes de regressão cobrem essas proteções.

**Teste e evidência:** `tests/test_gateway_v8.py` faz HTTP real gateway->API em localhost; `tests/test_dashboard_v8.py` protege integridade e renderização segura. `scripts/collect_gateway_evidence_v8.py` recria 7 evidências (dashboard 200, ready 200, metrics 403, login 200, lista 200, BOLA negado 403, dono permitido 200), sem salvar tokens. `bash scripts/verify.sh` executa tudo.

**Capturas:** `evidence/ui/*_MOCK.png` são renderizações Chromium reais com API **simulada apenas para a captura**. Não são provas de navegação do navegador até o servidor real.

## 5. Pesos do edital — prioridade correta

O edital NÃO fornece nota percentual por item; apenas **alta / média / baixa**.

**ALTA (P0, trabalho com maior retorno):** provar 5 problemas reais da aplicação original, com passos de reprodução, severidade/impacto, e 3 correções com teste antes/depois (em Flask/Firebase Emulator com identidades sintéticas). A V7 tem 6 comportamentos de *handlers* originais executados isoladamente com stubs, **não cinco explorações HTTP de sistema integrado**.

**MÉDIA (P1):** relatório executivo/técnico, hardening, arquitetura de balanceamento e evidência de dois backends Nginx. Algumas configurações estão escritas; precisamos rodá-las no Fedora.

**BAIXA (P2):** automatização, logs e monitoramento, CI, SAST/SCA. Ainda são relevantes para se destacar, sem roubar tempo do P0.

## 6. Onde estão os entregáveis

| Arquivo | Por que abrir |
|---|---|
| `dashboard/index.html`, `style.css`, `app.js` | Novo visual e comportamento do painel |
| `docs/DESIGN_V8.md` | Decisão de UX e QA |
| `tests/test_gateway_v8.py` | Testes HTTP reais do proxy local |
| `tests/test_dashboard_v8.py` | Regressão visual/lógica básica sem navegador |
| `scripts/collect_gateway_evidence_v8.py` | Provas HTTP geradas automaticamente |
| `evidence/generated/HTTP_GATEWAY_V8.json` | Resultado e request IDs dos sete checks locais |
| `evidence/ui/` | Quatro screenshots renderizados com API mockada |
| `docs/RELATORIO_PENTEST_V7.md` | Nove observações de segurança da origem, com limitações |
| `evidence/generated/ORIGIN_BEFORE_AFTER.json` | Comparação de handlers originais e corrigidos |
| `HANDOFF_MESTRE_V7.md` | Histórico detalhado da investigação antes da V8 |
| `.github/workflows/ci.yml` | Jobs configurados para GitHub Actions (ainda não rodados no GitHub) |

## 7. O que fazer no Fedora, na ordem

1. Extraia o ZIP V8 e execute `bash scripts/verify.sh` — precisa apenas Python 3.10+ e shell; roda testes e gera evidências.
2. Execute `bash scripts/start_local.sh`, depois acesse `http://127.0.0.1:8080/lab/`. Navegue nas quatro telas e exporte o JSON de autorização.
3. Faça screenshots **reais do navegador conectado à API**. Eles devem substituir as previews com `mock-preview` na apresentação final.
4. Com Docker instalado, rode `docker compose version` e `bash scripts/start_docker.sh`; verifique `docker compose ps`, requisições respondidas por `api-a` e `api-b` e degradação após parar um deles.
5. Se tiver internet, `cd frontend && npm ci && npm run build && npm audit --audit-level=high` (frontend React **original**). Salve logs sanitizados.
6. Para comprovação P0: configure **Firebase Emulator próprio + Flask** em cópia local, sem utilizar contas/credenciais de terceiros; faça testes HTTP do original e corrigido. Revise Realtime Database Rules; produza provas sanitizadas. Essa etapa define a qualidade da entrega.
7. Organize commits por correção, atualize relatório e confirme licença/permissão de publicação do código upstream antes de criar repositório público derivado.

## 8. Pendências mais importantes e riscos

- **P0:** ainda não há cinco explorações do CourseSphere real em Flask/Firebase em runtime, nem provas E2E de três correções. Esta é a principal lacuna.
- **P0 externo:** arquivo contendo campos de credencial no ZIP original removido do derivado; o proprietário precisa rotacionar/revogar. Não reutilizar/testar esse segredo.
- **P1:** Docker e Nginx/Grafana não foram executados neste ambiente; os testes de gateway stdlib NÃO validam distribuição de carga via Nginx.
- **P1:** frontend React original não passou por `npm ci`/build neste ambiente; dependências Flask indisponíveis aqui, inclusive em tentativa de instalação offline.
- **P1:** capturas Chromium com HTTP direto foram bloqueadas por política de rede do navegador da ferramenta; capturas visuais são previews mockadas, identificadas.
- **P2:** scanners reais Bandit/npm audit/CI remoto ainda sem relatório de execução. SBOM de pacote npm é inventário, não um CVE scanner.
- **Jurídico/ética:** não publicar cópia do repositório dos autores sem confirmar licença/autorização. Testes ofensivos sempre só em localhost/cópia autorizada.

## 9. Decisões sob controle do usuário

- **DEC-08 APROVADA:** painel SaaS simples, visual neutro, sem neon. Evitar regressão estética.
- **DEC-01 MANTIDA:** manter stack original React/Flask/Firebase/SQLite, em vez de migrar tudo para Rails apenas pela imagem da vaga.
- **DEC-09 PENDENTE:** instalar dependências e executar em Fedora; enviar logs sanitizados para corrigirmos problemas reais de runtime.
- **DEC-10 PENDENTE:** validar permissão de uso/fork público do repo dos autores.
- **DEC-11 PENDENTE:** escolher estratégia local de Firebase Emulator e usuários fictícios, jamais usar credenciais dos autores.

## 10. Critérios de pronto para banca

Desafio só pode ser marcado como concluído depois que houver (a) cinco problemas reais comprovados no escopo autorizado, (b) pelo menos três correções de causa raiz com evidências de regressão em runtime, (c) pelo menos duas melhorias adicionais de hardening, (d) logs JSON, `/health`, `/metrics`, 2 SLIs/SLOs, (e) Dockerfiles, Compose com 2 backends Nginx com distribuição real, (f) relatório claro com prints e reprodução, (g) README e Git público conforme direitos de uso. Diferenciais somente depois. Não inventar porcentagens ou garantias de aprovação.

**Conclusão V8:** a V8 atende sua nova direção estética e aumenta evidência verificável do **laboratório**. O P0 do CourseSphere original continua sendo o gargalo que decide se a entrega cumprirá o edital. Não confundir aparência bonita com a auditoria solicitada.
