# CourseSphere R13 — pacote único, sem instalação destrutiva

## O que é este arquivo

Esta entrega inclui o código da **linha V19.9/R12 refinada para R13**, testes, dashboard, Docker Compose oficial, integração Firebase local, roteiros AppSec/SRE e **um executor próprio para Fedora**. Não é a V19.15 principal: *não sobrescreva essa versão com este ZIP*.

## Executar agora no Fedora

Baixe o ZIP e copie o comando completo abaixo para o terminal:

```bash
ARQ="$(find "$HOME/Downloads" "$HOME/Transferências" -maxdepth 1 -type f -name 'CourseSphere_R13_PACOTE_UNICO*.zip' -print -quit 2>/dev/null)"
if [ -n "$ARQ" ]; then
  mkdir -p "$HOME/V-Lab DevOps" && \
  unzip -oq "$ARQ" -d "$HOME/V-Lab DevOps" && \
  bash "$HOME/V-Lab DevOps/CourseSphere_R13/EXECUTAR_NO_FEDORA.sh"
else
  echo 'ZIP nao encontrado em Downloads/Transferências. Confira o download.'
fi
```

O comando procura tanto em `Downloads` quanto em `Transferências`, e aceita sufixos como `(1)` adicionados pelo navegador. O script funciona em qualquer diretório e **não** apaga projetos antigos.

A execução padrão roda offline, sem instalar dependências ou iniciar Docker. No Fedora com dependências instaladas, roda suíte Python, três testes Node, duas provas Nginx, auditoria do lockfile e gate.

**Opcional**, somente quando houver acesso à Internet para baixar dependências e tempo para teste completo:

```bash
bash "$HOME/V-Lab DevOps/CourseSphere_R13/EXECUTAR_NO_FEDORA.sh" --full
```

Isso pode instalar pacotes no virtualenv `.venv` e em `frontend/node_modules` e iniciar temporariamente os Firebase Emulators locais. O Docker tem salvaguarda adicional: nenhum contêiner existente será alterado por esse executor sem verificação do operador.

## Resultado

Todos os resultados ficam em `~/CourseSphere-Diagnosticos/<data>/RESUMO.json`, com logs privados e um `LEIA_O_RESULTADO.txt`. Cada etapa é `PASS`, `FAIL` ou `SKIP`. `SKIP` não é aprovação.

## O que foi concluído e o que ainda falta

- Regressões Python, Node, Nginx e auditorias offline foram executadas nesta sessão e estão descritas em `HANDOFF_R13_2026_10_27.md`.
- Foram incluídos testes de segurança para inicialização de **duas instâncias Flask** e quota compartilhada com Firebase Auth/RTDB locais; a execução real depende de componentes que não estavam disponíveis no ambiente de geração do ZIP.
- Docker/Firebase real e o checkout V19.15 não foram verificados aqui. O gate de entrega **permanece bloqueado**.

Mais detalhes: `DOSSIE_APPSEC_R13.md` e `HANDOFF_R13_2026_10_27.md`.
