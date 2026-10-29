# CourseSphere V19.2 — Handoff de continuidade após o Work

**Base auditada:** `CourseSphere_V19_1_WORK.zip` (entrega do Work em 23/10/2026). Esta versão preserva as correções e provas da V19.1 e acrescenta tratamento de sessão no frontend. **Não está pronta para submissão.**

## 1. O desafio original e as prioridades

O desafio do V-Lab é de **AppSec + SRE no CourseSphere existente**, não de reconstrução da plataforma. A maior prioridade da banca é encontrar cinco vulnerabilidades reais em pelo menos duas categorias, com reprodução clara e justificativa, e corrigir pelo menos três causas raízes. Além disso: dois hardenings, logs e métricas/SLIs/SLOs, Docker com Nginx diante de duas instâncias, relatório e evidências. Scanners, CI, dashboards e experimentos de resiliência contam como diferenciais.

O repositório upstream utiliza React/TypeScript/Vite, Flask, Firebase Auth/Realtime Database e SQLite. O laboratório Python de cursos e aulas é **sintético e separado** — suas falhas intencionais não substituem vulnerabilidades demonstradas no upstream. Preserve o design SaaS sóbrio sem efeitos neon e a execução local/custo zero.

## 2. O que o Work concluiu na V19.1 (ver handoff original)

- Corrigiu o tratamento de `RequestEntityTooLarge`: quatro endpoints agora devolvem **HTTP 413** com resposta genérica, em vez de engolir a exceção e responder 500 em três casos.
- Executou **227 testes offline**, **15 casos HTTP reais Flask/Werkzeug com Firebase simulado**, um teste de limite de corpo com quatro subcasos e **build React completo** (TypeScript + Vite) para o código V19.1.
- Executou **Nginx com duas réplicas** do Flask corrigido e Firebase simulado, além do laboratório sintético, com failover demonstrado; 40 requisições distribuídas e oito atendidas após desligar uma instância.
- Criou checkpoints, scanner básico de segredos e relatório mais rigoroso sobre os cinco achados: `docs/REVISAO_ACHADOS_WORK.md`.
- Registra **42% do aceite interno (4/8 gates)** para *aquele código*; não prova Firebase Emulator ou Docker/Grafana.

**Importante:** F01 e F02 continuam *condicionais à política de negócio*; Firebase Admin criar uma conta não equivale a conceder papel administrativo. F03, F05 e F06 têm evidências mais fortes. O defeito D01 das regras Firebase surgiu na versão derivada e não conta como achado do upstream.

## 3. Trabalho adicional implementado na V19.2

### Isolamento de sessões no frontend original

- `frontend/src/sessionGate.ts`: geração de sessão que invalida resultados de requisições assíncronas após logout ou troca A→B→A, mesmo quando o UID inicial reaparece.
- `frontend/src/components/UserChats/UserChats.tsx`: limpa a lista imediatamente a cada transição de autenticação, cancela a requisição anterior e impede que uma resposta de A seja exibida sob a conta B.
- `frontend/src/api.ts`: carrega/zera o perfil por sessão e verifica o UID antes/depois de operações assíncronas; chamadas de recomendação e gravação de conversa recebem UID esperado para não gravar conteúdo na conta errada após troca de identidade.
- `frontend/src/components/ChatInterface/ChatInterface.tsx`: limpa mensagens, IDs, entrada e avisos quando muda a identidade; despreza respostas obsoletas e desabilita envio sem autenticação.
- `frontend/src/components/nav/Nav.tsx`: aguarda `auth.signOut()` terminar antes de redirecionar; libera o listener ao desmontar.
- `scripts/test_session_gate_v19_2.cjs`: exercita o código TypeScript compilado, cobrindo A→B, A→B→A, logout e novas gerações do mesmo UID.
- `scripts/test_user_chats_runtime_v19_2.cjs`: executa o callback/effect compilado de `UserChats` com Firebase/React isolados, atrasando a resposta de A até depois do login de B. Confirma que A não aparece, B aparece e logout limpa a lista. **É teste de componente simulado, não teste E2E em navegador real.**
- `scripts/test_profile_session_runtime_v19_2.cjs`: executa a função real de carregamento de perfil compilada do TypeScript com Auth e HTTP sintéticos; testa atraso da resposta de A, transição para B e limpeza integral no logout.
- Pipeline `.github/workflows/ci.yml` executa os três testes de sessão após o build React. Alguns testes legados de contrato foram ajustados para verificar as novas garantias de UID/geração, em vez de procurar strings obsoletas.

### Verificações efetivamente executadas nesta rodada

- **227/227 regressões Python** aprovadas, com checks legados atualizados para novos contratos.
- Três testes Node (geração, `UserChats` e perfil), incluindo callbacks TypeScript reais com Auth/HTTP simulados: **PASS**.
- Checagem sintática TypeScript/TSX pelo parser: **PASS** (não é `tsc -b`).
- Nginx nativo real e laboratório sintético: **PASS**; 20/20 distribuição e oito requisições após falha.
- A evidência offline regenerada foi validada no controle.
- **Não executei build completo React V19.2**: `npm ci --offline` falhou porque o cache não contém `yocto-queue`, e a tentativa de instalação em rede não concluiu neste ambiente.
- **Não reexecutei os 15 HTTP Flask sobre o código V19.2**, mas os arquivos do backend original não foram alterados; resultados da V19.1 são históricos da mesma lógica de backend.
- **Não executei Firebase Emulator 21 casos nem Docker/Grafana aqui**. Não confundir com o teste de Nginx nativo.

### Progresso em duas bases distintas

- **V19.1 do Work:** aceite interno 42% (4/8) com build React verificado para aquele código.
- **V19.2 atual:** aceite interno **35% (3/8)** após modificar o React; a prova de build da versão antiga foi corretamente invalidada. Percentuais não são nota ou chance de aprovação. A estimativa histórica de implementação era 69%; não aumentei esse número sem validação funcional.

## 4. Reproduzir a V19.2 no Fedora

```bash
# Na raiz CourseSphere_V19 do pacote V19.2
python3 -m scripts.record_offline_v16
node scripts/test_session_gate_v19_2.cjs
node scripts/test_user_chats_runtime_v19_2.cjs
node scripts/test_profile_session_runtime_v19_2.cjs
bash scripts/verify_frontend_build_v14_2.sh  # npm ci + tsc -b + Vite; atualiza evidência
python3 -m scripts.release_gate_v19
```

As duas provas Node exigem `typescript` em `frontend/node_modules` (preparado por `npm ci`). Para evitar erro de dependências, rode o build antes dos testes de sessão num Fedora recém-extraído. A prova Node isolada é um teste de comportamento simulado, não substitui Playwright/Cypress/E2E com Firebase real.

Com Java 21+, dependências e rede para preparar os emuladores: `bash scripts/verify_official_emulators.sh`. Com Docker Compose instalado e funcionando: `docker compose --profile observability up -d --build` e `python3 scripts/verify_docker_stack.py --failover`. Nunca rode os emuladores apontando para o Firebase dos autores; o script exige ambiente demo/loopback.

## 5. Próximas prioridades — não ampliar escopo sem ganho de evidências

1. Fazer `npm ci`, `tsc -b` e `vite build` para V19.2; executar fluxo real A→B→logout no navegador contra Firebase Emulator e registrar evidências de isolamento.
2. Integrar os **21 testes do Firebase Emulator** com regras de RTDB e quotas distribuídas (o Work V19.1 ainda não os concluiu no ZIP recebido).
3. Executar **Docker + duas réplicas + Prometheus + Grafana + failover** e anexar provas com IDs de instância.
4. Consolidar o relatório final com **cinco vulnerabilidades upstream independentes**, em duas categorias, e **três correções de causa raiz**, não inflando os achados condicionais F01/F02.
5. Confirmar autorização/licença de redistribuição do upstream e tratar a credencial do snapshot original com o proprietário; nenhuma publicação foi realizada.

## 6. Segurança, escopo e limitações

- Sem segredos de terceiros, URLs de projetos Firebase reais ou deploy público.
- Mantenha todas as vulnerabilidades demonstrativas no laboratório isolado.
- Evidências anteriores permanecem no ZIP com proveniência; cada artefato precisa de hash correspondente ao código testado.
- Nunca afirmar aprovação integral com base em parser sintático, handlers sintéticos ou YAML existente.
- Handoff da V19.1 preservado em `docs/HANDOFF_WORK_V19_1.txt` para comparação histórica.
