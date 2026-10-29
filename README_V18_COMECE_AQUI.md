# CourseSphere V18 — comece aqui

**O que é:** derivação para avaliação AppSec/SRE do CourseSphere fornecido, com alterações seguras e laboratório local isolado. Não é um produto novo a ser submetido em substituição ao original.

## Comandos sem rede / sem Docker

```bash
bash scripts/verify_v18.sh
python3 -m scripts.release_gate_v18
```

O primeiro executa a suíte offline e Nginx nativo quando instalado. O segundo atualiza o indicador de conclusão com evidência vinculada à versão.

## Quando for validar as integrações no Fedora (posteriormente)

```bash
# dentro da pasta extraída do projeto
bash scripts/fedora_validation_v16.sh --install-deps --with-docker
```

Isso pode instalar dependências e iniciar contêineres locais, portanto só execute quando quiser. O roteiro inclui Flask HTTP, Firebase Emulator, React e Docker; se houver falha, não reinterprete como sucesso.

## Portas (somente loopback)

- `127.0.0.1:8080` — gateway/laboratório
- `127.0.0.1:9090` — Prometheus opcional
- `127.0.0.1:3000` — Grafana opcional

**Nunca use credenciais do repositório de terceiros ou exponha o laboratório intencional na internet.**

## Onde controlar

- `HANDOFF_MESTRE_V18.md`: objetivos, decisões, histórico resumido, risco e próximas etapas.
- `docs/RELATORIO_APPSEC_V18.md`: os cinco achados centrais, métodos e limites de prova.
- `reports/CONTROLE_V18.html`: painel local com progresso e aceite.
- `docs/CHANGELOG_V18.md`: alterações específicas desta versão.
