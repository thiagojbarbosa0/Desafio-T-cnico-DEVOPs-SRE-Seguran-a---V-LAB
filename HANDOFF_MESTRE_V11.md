# Handoff mestre — CourseSphere AppSec/SRE — V11

**Estado:** rodada V11. **NÃO finalizado para envio ao V-Lab.** Documento atualizado para acompanhamento e tomada de decisões.

## 1. De onde viemos

O desafio do V-Lab não pede um novo produto educacional: pede que o candidato examine uma aplicação de referência, encontre no mínimo cinco problemas de segurança em ao menos duas categorias, reproduza os achados, corrija três causas raízes, acrescente hardening, observabilidade, Docker + balanceador e apresente relatório reproduzível. A banca dá maior prioridade a achados reais, provas e correções sem regressão; documentação, resiliência e hardening vêm depois; ferramentas automáticas e diferenciais são complementares. O prazo concreto está no edital, não neste pacote.

O usuário enviou o repositório `LambdaAK/CourseSphere`. O projeto upstream era React/TypeScript/Vite + Python/Flask + Firebase Auth/Realtime Database, além de módulos e dados SQLite, com parte do recomendador ainda demonstrativa. A implementação principal **não** contém o CRUD completo de cursos/aulas do exemplo do edital. Portanto, foi criada uma **extensão sintética isolada**, sem alegar que seu código substitui vulnerabilidades do upstream.

Histórico resumido: V1–V4 protótipo independente; V5 reorientação para código oficial; V6–V8 extensão local, testes, docs e painel SaaS claro; V9 Nginx real e integração Firebase Emulator preparada; V10 chat original corrigido, 104 testes, acceptance gate; V11 adiciona um roteiro de **comparação HTTP real Flask antes/depois com Firebase simulado**, reforça o frontend, melhora a rastreabilidade e repete testes de Nginx. Arquivos históricos permanecem no pacote para auditoria.

## 2. A visão do produto

**Entrega principal:** um repositório auditável do CourseSphere original com correções mínimas e justificadas, testes automatizados, relatório técnico, execução local sem custo, observabilidade, balanceamento e evidências. **Diferenciais:** Security Arena sintética, Evidence Engine, STRIDE, SBOM, resiliência e interface convencional e sóbria. Não priorizar animações/neon ou mudanças de stack gratuitas. Sempre implementar primeiro aquilo que atende ao edital.

## 3. Estado técnico agora

| Componente | Implementação | Execução comprovada |
|---|---|---|
| Código Flask original corrigido | Sim | Handlers sintéticos; **HTTP Flask E3 ainda pendente** |
| Frontend React original corrigido | Parcialmente | Parser TS/TSX, **build npm completo pendente** |
| Firebase Emulator Auth/Database | Scripts e regras preparados | **Pendente** |
| Laboratório local Python stdlib com cursos/aulas | Sim | Testes offline e HTTP sintético aprovados |
| Nginx, duas réplicas, failover | Configuração + script nativo | **Comprovado localmente com Nginx real e apps sintéticos** |
| Docker Compose e Grafana | Configuração + verificador | **Pendente em runtime** |
| Relatório, STRIDE, SBOM, CI, handoff | Arquivos disponíveis | CI não foi executado no GitHub nesta sessão |
| Direitos sobre fonte original / revogação de segredos | Atenção documentada | **Exige verificação humana** |

Veja `evidence/generated/RELEASE_GATE_V11.json`: os gates são binários e representam **evidência disponível**, não porcentagem de implementação, previsão de nota ou probabilidade de aprovação.

## 4. O que mudou na V11

- `integration/test_original_http_stubbed.py`: nove casos de **HTTP Flask real em loopback**, com mock explícito do Firebase para evitar uso de credenciais. Compara o snapshot upstream e o backend corrigido; não finge ser pentest do Firebase.
- `integration/run_original_http_stubbed.py`: runner falha se houver casos ignorados; produz JSON detalhado só após execução.
- `.github/workflows/ci.yml`: job independente para instalar Flask/Flask-Cors e rodar as provas HTTP antes/depois, além do teste do Firebase Emulator já existente.
- `frontend/src/api.ts`: tipos de login normalizados; perfil convertido para texto e bloqueio de consulta quando não há usuário, evitando `Bearer undefined`.
- `tests/test_v11_traceability.py`: 13 testes de rastreabilidade e prevenção de falsas alegações.
- `integration/test_official_emulators.py`: corrigida a expectativa de mensagens previamente inseridas, além de evitar corrida na escolha da porta HTTP. `tests/test_emulator_suite_v11.py` adiciona 4 testes offline de consistência; **a execução real com Firebase continua pendente**.
- `scripts/verify_v11.sh`: comando único para testes offline, prova Nginx e gate; a etapa Flask executa somente quando bibliotecas existem.
- `scripts/release_gate_v11.py`: oito critérios separados, distinguindo Flask com Firebase simulado, emuladores oficiais e runtime Docker.
- `docs/RELATORIO_PENTEST_V11.md`: nova matriz com severidade preliminar, causas e níveis de evidência.

## 5. O que significa cada nível de prova

- **Código encontrado** não prova exploração real.
- **Handler sintético** executa a lógica do upstream com dependências falsas; dá suporte à causa raiz, mas não a validação HTTP.
- **Flask HTTP com Firebase sintético** exercita roteamento, HTTP, CORS e resposta reais, mas **não** as regras de segurança do Firebase real.
- **Flask com Firebase Emulator** comprova integração com os emuladores locais sem tocar produção.
- **Docker/Nginx** só é considerado validado após execução da stack completa.
- **Deploy real** e uso de serviços de terceiros não são necessários para os requisitos mínimos; precisam de consentimento e segurança adicionais.

## 6. Como rodar — Fedora (sem credenciais)

Na raiz do projeto:

```bash
bash scripts/verify_v11.sh
```

Se quiser executar a etapa adicional E3 em ambiente isolado:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install 'Flask>=3,<4' 'Flask-Cors>=4,<6'
python3 -m integration.run_original_http_stubbed
```

Para o Flask **original com emuladores Firebase locais** (requer Java, Node, Firebase CLI e dependências Python):

```bash
python3 -m pip install -r backend/requirements.txt
bash scripts/verify_official_emulators.sh
```

Para Compose, em ambiente com Docker instalado:

```bash
bash scripts/start_docker.sh
python3 scripts/verify_docker_stack.py --failover
```

Para React:

```bash
bash scripts/verify_frontend_build_v10.sh
```

**Não** rode Firebase contra o projeto dos autores e **não** abra o laboratório sintético para a Internet.

## 7. Decisões que estão sob seu controle

- **DEC-01 – Fonte e arquitetura:** continuar preservando React/Flask/Firebase do CourseSphere original; migração para Rails só se houver motivo específico (recomendação atual: **não migrar**).
- **DEC-02 – Critério de achado válido:** reportar separadamente riscos estáticos, handlers sintéticos, HTTP com mocks e integrações em emuladores (recomendado: **sim**).
- **DEC-03 – Deploy:** priorizar execução local gratuita; qualquer exposição pública exige revisão de segurança (recomendado: **local**).
- **DEC-04 – Produto visual:** manter design sóbrio, claro, acessível, sem neon ou elementos futuristas (decisão do usuário: **sim**).
- **DEC-05 – Redistribuição:** antes de publicar um fork, conferir autorização/licença e se não existem credenciais ou dados de terceiros; solicitar revogação da credencial exposta no upstream.

## 8. Próximas prioridades, segundo o edital

1. **Altíssima:** fazer as provas E3 passarem com Flask instalado; depois fazer E4 passar com Firebase Emulator e registrar antes/depois por HTTP, categoria OWASP, severidade e impacto; não presumir que o mock satisfaz a banca.
2. **Alta:** verificar 5 achados aplicáveis ao CourseSphere original (2 categorias) e 3 correções de causa raiz com regressões provadas.
3. **Média:** testar o Docker + duas réplicas + Nginx + Prometheus/Grafana no Fedora; coletar métricas SLIs/SLOs e prints verdadeiros.
4. **Média:** build React e corrigir erros de compilação/integração.
5. **Entrega:** revisar o relatório executivo/técnico, histórico Git, licenças, credenciais, README e ordem de apresentação da banca.
6. **Extras:** polir Security Arena e Evidence Engine sem deslocar o foco das provas.

## 9. Checklist de aceitação final

- [ ] 5 vulnerabilidades do original sustentadas por prova reproduzível e impacto de negócio
- [ ] 2+ categorias OWASP documentadas
- [ ] 3 correções de causa raiz com testes antes/depois
- [ ] 2 melhorias adicionais de hardening comprovadas
- [ ] Logs JSON + saúde + métricas + 2 SLIs/SLOs demonstrados
- [ ] Dois backends no Docker + balanceamento verificado
- [ ] Relatório compreensível por gestão e por engenharia
- [ ] SAST/SCA em CI, se possível com relatório real
- [ ] Build React e integração Flask/Firebase com dados sintéticos
- [ ] Conferência de licença, eliminação/rotação de segredos e revisão do ZIP para vazamentos

**Não há garantia de aprovação** e porcentagens antigas relativas ao protótipo independente não representam este estágio do desafio.
