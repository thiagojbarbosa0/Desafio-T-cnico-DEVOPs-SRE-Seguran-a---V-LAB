# Continuidade — R15 Work, 27/10/2026

**Leia este arquivo e STATUS_ATUAL.json primeiro.** Base efetiva R14_PACOTE_UNICO, SHA-256 `50e91ddbde87761ab25956b2e192573ce892bb73712cbe9e30cbb24887498c91`. Diretório da sessão: `/workspace/scratch/4e90df872e3a/r14-work/CourseSphere_R14`. Pacote entregue usa raiz `CourseSphere_R15_WORK`. Não é V19.15 integrada: fonte completa não encontrada; só complementos portáveis.

## Concluído
- Instalador transacional: manifesto/hashes, rejeição de ZIP inseguro, extração nova, testes antes de ativar, backup por preservação da versão, configuração permitida 0600, rollback e relatórios automáticos na pasta permanente. Sem sudo ou remoção de serviços/volumes.
- Prova nativa portada seletivamente: dois Gunicorn/Flask independentes, gateway original, Firebase Auth/RTDB real em emuladores, React compilado e Prometheus. Quota concorrente 20 aceitas/4 negadas; failover autenticado 8/8; recuperação preservou perfil; cleanup R14 confirmado.
- Seis cenários semânticos de alertas via promtool; job CI preparado, NÃO executado remotamente.
- Lockfile npm atualizado dentro das faixas declaradas. Auditoria produção: 24→14 alertas; críticos 2→0, altos 9→5. Quatorze restantes exigem revisão; sem audit fix --force/downgrade automático.
- Harness sintético antigo corrigido para implementar probe_dependencies e testar /metrics com readiness. Nenhuma alteração destrutiva no backend da R14.
- Revisão de achados evita contar dois limites de entrada como independentes ou cadastro público como vulnerabilidade incondicional.

## Validação atual
811 offline; 15 HTTP antes/depois; 23 Firebase + 8 critérios de quota; 7 WSGI; 8 métricas; 5 CORS; 3 scripts Node; comparação de perfil upstream; build React; duas provas nativas Nginx; integração real nativa; 6 cenários promtool; 4 testes de instalador. PASS, com logs WORK_R15_* e JSONs em evidence/generated.

Falhas corrigidas: cache do JAR ausente (recuperado/CRC verificado), adapter de readiness ausente em testes HTTP, evidência stale após editar CI (regenerada). npm audit continua FAIL pelos alertas restantes. Build/Node reexecutados após atualizar lock; integração nativa reexecutada contra o novo frontend. Resultados herdados sem nova execução são STALE, não prova nova.

Gate estrito R14 aceita cleanup/quota atual. Aceite ponderado 60/100; não pronto para submissão. Não é nota nem percentual de implementação. Sem nova estimativa numérica de implementação.

## Bloqueios / próxima ação
Docker completo e Grafana: NOT_RUN (runtime Docker indisponível no Work). Navegador e CI remoto: NOT_RUN. V19.15 completa ausente. Revisão formal AppSec, credenciais/licença e npm alto pendentes. Próxima prioridade: Docker original com duas réplicas/Firebase/Prometheus/Grafana e resolução das dependências restantes.

## Retomada
No Fedora, use o mega comando da entrega: busca ZIP em Downloads, verifica hash, instala e salva tudo em `/home/thiago_jj/V-Lab DevOps/CourseSphere_EVIDENCIAS/`. Não execute isso no Work como se fosse o Fedora.

Na árvore já preparada:
```bash
python3 -m scripts.record_offline_v16
bash scripts/verify_frontend_build_v14_2.sh
bash scripts/verify_official_emulators.sh
bash scripts/verify_integrated_native_work.sh
promtool test rules ops/prometheus/alerts.official.test.yml
python3 -m scripts.release_gate_r14 --require-r14
```
Dependências: Python 3.12 + backend/requirements.txt + gunicorn 23.0.0; Node/npm; Firebase CLI 15.34.0; Java 21; Nginx/Prometheus no PATH. No Work, JAR em `emulator-cache`, dependências isoladas fora da entrega; FIREBASE_EMULATORS_PATH aponta para esse cache. Sem segredos/venv/node_modules no ZIP.

Patch portável: patches/R14_to_R15_WORK.patch, somente sobre o R14 exato. Não aplicar cegamente à V19.15. Empacotamento: `python3 -m scripts.package_release_work --out /caminho/externo/CourseSphere_R15_WORK.zip`.

Checkpoint final: ZIP real instalado em diretório temporário do Work; manifesto, compilação, 811 testes e ativação PASS. Smoke usou --skip-deps; pip/npm/build/Firebase foram executados separadamente na árvore de desenvolvimento. Prova refere SHA do checkpoint antes deste registro documental; fontes do instalador e testes permanecem idênticas.
