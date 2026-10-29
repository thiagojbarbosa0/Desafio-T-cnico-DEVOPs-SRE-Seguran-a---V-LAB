# CourseSphere R14 — pacote único, sem sobrescrever V19.15

**O arquivo principal é `CourseSphere_R14_PACOTE_UNICO.zip`.** Extraia-o numa pasta nova. Ele contém o frontend, o Flask original endurecido, a stack Compose/Nginx, os testes, o dossiê AppSec, as evidências e o executor para Fedora. É uma derivação da V19.9/R13, **não a integração da V19.15 principal**.

Para diagnóstico offline, com a pasta extraída, execute:

```bash
bash EXECUTAR_NO_FEDORA.sh
```

Não há instalação obrigatória nem Docker nesse comando. Para permitir a instalação de dependências no projeto e tentar a integração Firebase Emulator (quando houver rede e Java/Node), execute `bash EXECUTAR_NO_FEDORA.sh --full`. Este modo ainda **não inicia automaticamente** o Compose com nome potencialmente compartilhado com outro checkout.

O relatório local é criado em `~/CourseSphere-Diagnosticos/<data>/RESUMO.json`. No Fedora, preserve esse relatório e não compartilhe logs brutos com possíveis tokens sem revisão. O CI fornece o teste completo `bash scripts/verify_official_emulators.sh`, que exige um projeto local `demo-coursesphere-vlab` e duas réplicas Flask.

A R14 acrescenta teardown de contas e RTDB restrito ao UID sintético, verificação de remoção por leitura, token apenas no coordenador, testes de falha de limpeza e release gate separado `python3 -m scripts.release_gate_r14`. O gate com `--require-r14` deve **falhar** quando o Firebase Emulator não foi efetivamente executado, impedindo uma aprovação fictícia.

**Escopo verificado no ambiente de desenvolvimento:** 807 testes Python; três scripts Node; duas provas de Nginx real com serviços upstream sintéticos; sintaxe TypeScript; checagem estrutural do lockfile. Não houve execução Flask/Firebase Admin, Docker, Prometheus/Grafana integrados ou `npm ci`/build React completo nesta sessão.

Detalhes no `HANDOFF_R14_2026_10_27.md` e `DOSSIE_APPSEC_R13.md`. Antes da submissão: integrar à V19.15 exata, executar os testes de serviços completos, revisar dependências e confirmar licença/rotação de credenciais antigas.
