# CourseSphere V14.3 — correção do script de compilação React

O script V14.2 chamava o parser TypeScript **antes** do `npm ci`, terminando em `TypeScript parser indisponível` antes de tentar o build.

A V14.3 instala as dependências com o lockfile (`npm ci`), verifica a sintaxe, e então executa `npm run build` (TypeScript + Vite). Evidência de build aprovado só é gerada se todas essas operações concluírem sem erro.

## No Fedora

Na pasta CourseSphere_V14 desta versão:

```bash
bash scripts/verify_frontend_build_v14_2.sh
```

O sucesso termina com `Build React validado!`. Se aparecer outra falha, envie o trecho a partir de `[1/3]`, `[2/3]` ou `[3/3]` até o erro.

- ZIP e sintaxe Bash validados aqui.
- Build React completo ainda depende da execução no Fedora.
- O resultado HTTP anterior 15/15 aprovado com Firebase simulado foi informado pelo usuário; nenhum teste de Firebase real é alegado nesta mudança.
