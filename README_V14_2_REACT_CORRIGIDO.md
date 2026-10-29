# CourseSphere V14.2 — correção do build React identificada no Fedora

Este pacote é uma correção **incremental sobre a V14.1**. Mantém o backend, a prova HTTP Flask e a direção visual já acordada. A pasta raiz continua se chamando `CourseSphere_V14` para reduzir diferenças nos comandos.

## Por que esta versão existe

Em 23/10/2026, o Fedora compilou o frontend com `npm run build` e encontrou **11 erros TypeScript** (não são 11 vulnerabilidades): parâmetros e imports não utilizados; ausência de tipos para `jquery`; componente `TellMeAboutYourself` com props inconsistentes; e `sectionNumber` obrigatória mesmo ausente das recomendações. A mesma execução comprovou os **15 casos HTTP Flask** (`validated=True`), com Firebase simulado.

## O que foi corrigido

- `Nav.tsx`, `App.tsx` e `Dashboard.tsx`: imports/variáveis/parâmetros inutilizados retirados ou identificados como ignorados.
- `api.ts`: acesso aos campos de login/cadastro por DOM tipado, eliminando a dependência de tipagens externas do jQuery para a compilação.
- `Dashboard.tsx`: campo `about` controlado pelo estado React; `year`, `college` e `about` enviados do estado para a API, em vez de ler o DOM incidentalmente.
- `interfaces.d.ts` e `CourseCard.tsx`: `sectionNumber` opcional e renderização condicional.
- Testes de regressão ajustados às novas invariantes, com testes adicionais cobrindo os problemas reportados.
- Validador completo de sintaxe TS/TSX, e script de build que **só grava evidência de sucesso após `npm run build` retornar código zero**.
- Runner do Fedora reaproveita a `.venv` com Flask na Etapa 1, para não sinalizar um falso `NOT TESTED` quando a biblioteca existe no ambiente virtual.

## Passo 1 — próximo teste no Fedora (sem Docker)

Abra o terminal **dentro da pasta `CourseSphere_V14` deste ZIP novo**:

```bash
bash scripts/verify_frontend_build_v14_2.sh
```

O script usa `npm ci` com `package-lock.json` e executa `tsc -b && vite build`. Se passar, cria `evidence/generated/FRONTEND_BUILD_V13.json`, com hash da árvore frontend (o nome V13 é mantido por compatibilidade com o release gate).

**Se falhar:** copie a saída a partir de `npm run build` e envie. Não mude `tsconfig` para desativar erros nem use `--force` por padrão.

**Se passar:** continue com `bash scripts/fedora_validation_v14.sh --install-deps --with-docker` somente se o Docker estiver instalado e operacional. Para o teste sem Docker, use `bash scripts/fedora_validation_v14.sh --install-deps`. Esta etapa pode instalar dependências gratuitas, iniciar emuladores locais e gerar logs.

## Escopo do resultado

Nesta sessão de preparação, a análise de sintaxe TypeScript foi executada, e os testes Python do laboratório foram executados. O **build completo do React não foi validado neste ambiente**, pois a instalação npm não encontrou todos os pacotes; a confirmação dependerá do Fedora. Os testes Flask/Firebase de ponta a ponta e Docker/Grafana são etapas distintas.

O relatório de segurança não é modificado nesta versão: **ainda faltam provas integradas de todas as categorias obrigatórias**, além da revisão manual dos achados e autorização de redistribuição da origem.
