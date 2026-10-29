# Design V8 — produto normal, sem estética sci-fi

**Decisão UX-08, aprovada pelo pedido de 22/10/2026:** abandonar a estética de neon, brilhos, gradientes de cibersegurança, efeitos futuristas e textos de “mission control”. Preferência: aplicação corporativa/SaaS padrão, bonita, sóbria e clara, com funcionalidades reais e layout responsivo.

## Linguagem visual

- Fundo cinza claro (`#f6f7f9`), superfícies brancas, bordas suaves e sombra mínima.
- Azul discreto (`#254a83`) só para estados de ação, verde para status positivo, vermelho para erro.
- Tipografia nativa do sistema: sem fontes externas, mais rápido e independente de redes/CDN.
- Sidebar estável no desktop, navegação rolável horizontalmente no celular.
- Quatro telas: Visão geral, Testes de segurança, Cursos e permissões, Confiabilidade.
- Interface sem métricas de testes fixas/enganosas. O estado da API e a instância são coletados de `/api/ready`; os SLOs têm rótulo claro de **metas propostas**.

## Funcionalidades implementadas

1. Navegação de telas reais, com títulos e aria-current atualizados.
2. Lista de cursos da API sintética, com renderização via `textContent` (sem HTML injetado).
3. Teste de autorização de proprietário: autenticação temporária no sandbox, GET do recurso, PUT sem modificar conteúdo e conferência do HTTP 403 ou 200 conforme caso.
4. Exportação local de JSON de evidência **sem token** (ator, recurso, HTTP esperado/recebido, request ID e escopo explícito).
5. Diagnóstico HTTP de prontidão, resposta/instância exibidas, e status offline quando necessário.
6. Feedback acessível (`aria-live`) e `prefers-reduced-motion`.

## QA executado

- Chromium renderizou HTML/CSS/JS reais com API **mockada** para screenshots desktop, segurança, cursos e mobile.
- Sem erros JavaScript nesse ensaio; 390px com `scrollWidth === innerWidth`.
- Testes reais da API/gateway via `unittest` e script HTTP no localhost em separado.
- Política de rede impediu o Chromium de acessar localhost diretamente; e2e real de navegador é **pendência de Fedora**.

## O que não é esta interface

Não substitui nem restiliza o frontend React/TypeScript original, que depende de Firebase. É o painel do laboratório AppSec/SRE local. Qualquer alteração visual do React de origem deve ser decidida e testada à parte para não mascarar ou introduzir regressões funcionais.
