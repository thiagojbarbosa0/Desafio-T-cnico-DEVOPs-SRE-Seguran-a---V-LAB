# CourseSphere V-Lab — R6 (derivada da V19.9 real)

A R6 continua a base original V19.9 → R5. **Ela não é a V19.15**, e não substitui o trabalho da linha principal. Nenhum Docker/Firebase Emulator foi executado nesta rodada.

Alterações principais: validação fail-closed de hosts e modo Firebase, prevenção de reutilização acidental de um app Firebase Admin de outro banco, verificação de URLs HTTPS RTDB, fingerprints de fonte reforçados e relatório de observabilidade coerente entre réplicas.

A partir da pasta extraída, para testes sem rede:

```
python3 -m scripts.record_offline_v16
python3 -m unittest tests.test_firebase_configuration_r6 tests.test_firebase_sdk_wiring_r6 tests.test_observability_gate_r6 -v
python3 -m scripts.release_gate_work_v19_9
```

Para as provas opcionais de Nginx local real (com upstreams simulados):

```
python3 scripts/prove_nginx_native.py
python3 scripts/prove_official_nginx_contract_v19_7.py
```

Consulte `docs/FIREBASE_CONFIG_R6.md` e `HANDOFF_R6_2026_10_25.md` para restrições e plano de integração. O gate R6 ponderado segue 22/100 por falta de novas evidências integradas do Flask/Firebase/Docker após alterações de código. Não é nota ou previsão da banca.
