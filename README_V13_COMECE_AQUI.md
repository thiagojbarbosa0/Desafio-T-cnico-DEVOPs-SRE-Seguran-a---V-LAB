# Comece aqui — CourseSphere V13

**Meta:** cumprir o desafio AppSec + SRE sobre o CourseSphere original, com evidências reproduzíveis. A sandbox de cursos é separada do upstream, não é uma prova de falhas do código original.

### Sem instalar nada

```bash
bash scripts/verify_v13.sh
```

O comando executa a suíte offline; valida a configuração Nginx com duas réplicas **se houver Nginx**; tenta a suíte HTTP do Flask **somente se as bibliotecas estiverem instaladas**. Em seguida gera `evidence/generated/RELEASE_GATE_V13.json`, que nunca marca dependências ausentes como aprovadas.

### Quando quiser liberar instalação local de dependências gratuitas

```bash
bash scripts/fedora_validation_v13.sh --install-deps
```

O script usa `.venv` e `frontend/node_modules` no próprio projeto, pode baixar dependências pela internet e executa os emuladores Firebase em loopback. Nunca conecta ao Firebase dos autores.

### Para permitir **também** o teste com Docker

```bash
bash scripts/fedora_validation_v13.sh --install-deps --with-docker
```

A stack Docker permanece iniciada para inspeção depois dos testes. Pare com `docker compose --profile observability down`.

### O que ainda exige decisão humana

- Verificar com a banca se o escopo do CourseSphere original (recomendação de disciplinas) atende o desafio cujo exemplo é CRUD cursos/aulas.
- Fechar cinco falhas **reais e independentes** do original e demonstrar três correções de causa raiz em uma API executada.
- Verificar licença/permissão de redistribuição do upstream e solicitar rotação da credencial que existia no ZIP original. **Não** incluir valores de segredos no GitHub.
- Publicar no GitHub com commits separando cada correção; scripts locais não fabricam histórico Git.

Veja `HANDOFF_MESTRE_V13.md` para decisões e prioridades; `docs/SLOS_FLASK_ORIGINAL_V13.md` para observabilidade.
