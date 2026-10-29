# Indicadores de progresso — CourseSphere V13

**Data:** 23/10/2026. **A base é o repositório original enviado pelo candidato**; o laboratório sintético não deve ser apresentado como fonte das vulnerabilidades upstream.

## Dois números, significados diferentes

- **≈60% de implementação preparada**: julgamento técnico aproximado e explícito sobre o trabalho construído/configurado, incluindo itens ainda sem teste integrado. Não é uma medição oficial nem previsão de aprovação.
- **15% de aceite comprovado ponderado**: medição estrita de artefatos executados e rastreáveis conforme o gate de V13. Reflete apenas os componentes já realmente validados no ambiente atual. **2 de 8 grupos de validação aprovados**, com pesos definidos por nós para dar mais importância à análise/correção de segurança, conforme a prioridade qualitativa do edital.

| Frente | Peso interno de trabalho | Prontidão estimada | Contribuição |
| --- | ---: | ---: | ---: |
| Cinco achados e três correções no upstream | 35% | 50% | 17,5 |
| Hardening | 10% | 80% | 8,0 |
| Observabilidade + SLIs/SLOs | 10% | 75% | 7,5 |
| Docker, Nginx, resiliência e escala | 15% | 55% | 8,25 |
| Relatórios e evidências | 10% | 75% | 7,5 |
| Testes, pipeline e SAST/SCA | 10% | 80% | 8,0 |
| Diferenciais opcionais | 5% | 65% | 3,25 |
| Publicação, licença e revisão final | 5% | 5% | 0,25 |
| **Total (não é nota de banca)** | **100%** | | **60,25 ≈ 60%** |

Estas prontidões são avaliações de engenharia, **não** cálculo automático. Foram arredondadas para não sugerir precisão inexistente. Pesos percentuais acima são **nossos**, porque o edital fornece prioridades alta/média/baixa e **não** pesos numéricos.

## Aceite comprovado (fonte: `evidence/generated/RELEASE_GATE_V13.json`)

Pesos internos de verificação: 7% testes offline, 8% Nginx nativo, 20% HTTP Flask original/patch, 18% emuladores, 7% React, 15% Docker/Grafana, 20% validação das falhas/correções no upstream e 5% licença/rotação de credenciais. Na rodada atual, somente os primeiros dois passaram: **7+8 = 15%**.

O valor é conservador porque o ambiente não possui Flask, pacotes Firebase, dependências npm completas nem Docker. Arquivos de configuração e planos de testes **não** contam como validação executada.

## O que impede os 100%

- Provar por HTTP cinco problemas independentes do código original, e demonstrar três correções da causa raiz. Os 15 casos sintéticos fornecem parte da evidência, mas não substituem contextualizar risco e uso real.
- Rodar Flask verdadeiro + Firebase Auth/Database Emulator com 19 testes e isolamento entre contas.
- Fazer build completo do React/TypeScript e integrar interface e API.
- Executar Docker Compose, Prometheus e Grafana com duas réplicas e testes de falha reais.
- Colher resultados do SAST/SCA e validar o relatório para entrega pública.
- Verificar licença/autorização para redistribuir o upstream e confirmar com o proprietário a rotação de credencial; só removê-la do pacote não desativa a versão vazada.
- Criar repositório público com histórico Git real e rastreável, depois da verificação de licença.

**Implicação para o pedido "eu testo quando chegar a 100%":** realizar os testes integrados faz parte do próprio critério de 100%. O software pode ficar muito preparado sem intervenção do usuário, mas não é correto marcar como totalmente pronto enquanto o ambiente necessário estiver indisponível. Evitar entregar 100% fictício é uma proteção para o candidato na avaliação.
