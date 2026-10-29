# CourseSphere R12 — ingresso JSON seguro no Flask original

**Base real:** R11 derivada da V19.9. **NÃO substitui a V19.15** e NÃO constitui certificado de deploy.

## Correção implementada

`backend/strict_request_json.py` valida corpos JSON dos quatro handlers POST do **Flask original** (`/users/info`, `/users/query`, `/hash`, `/chats/<chat_id>/messages`).

- Recusa chaves JSON duplicadas, inclusive em objetos aninhados, `NaN`/`Infinity` e floats convertidos em infinito (`1e9999`), Unicode inválido, profundidade/número de nós excessivos, JSON extra e corpos acima de 32 KiB.
- Exige `application/json`, respeita `MAX_CONTENT_LENGTH` do Flask e conserva erros seguros.
- Mantém a verificação de autenticação antes da leitura do corpo no endpoint de perfil. Nenhuma quota é debitada após validação inválida.
- O harness AST legado é adaptado para isolar o parser HTTP; os testes da R12 exercitam o parser verdadeiro e os testes HTTP com Flask estão no CI.
- O utilitário R11 de quota passa a vincular o hash do novo parser como fonte relevante; provas de quota antigas não certificam estes bytes.

## Verificar localmente

```bash
cd CourseSphere_V19_9_R12
bash scripts/verify.sh
python3 -m scripts.prove_r12_strict_json
python3 -m scripts.release_gate_r12 --require-r12
```

**Com Flask + Flask-Cors instalados e Firebase completamente simulado**:

```bash
python3 -m integration.run_r12_flask_strict_json
```

O teste acima exige Flask real; ausência das dependências resulta em erro, e cenários ignorados NÃO são PASS.

## Portabilidade

O ZIP completo contém o código derivado da V19.9 R11, acrescido de R12. O patch `CourseSphere_V19_9_R12_ENGINEERING.patch` aplica-se **apenas** à base R11 exata. Para a V19.15, faça merge seletivo depois de comparar `backend/endpoints.py`, `backend/security_core.py`, `tests/origin_harness.py`, CI e os executores de prova. NÃO substitua a V19.15 pelo ZIP integral.

## Limites e risco residual

- Não foram executados nesta rodada Docker, Firebase Admin, Auth/RTDB Emulator, Prometheus/Grafana reais nem build completo do React.
- Testes offline não demonstram segurança de rede/proxy HTTP; os testes Flask HTTP ficam configurados no CI e não foram aprovados aqui.
- O novo parser não substitui regras RTDB, autorização de servidor, avaliação de vulnerabilidades npm ou testes de concorrência distribuída.
- O gate da base derivada deve permanecer `ready_for_submission=false`; nenhum teste sintético recebe pontos extra de aceite.
