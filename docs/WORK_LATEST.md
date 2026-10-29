# WORK_LATEST — V19.9 Work, base V19.8

Data: 2026-10-24. Base recuperada: `CourseSphere_V19_8_OBSERVABILIDADE_FLASK_ORIGINAL.zip`; 447 entradas do manifesto original conferidas antes das alterações. Não houve reconstrução nem troca por uma versão anterior.

## Alterações reais
- Logs JSON INFO agora são emitidos pelo Flask; handler de transporte local evita URL/query e identificador bruto nos logs. Teste HTTP reproduziu a ausência dos eventos antes e passou depois.
- Métodos HTTP de métricas restritos a lista fixa; verbos arbitrários convergem para OTHER, evitando séries ilimitadas.
- Checkpoint exclui `.local` (segredos do monitoramento), mantém exclusões de dependências/credenciais e identifica V19.9.
- Nova prova com Prometheus real: duas réplicas Flask, contadores, regras oficiais carregadas, queda e recuperação. Firebase sintético; não representa Docker/Grafana.
- Nova prova upstream/corrigido do perfil após troca A→B, com TypeScript original byte a byte e respostas controladas. A correção de sessão já existia na base.
- Corrigidos testes WSGI que lançavam classes de exceção de outro módulo Python; sete cenários agora validam 429/503 e ausência de mutação.
- Corrigida duplicação de portas no teste Nginx e adaptado o parser nativo para ambiente sem usuário/mime.types da distribuição. A substituição de MIME é apenas para sintaxe.

## Execuções atuais
Evidências em `evidence/generated/WORK_V19_9_*.log`, JSONs com hashes e `MANIFEST_SHA256_WORK_V19_9.txt`.
- PASSOU: 339 testes Python offline (337 existentes + 2 regressões úteis).
- PASSOU: 15 HTTP Flask antes/depois; 23 Flask+Firebase Auth/RTDB Emulator; 8 proteção de métricas; 7 WSGI auth/quotas; 5 CORS; 1 regressão HTTP de logs.
- PASSOU: npm ci, TypeScript e Vite; três scripts Node de isolamento; comparação adicional de perfil upstream/corrigido.
- PASSOU: Nginx nativo sintético, Nginx+Flask real com Firebase simulado, contrato do gateway original, failover e Prometheus nativo.
- FALHOU e corrigido: logs INFO ausentes, testes estáticos dependentes de texto exato, identidade de exceções no harness, portas duplicadas e parser Nginx em instalação mínima. Logs anteriores pertinentes preservados; resultados finais acima.
- BLOQUEADO: Docker/Compose e Grafana integrado (runtime ausente); navegador automatizado (download do Chromium não íntegro). Não há prova end-to-end em navegador.
- PENDENTE: revisão formal dos cinco achados independentes, execução completa Docker original e validação de direitos/rotação upstream. Nenhuma credencial externa testada.

## Retomada
```bash
cd CourseSphere_V19_9
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m scripts.record_offline_v16
bash scripts/verify_frontend_build_v14_2.sh
bash scripts/verify_official_emulators.sh
python -m integration.run_original_http_stubbed
python -m integration.run_v19_4_flask_wsgitest
python -m integration.run_v19_8_metrics_runtime
node scripts/prove_profile_race_work.cjs
# Com Nginx e Prometheus instalados no PATH:
python scripts/prove_original_flask_nginx.py
python -m scripts.prove_native_prometheus_work
python -m scripts.release_gate_work_v19_9
```
Firebase CLI 15.34.0 e Java 21 foram usados; dependências instaladas não estão no ZIP. No ambiente desta sessão foi necessário retirar HTTP_PROXY/HTTPS_PROXY somente do processo local do CLI após baixar o JAR. Não copiar essa configuração indiscriminadamente para outros ambientes.

Próxima prioridade: executar `compose.official.yaml` e overlay de observabilidade em host Docker, usando `scripts/start_official_observability_v19_8.sh` e `scripts/verify_official_observability_v19_8.py --failover`, após preflight. Em paralelo, revisar `docs/REVISAO_SEGURANCA_WORK_V19_9.md`. Não publicar automaticamente.

Aceite ponderado: 60/100, cinco de oito gates. Estimativa histórica de implementação: 73%, mantida sem aumento arbitrário. Não pronto para declarar edital integralmente atendido. Documentos anteriores e manifestos V19.8 são históricos; este handoff e o relatório atual prevalecem.
