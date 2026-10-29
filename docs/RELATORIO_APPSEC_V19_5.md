# CourseSphere — Relatório de Segurança V19.5 (síntese conservadora)

## Fonte e ambiente

A avaliação utiliza o código-fonte original fornecido pelo usuário (`CourseSphere-main.zip`) e a derivação V19.5, sem acesso aos sistemas em produção, sem chamadas a contas externas e sem testar credenciais. O pacote de entrega **não inclui** o ZIP upstream ou os valores de credenciais. Cenários HTTP Flask com Firebase sintético são distintos da validação posterior via Firebase Emulator.

## Achados e grau de comprovação

| ID | Categoria | Evidência | Situação / limitação |
|---|---|---|---|
| F01 | Cadastro/abuso de funcionalidade administrativa | A rota upstream expõe chamada privilegiada de criação de contas sem pré-autenticação; HTTP baseline 200, corrigido 410 | **Condicional:** cadastro aberto pode ser funcionalidade legítima. Não alegar criação de administrador ou escalada sem prova. |
| F02 | Autenticação/controle de uso | Consulta upstream anônima aceita; HTTP antes 200/depois 401 | **Condicional:** só constitui violação de política se recomendação requerer login. Não inferir custo ou DoS. |
| F03 | Gestão de sessão / credenciais | Token de autenticação aceito por parâmetro de URL no upstream, agora requer Bearer | Comportamento demonstrado em HTTP local com token sintético. Risco de exposição em histórico e logs, não vazamento de token real. |
| **F04** | **Exposição de dados sensíveis / gestão de segredos** | ZIP upstream contém `backend/cornell-course-sphere-data/reddit-data/reddit_key.json` com `client_id` e `client_secret`, incluindo valor com formato não evidentemente demonstrativo | **Presença confirmada estaticamente. Validade atual, privilégios e impacto externo não testados.** Rotação/revogação dependem do proprietário. |
| F05 | Divulgação de detalhes de erro | Exceções internas inseridas em respostas do upstream, saneadas na derivação | Comportamento confirmado com exceções sintéticas; severidade depende do conteúdo real exposto. |
| F06 | Validação e limitação de entrada | Perfis, consultas e mensagens aceitos sem limites antes; limites e tipos rejeitados agora | Falha confirmada de validação; não há demonstração de indisponibilidade/DoS. |

### F04 — prova reproduzível sem revelar dados sensíveis

O analisador `scripts/prove_upstream_credential_f04.py` **lê exclusivamente um ZIP original local fornecido pelo operador**, reconhece o arquivo e os nomes de campo esperados e gera metadados sanitizados. Não imprime, copia, transmite nem produz hashes de valores de segredo. Registra somente o SHA-256 do **ZIP inteiro**, que permite comparar a origem do snapshot. O arquivo gerado está em `evidence/generated/F04_UPSTREAM_CREDENTIAL_EXPOSURE.json`.

Execução opcional com uma cópia original autorizada:

```bash
python3 scripts/prove_upstream_credential_f04.py --source /caminho/para/CourseSphere-main.zip
```

**Medida aplicada na derivação:** remoção do arquivo credencial e verificação antes da publicação, inclusive se ele voltar a aparecer sob outro nome JSON. **Medida fora do nosso alcance:** notificar reservadamente o dono do repositório para confirmar e revogar/rotacionar o segredo caso seja válido. A remoção do arquivo não elimina sua existência em histórico Git público.

### Três correções de causa raiz demonstradas anteriormente

1. **Token em URL** → a API exige `Authorization: Bearer ...`; o gateway bloqueia URLs com query string em `/api/` e os logs do Nginx não armazenam query strings.
2. **Erros internos expostos** → o Flask preserva códigos HTTP, mas emite JSON genérico sem detalhes de exceções de serviços.
3. **Entrada sem limites/tipos** → validações no backend antes de Firebase/QueryManager; 413 preservado no caso de corpo excessivo.

A V19.5 acrescenta um quarto eixo de correção: **prevenção de publicação de arquivos de segredos**, após encontrar o arquivo no snapshot original. Não há comprovação de rotação/invalidade da credencial.

## Peso para a avaliação

O edital requer **cinco vulnerabilidades reais** em pelo menos duas categorias e **três correções com causa raiz**. A matriz tem seis candidatos, mas F01/F02 são condicionais e a banca deve julgar o escopo funcional. F04 é uma exposição de material de credenciais no código, não comprovação de comprometimento. Não converter seis candidatos em seis explorações reais ativas. É prudente obter confirmação dos requisitos de cadastro/recomendação ou localizar achados independentes adicionais.

### Resultados executados nesta rodada

Consulte `HANDOFF_V19_5.md` e `evidence/generated/RELEASE_GATE_V19_5.json` para contagens verificadas, hashes e testes ainda não executados. Testes sintéticos, Selenium/navegador, Firebase Emulator, React build, Docker, Grafana e Prometheus possuem escopos diferentes; nenhum substitui o outro.

## Publicação

O snapshot original não contém licença explícita identificada na raiz do ZIP. **Não pressupor permissão irrestrita de redistribuição** do código derivado sem esclarecer a licença com o proprietário/organização. Antes de publicar, inspecionar histórico Git, rodar scanners de dependência e confirmar a gestão do segredo upstream.
