# CourseSphere — DevOps / SRE / AppSec

Aplicação CourseSphere (frontend React e API Flask) com autenticação Firebase,
quota compartilhada, Nginx com duas réplicas e observabilidade Prometheus/Grafana.
Esta é a **única versão de código publicada na branch principal**.

## Componentes

- `frontend/`: aplicação React/Vite.
- `backend/`: API Flask, validação, autenticação e quota.
- `ops/`: proxy, métricas, alertas e dashboards.
- `compose.official.yaml`: stack Flask/React local (exige Firebase configurado).
- `compose.official.observability.yaml`: overlay Prometheus/Grafana.
- `compose.r16.existing-emulator.yaml`: piloto com Auth/RTDB Emulator já existente.
- `scripts/`: inicialização e verificações relevantes.
- `tests/`: regressão de segurança, autenticação e quota.

## Verificar

```bash
python3 -m unittest tests.test_security_core tests.test_firebase_configuration_r6 tests.test_shared_quota_final tests.test_r14_scoped_fixture_cleanup tests.test_r14_proof_fail_closed -q
cd frontend && npm ci && npm run build
```

## Executar localmente

```bash
docker compose -f compose.official.yaml up -d --build
```

A stack oficial sem emuladores não oferece fluxos autenticados completos.
Para a demo com Firebase Emulator existente, siga `scripts/deploy_r16_docker_pilot.py`
e use apenas um projeto Firebase `demo-*`, no ambiente local e autorizado.
A porta de acesso do piloto é `http://127.0.0.1:18081`.

A observabilidade local utiliza `scripts/start_official_observability_v19_8.sh`.

## Segurança e procedência

Não configure credenciais reais na imagem, no código ou no Git. Dados de terceiros
(Cornell/Kaggle), `.env`, logs, evidências locais e builds são excluídos.
Esta entrega deriva de CourseSphere (LambdaAK); verifique as permissões de uso.
Testes sintéticos e verificações de código não equivalem a homologação externa.
