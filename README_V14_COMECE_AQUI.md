# CourseSphere V14 — comece aqui

**Objetivo:** melhorar a segurança e a confiabilidade do [CourseSphere original](https://github.com/LambdaAK/CourseSphere), encontrando pelo menos cinco vulnerabilidades reais, corrigindo três delas e demonstrando hardening, métricas, balanceamento, Docker e documentação de pentest.

**O CourseSphere original é uma plataforma de recomendação de disciplinas (Flask/React/Firebase/SQLite);** a API de cursos/aulas criada para o desafio é uma **sandbox sintética separada**. Ela não comprova vulnerabilidades da aplicação original.

## Estado atual (V14)

- **≈62% implementação estimada** — código, testes e configurações entregues, mas nem tudo testado em integração.
- **15% aceite ponderado comprovado** — regressões Python e Nginx real, com pesos internos não oficiais.
- **151 testes Python offline passaram na rodada de V14** e Nginx real distribuiu 20/20 requisições entre réplicas sintéticas e respondeu 8/8 após falha controlada.
- Testes reais com Flask/Firebase emulators, build React, Docker/Prometheus/Grafana: **não comprovados** neste ambiente.

## Começar sem instalar nada

```bash
bash scripts/verify_v14.sh
```

O script reproduz verificações offline, Nginx nativo se instalado, varredura preliminar de credenciais e atualiza `evidence/generated/RELEASE_GATE_V14.json`. Não marca testes pulados como aprovados.

## Ação necessária para desbloquear as próximas validações

**O código restante pode continuar sendo aprimorado, mas os critérios de aceite de integração não chegam a 100% sem executar os sistemas.** Quando estiver em seu Fedora (com Docker, Java, Node/npm, Python e rede para pacotes), execute **dentro desta pasta**:

```bash
bash scripts/fedora_validation_v14.sh --install-deps --with-docker
```

Esse comando permite baixar dependências gratuitas para o workspace, subir ambientes locais controlados (Firebase emulador, Docker), executar testes e atualizar evidências. Pode usar `--install-deps` sem `--with-docker` se ainda não tiver Docker. **Não exponha os emuladores ou laboratório à internet.** Nenhuma credencial original é necessária.

Envie os arquivos de evidências/log de saída depois; um resultado diferente de zero é falha, não aprovação parcial silenciosa.

## Antes do GitHub público

1. Confirmar a licença/autorização de redistribuição do código upstream (sem pressupor que repositório público = licença livre).
2. Informar o mantenedor original sobre o arquivo de credencial encontrado no ZIP recebido e recomendar rotação/revogação e avaliação do histórico Git. A V14 **não contém** os valores.
3. Rever os achados no escopo da aplicação realmente utilizada e obter cinco provas independentes + três correções com evidências antes/depois.

## Onde controlar

- `HANDOFF_MESTRE_V14.md` — visão, prioridades, decisões, riscos e impedimentos.
- `docs/SECURITY_MATRIX_V14.md` — achados originais e nível de comprovação.
- `docs/PROGRESSO_V14.md` — cálculo e limites das porcentagens.
- `evidence/generated/RELEASE_GATE_V14.json` — gate gerado da execução.
