# CourseSphere R16 — Docker piloto sem interferir na stack existente

Base: R15 Work, **não** é a fonte V19.15 original consolidada.

## O que mudou

- Docker Compose novo e isolado (`compose.r16.existing-emulator.yaml`) sob projeto **coursesphere-r16-pilot**.
- Duas instâncias reais do Flask, frontend React, gateway Nginx, Prometheus e Grafana.
- Reutilização do **Firebase Emulator local previamente ativo e healthy** do projeto Docker `coursesphere-official-local` por uma rede Docker existente (somente os dois backends se conectam a ela).
- Ajuste restrito do adaptador: acesso via DNS é aceito **somente** com `COURSESPHERE_DOCKER_EMULATOR_MODE=1` e nomes literais `official_firebase_emulators:9099`/`:9000`; o modo normal continua exclusivamente loopback e nunca admite credenciais reais.
- Prova real de 20 escritas/21ª negada por duas APIs **dentro do Docker**, leitura de ambas, cleanup do usuário sintético, Prometheus/Grafana, regras, proteção do gateway e failover (8 requisições com A parada), recuperação.
- Todos os relatórios gerados em `~/V-Lab DevOps/CourseSphere_EVIDENCIAS/R16_DOCKER_*/RESUMO.json`; sem tokens, senhas ou identificadores de usuário no resumo.

## Portas reservadas (somente loopback no Fedora)

- `http://127.0.0.1:18081`: SPA + API via gateway R16.
- `127.0.0.1:18091`, `127.0.0.1:18092`: APIs para prova específica por réplica.
- `http://127.0.0.1:19092`: Prometheus R16.
- `http://127.0.0.1:13001`: Grafana R16; senha local em `.env.r16.local` (0600). **Não publique essa senha.**
- `127.0.0.1:9099`, `127.0.0.1:9000`: emuladores **já existentes** do Fedora (não criados/reiniciados pela R16).

## Comando de trabalho dentro da versão instalada

```bash
cd "$HOME/V-Lab DevOps/CourseSphere_ATUAL" && .venv/bin/python scripts/deploy_r16_docker_pilot.py
```

**O comando de bootstrap distribuído com o ZIP instala a versão, testa, arquiva evidências, ativa-a com backup, e executa o Docker piloto.** Ele procura apenas o ZIP exato em Downloads e valida SHA-256.

O script aborta sem tocar no Docker antigo se o emulador não pertencer ao projeto esperado, estiver unhealthy, faltar o alias DNS, alguma das portas novas estiver ocupada ou já existir uma instância R16. Não executa `docker compose down`, não conecta/desconecta a rede antiga, não apaga volumes nem reinicia outros serviços. Em caso de falha, deixa logs e relatório; a versão anterior é preservada. Para limpar futuramente a stack R16, faça uma revisão separada de nomes, serviços e volumes.

## Estado de certificação

Testes **offline** e de contrato validam esta implementação, mas Docker não pôde ser executado no ambiente de desenvolvimento desta entrega. A prova de Docker só será reconhecida como PASS após a execução no Fedora, com SHA do código e relatórios. Outros bloqueios: cinco achados upstream formalmente independentes, vulnerabilidades npm remanescentes, recuperação da V19.15 integral. Não equipare o nome da R16 derivada à V19.15.
