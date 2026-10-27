# Instalação R15 Work — base R14

Baixe `CourseSphere_R15_WORK.zip` para `/home/thiago_jj/Downloads/` e use o comando completo fornecido com a entrega. Ele procura o nome exato e cópias com `(1)`, `(2)` etc.; verifica o SHA-256 esperado antes de executar o instalador incluído.

O instalador verifica membros e hashes do manifesto, rejeita travessia, links, duplicação, conteúdo extra e tamanho excessivo. Extrai em diretório novo em `~/V-Lab DevOps/releases`, compila e testa antes de trocar o link `CourseSphere_ATUAL`. A versão antiga permanece e o registro de backup fornece rollback. Diretórios manuais preexistentes ficam intactos; uma pasta real chamada CourseSphere_ATUAL é recusada para evitar sobrescrita.

Instala dependências somente dentro da versão, executa npm ci/build, verifica Docker sem iniciá-lo e verifica portas antes de tentar Firebase. Java e Node/npm são pré-requisitos do sistema. Se Java/CLI não estiverem disponíveis, a integração é SKIP; falhas em validações obrigatórias impedem ativação. Não há sudo, remoção de volumes nem parada de serviços de outros projetos.

Configurações copiadas: somente `.env.official.observability` e `.local/official_metrics_token`, sem symlinks e com permissão 0600. Outras credenciais/configurações não são copiadas automaticamente. A pasta da versão mantém seu caminho após criar venv para preservar os shebangs.

**Todos os resultados** ficam em `~/V-Lab DevOps/CourseSphere_EVIDENCIAS/<data>/RESUMO.json`, com logs, manifesto e evidências do projeto, inclusive quando ocorre falha. O resumo contém o comando exato de rollback quando existe versão anterior. Rollback também grava resumo.

A atualização foi testada em diretórios temporários do Work; não foi executada no computador Fedora do usuário. Docker integrado não foi aprovado. Consulte RELATORIO_STATUS.md antes de submeter.
