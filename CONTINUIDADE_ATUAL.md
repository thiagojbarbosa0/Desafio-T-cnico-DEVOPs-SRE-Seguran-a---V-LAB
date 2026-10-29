# CourseSphere R16 Docker Pilot — Handoff

Base concreta `CourseSphere_R15_WORK.zip` do Work, derivada de R14/V19.9; não contém a V19.15 integral. Esta versão adiciona implantação isolada Docker, sem modificar serviços Docker existentes.

## Fatos
- Na R15 o usuário instalou e ativou o pacote no Fedora, e passou 3/3 Node, Flask/Firebase Emulator local e quota entre duas instâncias; `CourseSphere_ATUAL` apontou para o release R15.
- Na R16, a alteração ao backend é restrita à configuração de host Firebase em Docker (`backend/firebase_configuration.py`); validar com `tests/test_r16_docker_pilot.py`.
- O projeto Docker R16 `coursesphere-r16-pilot` é separado do Compose antigo `coursesphere-official-local`. A nova rede é própria; somente as APIs ingressam na rede externa já usada pelo emulador. Portas são 18081/18091/18092/19092/13001, bind 127.0.0.1.
- Nova stack: `compose.r16.existing-emulator.yaml`. Verificação `scripts/deploy_r16_docker_pilot.py` exige emulador preexistente healthy, label de projeto/serviço esperado, DNS `official_firebase_emulators` e portas antigas presentes, antes de criar recursos R16.
- O script de instalação do ZIP preserva a R15 via diretórios versionados e symlink `CourseSphere_ATUAL`; logs permanentes no diretório `CourseSphere_EVIDENCIAS`.

## Precisa ser comprovado no Fedora
Docker R16 com duas APIs e gateway, quotas 20/21, cleanup, 2 scrapes e readiness, Grafana dashboard, failover e recuperação. Não reportar PASS de Docker sem JSON R16 validado. Para mais detalhes, consulte `COMECE_AQUI_R16.md`.

## Pendentes
- 5 achados upstream independentes formalmente comprovados e 3 correções rastreadas.
- Vulnerabilidades npm de produção (R15 tinha 14 alertas, 5 altos).
- Obter fonte completa V19.15 e integrar criticamente.
- CI remoto, browser E2E e licenciamento.
