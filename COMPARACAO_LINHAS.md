# Bases e integração

Base efetiva: R14_PACOTE_UNICO, SHA-256 `50e91ddbde87761ab25956b2e192573ce892bb73712cbe9e30cbb24887498c91`. Extração conferiu CRC, caminhos e ausência de symlinks.

A busca exata por `CourseSphere_V19_15.zip` não retornou pacote. A busca ampliada `CourseSphere_V19_15` retornou complementos portáveis R1–R15 e um auxiliar, sem fonte completa. Esses complementos não demonstram acesso ao checkout principal. **Não houve integração à V19.15.**

Comparação direta com a ramificação V19.9 antes disponível mostrou que a R14 já acrescenta readiness, correlação, identidade de réplica, parser JSON estrito, configuração Firebase e limpeza restrita de fixtures. Nenhum desses arquivos foi substituído pela versão antiga. Somente a nova prova nativa foi portada e adaptada para preservar cleanup R14, readiness e origem do frontend; reexecutada contra os arquivos R14 atuais.

O patch `patches/R14_to_R15_WORK.patch` compara os arquivos de código/configuração desta entrega com o ZIP R14 exato; aplicar somente a essa base, com revisão. Não é patch validado para V19.15.
