# CourseSphere R11 — prova de quota do Flask original por réplica

## O que mudou

A R11 parte da **R10 derivada da V19.9**, não da V19.15 principal. Ela acrescenta uma pequena identificação controlada ao Flask original e uma ferramenta independente para verificar o limite de 20 gravações autenticadas de perfil, distribuídas entre **duas réplicas Flask distintas** usando **Firebase Auth e RTDB Emulators locais**.

Arquivos de código alterados/criados:

- `backend/endpoints.py`: cabeçalho `X-CourseSphere-Replica`, com apenas `official_api_a`, `official_api_b` ou `unknown`. O cliente não controla esse cabeçalho de resposta.
- `scripts/verify_official_replica_quota_r11.py`: duas URLs de IP loopback, guardas `demo-*`, token via variável de ambiente; perfil sintético; 20 gravações alternadas; 21ª tentativa em A e B deve ser HTTP 429; verifica que a negação não mudou o valor salvo. Recusa mesmo socket, mesmo ID de réplica e alternância de identidade no mesmo socket.
- `scripts/release_gate_r11.py`: integra relatório opcional ao gate e exige hashes atuais quando requisitado `--require-r11`, **sem acrescentar pontos de aceite**.
- Dois módulos de testes unitários offline (21 casos) e dois arquivos de teste/runner de Flask HTTP real com Firebase **simulado** (4 casos preparados para CI).
- `.github/workflows/ci.yml`: testes offline sempre; testes HTTP Flask reais quando as dependências são instaladas no job apropriado.

## Executar agora — sem contas ou credenciais externas

```bash
bash scripts/verify.sh
python3 -m scripts.prove_r8_atomic_audit
python3 -m scripts.prove_r9_transport
python3 -m scripts.prove_r10_deadline
python3 -m scripts.release_gate_r11
```

O gate R11 **deve permanecer `r11_original_flask_emulator=false`** enquanto a prova original não for executada. Não marque o relatório como PASS manualmente.

## Prova integrada futura (somente ambiente de demonstração)

Pré-requisitos: dois Flask **originais**, em processos distintos, acessíveis por **portas diferentes e exclusivamente IPs loopback**; os dois servidores devem usar a **mesma instância do RTDB Emulator** e o **mesmo projeto `demo-*`**, mas nomes `COURSESPHERE_REPLICA_NAME` distintos (`official_api_a` e `official_api_b`). Tenha um token Firebase **emitido pelo Auth Emulator** para uma conta sintética nova. **Não use contas/segredos/URLs de produção.**

```bash
export COURSESPHERE_USE_FIREBASE_EMULATORS=1
export GCLOUD_PROJECT=demo-coursesphere-vlab
export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
export FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000
# Coloque o idToken do Auth Emulator numa variável de ambiente sem imprimi-lo.
read -rs COURSESPHERE_R11_FIREBASE_ID_TOKEN
export COURSESPHERE_R11_FIREBASE_ID_TOKEN
python3 -m scripts.verify_official_replica_quota_r11 \
  --replica-a http://127.0.0.1:18091 \
  --replica-b http://127.0.0.1:18092
python3 -m scripts.release_gate_r11 --require-r11
unset COURSESPHERE_R11_FIREBASE_ID_TOKEN
```

As portas 18091/18092 são **exemplos**; a R11 não altera o Compose, não cria encaminhamentos e não pressupõe que essas portas estejam prontas. A verificação precisa começar antes dos últimos 15 segundos de um minuto UTC e deve usar uma conta sintética **nova sem quota consumida**. O teste sobrescreve o perfil dessa conta. Nenhum token, UID ou conteúdo do perfil é gravado no relatório.

**Limites das evidências:** um ID de réplica HTTP não é prova criptográfica de identidade de imagem Docker; é preciso validar hashes dentro dos contêineres separadamente. O teste isolado com dois servidores HTTP falsos confirma a lógica do **verificador**, não a quota Firebase. O Flask instalado no CI é real, mas o adaptador Firebase no teste de cabeçalho é simulado. Nenhum desses resultados, isoladamente, autoriza submissão à banca.

## V19.15

O patch R10→R11 aplica-se à derivação R10 recuperada. **Não execute `patch` sobre a V19.15 principal sem revisar os conflitos**: preserve as mudanças posteriores no Flask, regras Firebase, Nginx e pipeline. A V19.15 nunca foi substituída nesta rodada.
