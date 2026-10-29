# CourseSphere — Entrega AppSec / DevOps / SRE — revisão final R42

> **Estado:** código de entrega derivado de **R16_DOCKER_PILOT / R15_WORK**, **não** da V19.15 principal. Esta árvore preserva a aplicação React/Flask/Firebase e o laboratório sintético separado. Uma release exportada não significa que os requisitos foram homologados.

## Stack da entrega

- Backend original Flask com autenticação **Bearer Firebase**, validação estrita de JSON, quota compartilhada por transações no Firebase RTDB, health/readiness e métricas Prometheus privadas.
- Frontend React/TypeScript/Vite com login Firebase e rotas relativas ao gateway.
- Docker Compose `compose.r16.existing-emulator.yaml`: duas instâncias Flask, frontend Nginx, gateway, Prometheus e Grafana, com portas publicadas apenas no loopback.
- Firebase Emulator **já existente** em rede Docker de demonstração, validado pelo código R16. Não carregar credenciais reais no modo demo.
- CI Python/Node e outros testes no repositório, além dos verificadores do piloto.

## Evidência e critérios obrigatórios

| Critério | Situação | Prova necessária para nota |
|---|---|---|
| 5 achados upstream em 2 categorias OWASP | **Pendente de aceite formal** | Fonte upstream fixa, cinco causas independentes, reprodução controlada e matriz antes/depois |
| 3 correções de causa raiz | Código para diversas causas implementado | Execução antes/depois correspondente a três achados aceitos |
| 2 hardenings independentes | Implementados | Exibir testes de entrada, token e configuração de serviços |
| Observabilidade, logs, SLIs e SLOs | Implementados | Mostrar métricas de duas instâncias, alertas e dashboard provisionado |
| 2 réplicas Flask, balanceamento e failover | Compose e verificador implementados | `R16_DOCKER_*/RESUMO.json` com `validated:true`, testes reais e recuperação A |
| Quota RTDB distribuída | Código transacional implementado | Prova com emulador real e duas instâncias: 20 aceitas/4 negadas, cleanup seguro |
| Frontend/CI | Presente | `npm ci`, build React e workflow GitHub Actions no repo publicado |
| Segredos e supply-chain | Preflight offline e Dependabot presentes | Revisão humana, rotação se aplicável, auditoria npm remanescente |

**Não conte cinco achados automaticamente**: cadastro via Admin SDK, tratamento de erros, transporte de token, dados de credenciais, validação de tamanho e estado de sessão têm modelos de ameaça diferentes; algumas evidências históricas não confirmam impacto. Os relatórios da própria R16 alertam sobre essa diferença. Fonte de evidência original: `RELATORIO_SEGURANCA_ATUAL.md`, `docs/SECURITY_MATRIX_V14.md` e dossiês `audit/`.

## Execução local (sem alterar serviços)

```bash
python3 -m unittest tests.test_firebase_configuration_r6 tests.test_v17_shared_quota tests.test_security_core -q
node scripts/test_session_gate_v19_2.cjs
node scripts/test_profile_session_runtime_v19_2.cjs
```

## Docker já existente

O piloto Docker da R16 pode **já estar rodando**. O `release_tools/r40_readonly_pilot.py` foi incluído para inspecioná-lo sem alterações. Não execute `docker compose down -v`, `docker system prune` ou `up` contra um projeto existente sem revisar volumes e contêineres.

A prova ativa opcional original `scripts/deploy_r16_docker_pilot.py --verify-only` testa Firebase e failover; pode criar/remover dados sintéticos e parar/reiniciar a réplica A temporariamente. Execute somente com consentimento e certeza de que se trata do Emulator `demo-coursesphere-vlab`.

## Publicação GitHub

- O assistente **não faz commit** no repositório: a publicação acontece apenas no Fedora e sob sua autorização.
- O finalizador produz uma **nova branch**, sem `force`, sem mudar `main`, sem apagar branches e sem enviar logs nem evidências privadas.
- Sem licença/consentimento explícito para redistribuir o upstream, publique somente conteúdo que você tem direito de compartilhar. Dê preferência a repositório privado e verifique a licença/copyright dos datasets.

## Integridade e limites

Cada execução cria pasta própria em `~/V-Lab DevOps/CourseSphere_ENTREGAS_FINAIS`, com arquivo ZIP completo da cópia sanitizada e `evidencias/RESUMO_FINAL.json`. Os resultados são vinculados à execução atual, **não** às contagens históricas R25–R37 de módulos isolados. Nenhuma limpeza é feita na release original nem no Docker; diretórios temporários reconhecidos são movidos para quarentena, não apagados.

## Ajuste R42

O dataset externo Cornell/Kaggle de 72,4 MB não é incluído no checkout exportado, seguindo o `.gitignore` presente no repositório. A fonte R16 no Fedora não é modificada. O GitHub recebe uma branch nova derivada da `main`, permitindo comparação e PR sem histórico desconectado. A análise de segredos lê arquivos grandes em streaming e não classifica tamanho como segredo.
