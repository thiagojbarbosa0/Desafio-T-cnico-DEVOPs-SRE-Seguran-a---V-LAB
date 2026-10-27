# CourseSphere — Desafio Técnico DevOps / SRE / Segurança (V-Lab)

Laboratório de engenharia de segurança e confiabilidade aplicado a uma aplicação
**Flask + React**, com autenticação e banco de dados Firebase (emuladores para testes),
Docker Compose, Nginx, Prometheus e Grafana.

> **Status:** versão de trabalho **R16 Docker Pilot**, derivada da R15 Work / R14.
> Não equivale à fonte histórica **V19.15** integralmente consolidada.
> O Docker piloto precisa de validação final no ambiente Fedora; não está homologado.

## Arquitetura

- **`backend/`**: API Flask, validação, quotas, métricas e conectores Firebase.
- **`frontend/`**: aplicação React/TypeScript e build Vite.
- **`ops/`**: configurações Nginx, Prometheus, Grafana e regras Firebase.
- **`integration/`, `tests/`**: provas e regressões automatizadas.
- **`scripts/`**: verificadores, ferramentas de execução e release gates.
- **`dashboard/`**: dashboard didático independente.
- **`docs/`**: documentação arquitetural e operacional selecionada.

## Verificação de código (sem alterar outros contêineres)

```bash
python3 -m unittest discover -s tests -v
cd frontend && npm ci && npm run build
```

Alguns testes históricos pressupõem dados/evidências excluídos desta cópia pública e podem ser ignorados ou falhar sem esses insumos.
Os testes de integração Firebase requerem **somente emuladores locais de demonstração**.
Veja [`COMECE_AQUI_R16.md`](COMECE_AQUI_R16.md) para o piloto Docker isolado e seus pré-requisitos.
**Não** execute o Compose contra instâncias Firebase reais sem revisar a configuração.

## Estado das provas

- Regressão offline R16: 821 testes aprovados na preparação da entrega.
- Flask + emuladores Auth/RTDB e quota em duas réplicas: comprovados em testes locais.
- Build React e testes Node: aprovados nos checkpoints prévios.
- **Docker R16 integrado / Grafana / failover containerizado: pendente de evidência final.**
- Avaliação de cinco achados upstream e tratamento dos alertas npm restantes: pendentes.

Estes números são históricos; uma alteração de código exige nova execução e novas evidências.

## Segurança e dados

Este repositório contém **código e configuração de demonstração**, não deve conter
`.env`, chaves, tokens, contas reais, logs privados, históricos completos de execução
ou dados coletados de terceiros. O conjunto `backend/cornell-course-sphere-data/`
foi **intencionalmente excluído**: obtenha dados de exemplo autorizados de forma separada,
se algum fluxo do aplicativo depender deles.

Resultados privados devem permanecer fora do Git, em
`~/V-Lab DevOps/CourseSphere_EVIDENCIAS/`.

## Origem, autoria e licença

Projeto derivado de [LambdaAK/CourseSphere](https://github.com/LambdaAK/CourseSphere),
com adaptações para fins de avaliação AppSec/SRE. Preserve a atribuição dos autores
originais. **Não há licença de redistribuição verificada neste snapshot.** Confirme a
permissão aplicável antes de manter este repositório público. Nenhuma nova licença é
concedida implicitamente por este README.
