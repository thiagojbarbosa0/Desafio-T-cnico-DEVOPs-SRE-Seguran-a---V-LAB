# CourseSphere R8 — continuidade sobre V19.9/R7

**Leia antes de usar:** este ZIP é uma evolução do laboratório derivado de **V19.9**, não uma V19.15 integral. Não sobrescreva o backend original Flask/Firebase nem o CI da V19.15 com os arquivos deste projeto sem comparar ambos os códigos.

## Alteração P0 — auditoria atômica

Se o SQLite aceitava a mudança de um curso/aula e falhava ao escrever o evento de auditoria na conexão seguinte, o estado era alterado sem rastro. A R8 insere o evento de **sucesso** na mesma transação de criação, edição ou exclusão (6 operações) e remove as gravações duplicadas do controlador. Se o registro falhar, o `connect()` faz rollback e a API responde com erro sem persistir a mutação. Triggers bloqueiam UPDATE e DELETE de eventos por SQL ordinário.

**Não é log imutável ou resistente a adulteração por administrador do banco/host**: quem controla o arquivo SQLite pode remover triggers ou alterar o próprio arquivo. Para produção seria necessária trilha de auditoria com armazenamento externo e controles de acesso adequados.

## Alteração P1 — request parsing e readiness

Rejeita `Authorization`, `Host`, `Content-Type` e `Content-Length` duplicados, `Transfer-Encoding` não suportado e `Content-Length` não canônico; isso reduz divergências entre parsers do proxy e backend. Restringe `INSTANCE_ID` a rótulo seguro antes de inseri-lo em headers/logs/métricas. `/api/ready` devolve 503 genérico se o SQLite falhar, enquanto `/api/health` continua medindo apenas liveness.

## Como testar no checkout R8

```bash
bash scripts/verify.sh
python3 -m scripts.prove_r7_dual_replica_auth
python3 -m scripts.prove_r8_atomic_audit
python3 -m scripts.record_offline_v16
python3 -m scripts.release_gate_r8 --require-r8
```

Testes de Nginx opcionais (precisam do binário instalado):

```bash
python3 scripts/prove_nginx_native.py
python3 scripts/prove_official_nginx_contract_v19_7.py
```

CI incorpora os testes e o comprovante da R8. A prova do R8 tem **peso zero no aceite formal**, pois usa Python HTTP + SQLite sintéticos, e não Flask/Firebase/Docker. Não utilize credenciais reais e não publique o laboratório na internet.
