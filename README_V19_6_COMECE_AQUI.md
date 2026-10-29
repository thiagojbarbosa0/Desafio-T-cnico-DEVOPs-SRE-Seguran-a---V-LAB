# CourseSphere V19.6 — comece aqui

Esta versão continua do **CourseSphere original** (React/TypeScript + Flask + Firebase), com um laboratório AppSec/SRE **isolado** que não substitui o upstream.

## O que mudou

- O Flask agora valida `ALLOWED_ORIGINS` por uma política explícita. `*`, URLs com usuário/senha, caminhos, query strings e HTTP remoto deixam de ser aceitos silenciosamente. HTTP local (`localhost`, `127.0.0.1`, `::1`) continua funcionando com o React do Vite.
- Nova suíte de **5 testes reais de Flask/flask-cors** (WSGI) preparados para GitHub CI/Fedora e **13 regressões Python offline** nesta rodada (incluindo provas do gate).
- Evidências de Flask, Firebase Emulator e réplicas Flask/Nginx agora incluem hash de `backend/cors_policy.py`. Uma prova antiga dessa área **não pode validar a nova versão**.
- Novo verificador único: `bash scripts/verify_local_v19_6.sh`. Sem Flask instalado, **ele marca como não executado**, sem inventar sucesso. Nenhum Docker, Firebase real ou conta de terceiro é necessário para o núcleo offline.

## Conferir a entrega e executar localmente

Na pasta extraída, **antes de executar qualquer teste**, verifique o manifesto SHA-256:

```bash
sha256sum --quiet -c MANIFEST_SHA256_V19_6.txt
bash scripts/verify_local_v19_6.sh
```

O primeiro comando só é esperado passar **antes** dos testes: os scripts regeneram artefatos em `evidence/generated/`, de forma que algumas somas mudam legitimamente depois da execução. Não confundir esses arquivos alterados com corrupção do ZIP original. A integridade do ZIP também é checada separadamente.


Se quiser executar os testes HTTP opcionais com **Flask real e Firebase sintético** no Fedora, dentro do projeto:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'Flask>=3,<4' 'Flask-Cors>=4,<6'
PATH="$PWD/.venv/bin:$PATH" bash scripts/verify_local_v19_6.sh
```

Esses comandos de integração **não** precisam de Firebase real, credenciais ou serviços pagos.

## Configurar CORS corretamente

```bash
export ALLOWED_ORIGINS='http://localhost:5173,http://127.0.0.1:5173'
# Para ambiente HTTPS: export ALLOWED_ORIGINS='https://app.example.org'
```

Somente origens completas sem caminho ou barra final; não usar `*`. Para acesso remoto, usar HTTPS. Isso configura acesso no navegador, **não concede autorização**; as rotas continuam exigindo Firebase Auth onde aplicável.

## Provas pendentes para aprovação

1. Executar Flask original + Firebase Emulator, confirmar as permissões RTDB e quotas.
2. Executar build React/TypeScript atual e testes de sessão no navegador.
3. Executar Docker Compose, Nginx, duas réplicas, Prometheus e Grafana.
4. Consolidar **5 achados independentes realmente aplicáveis ao upstream**, com severidades justificadas, e **3 correções de causa raiz** comprovadas. F01/F02 dependem da política funcional; não alegar impacto ainda não provado.
5. Verificar permissão de redistribuição e informar privadamente os responsáveis sobre a credencial do snapshot upstream.

**O projeto NÃO está liberado para submissão final.** Leia `HANDOFF_V19_6.md` para estados, riscos e comando de continuidade.
