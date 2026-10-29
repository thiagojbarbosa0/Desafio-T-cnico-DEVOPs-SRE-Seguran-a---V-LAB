# CourseSphere V19.7 — comece aqui

**Projeto:** avaliação de AppSec/SRE sobre o CourseSphere original (Flask + React/TypeScript + Firebase Auth/RTDB), com laboratório sintético isolado apenas como demonstração auxiliar.

**Principais entregas novas:** implantação Docker opcional do Flask original em duas réplicas + React + Nginx (não substitui o Docker didático), prova de roteamento/failover usando Nginx real e serviços simulados, verificador de execução Docker com evidências SHA-256 e jobs de CI separados. Visual SaaS discreto preservado.

## Para entender o projeto

Leia `HANDOFF_V19_7.md` e `docs/STACK_FLASK_ORIGINAL_V19_7.md` antes de executar contêineres. Os arquivos `HANDOFF_V19_6.md` e anteriores são históricos. **Não há credenciais Firebase/OpenAI dos autores** e não é necessário fornecê-las.

## Validação local (sem Docker)

```bash
# Primeiro, antes dos testes, se o ZIP veio da entrega:
sha256sum --quiet -c MANIFEST_SHA256_V19_7.txt
bash scripts/verify_local_v19_7.sh
```

O segundo comando altera arquivos de evidências geradas: isso é esperado, e não invalida o ZIP original, mas a verificação de manifesto deve ocorrer **antes** da execução.

## Stack Docker didática vs original

| Stack | Comando | O que demonstra |
|---|---|---|
| Didática independente | `docker compose up -d --build` | CRUD fictício, autenticação local sintética, demonstração de balanceamento |
| **Flask original** | `docker compose -f compose.official.yaml up -d --build` | Duas instâncias Flask originais com Gunicorn, React original e Nginx local em `http://127.0.0.1:8081` |

**O login no segundo ambiente NÃO é demonstrado sem Firebase autorizado/emulado.** O perfil Firebase Admin não é configurado nessa stack; o healthcheck comprova apenas liveness. Prometheus/Grafana do primeiro ambiente não monitoram o Flask original.

Para testar o contêiner original *depois* de subir a stack:

```bash
python3 scripts/verify_official_docker_v19_7.py --failover
```

A ferramenta desliga temporariamente a primeira réplica e a reinicia ao terminar. Requer Docker Compose V2 e uma porta 8081 livre. Se retornar erro, não marque essa validação como concluída; consulte `evidence/runtime/OFFICIAL_DOCKER_V19_7.json` (sem tokens).

## O que ainda impede submissão

Evidências integradas com Firebase Emulator, build React completo da versão atual, Docker original executado, prometheus/grafana efetivamente ligados ao Flask, cinco achados independentes do upstream e três correções formalmente aceitas/reproduzidas, além da licença/permissão e rotação de credenciais do upstream.

**Números de progresso:** `evidence/generated/RELEASE_GATE_V19_7.json`, gerado a partir do código local. Percentuais são critérios internos, não previsão de nota.
