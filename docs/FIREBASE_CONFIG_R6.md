# R6 — Firebase Auth/RTDB: configuração à prova de ambiguidades

## Modelo de ameaça

Esta correção é para o backend Flask **original** do CourseSphere, não para o CRUD didático. Configuração ambígua de emulador (por exemplo `usuario@localhost:9099`) pode parecer local ao analisar apenas `urlsplit().hostname`, embora bibliotecas ou ferramentas interpretem a autoridade de modo diferente. Um processo Python também pode herdar um Firebase Admin default app já inicializado para outro banco/projeto. A R6 reprova ambos os casos explicitamente.

## Contrato da R6

- `COURSESPHERE_USE_FIREBASE_EMULATORS` aceita somente `0` ou `1`. Valores como `true`, `yes` ou vazio são recusados, em vez de mudar silenciosamente para produção.
- Com `1`: exige `GCLOUD_PROJECT` no formato `demo-*`, `FIREBASE_AUTH_EMULATOR_HOST` e `FIREBASE_DATABASE_EMULATOR_HOST` como **localhost:porta**, **127.0.0.1:porta** ou **[::1]:porta**; porta 1–65535. Rejeita login embutido, URL com esquema, path, query, fragmento e credenciais de service account.
- Com `0`: exige `FIREBASE_CREDENTIALS_FILE` explícito e `FIREBASE_DATABASE_URL` HTTPS com domínio RTDB oficial (`*.firebaseio.com` ou `*.firebasedatabase.app`), sem login embutido, path, query ou fragmento. Conexões de produção **não foram realizadas** nesta rodada.
- O Firebase Admin default app só pode ser reutilizado se o banco e (no modo emulador) projeto/credencial local forem compatíveis. Caso contrário, retorna erro antes de qualquer uso pela aplicação.
- A geração das provas Firebase Auth/RTDB e Prometheus de duas réplicas agora vincula SHA-256 ao módulo de configuração. A prova Auth/RTDB também inclui o próprio executor, fechando lacuna de rastreabilidade.
- O gate exige coerência entre `application_ready_for_authenticated_traffic` e os estados observados de readiness A/B; booleanos não podem ser substituídos por `1` ou `0` como se fossem atestados.

## Exemplo de modo local emulador (apenas operadores)

```
COURSESPHERE_USE_FIREBASE_EMULATORS=1
GCLOUD_PROJECT=demo-coursesphere-vlab
FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000
```

Não adicionar `FIREBASE_CREDENTIALS_FILE` no modo emulador; não publicar portas. A compatibilidade efetiva da R6 com Docker e Firebase Emulator precisará ser comprovada em CI/operação antes de reivindicar aceite.

## Provas executadas

- Testes de configuração SDK-free e do ramo real `_firebase()` com bibliotecas sintéticas e rede bloqueada; não houve leitura de certificado ou contato com serviços reais.
- A suíte offline da base V19.9 derivada passou; CI recebeu passo dedicado para R6.
- Testes Node e Nginx executados separadamente contra simuladores locais, não equivalem a Auth/RTDB ou build React integrado.

**Portabilidade:** não aplicar `backend/firebase.py` da R6 integralmente sobre V19.15 sem um merge de três vias, pois a V19.15 contém código de atestação e outras adaptações posteriores. Portar a validação e os testes, depois rever os hashes de evidência e reexecutar o gate.
