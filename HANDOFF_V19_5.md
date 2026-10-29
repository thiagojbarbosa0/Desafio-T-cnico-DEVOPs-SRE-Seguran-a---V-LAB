# Handoff mestre — CourseSphere V19.5

**Data:** 23/10/2026 (horário de Recife). **Baseline anterior:** V19.4. **Estado:** desenvolvimento; **NÃO** pronto para a banca. Este arquivo prevalece sobre relatórios históricos de versões anteriores.

## 1. Missão original (o que o V-Lab realmente pede)

A partir da aplicação CourseSphere original (`LambdaAK/CourseSphere`, ZIP fornecido pelo usuário), investigar pelo menos **cinco vulnerabilidades reais** em pelo menos duas categorias; documentar impacto, severidade, reprodução; **corrigir três causas raízes** com testes. Implementar pelo menos dois controles extras (hardening), logs estruturados, métricas/SLIs/SLOs, Docker para backend e frontend, Nginx balanceando duas instâncias, evidências, relatório de pentest e README. Diferenciais: STRIDE, CI, SAST/SCA, Grafana, testes de autorização, resiliência e nuvem/Kubernetes, conforme aplicável.

**Arquitetura original:** React/TypeScript/Vite, Flask, Firebase Auth e RTDB, módulos SQLite auxiliares e recurso de recomendação *não funcional/placeholder* na origem. **O laboratório de cursos/aulas/usuários sintéticos é separado** e serve para demonstração, não pode ser confundido com as vulnerabilidades da aplicação original. Não há decisão de migrar toda a stack para Rails.

O usuário exige um produto profissional, interface SaaS convencional, sem neon/glow/futurismo e sem custo pago. Pode desenvolver autonomamente, mas preservar decisões importantes para aprovação.

## 2. Trabalho novo da V19.5

1. **Achado F04 — credencial com aparência real exposta no snapshot upstream.** Inspecionei o ZIP original fornecido pelo usuário, com dois campos `client_id`/`client_secret` em `backend/cornell-course-sphere-data/reddit-data/reddit_key.json`. A evidência sanitizada registra somente o SHA-256 do ZIP completo, caminho e nomes de campo. **Não** registra valores, não testa validade, não faz contato externo e não inclui a fonte sensível no projeto derivado. Veja `evidence/generated/F04_UPSTREAM_CREDENTIAL_EXPOSURE.json` e `scripts/prove_upstream_credential_f04.py`.
2. **Scanner reforçado:** `scripts/security_preflight_v14.py` agora identifica valores JSON com formato de segredo OAuth mesmo em arquivos renomeados ou aninhados. Reconhece placeholders como `REPLACE_WITH_*`. Sem transmitir/imprimir valores.
3. **Auditoria do ZIP:** `scripts/check_release_archive_v19_5.py` impede caminhos perigosos, duplicados, links simbólicos, ambientes instalados, arquivos de credenciais, arquivos compactados aninhados e valores sensíveis comuns. O dataset JSONL grande conhecido é analisado em streaming, sem exclusão silenciosa.
4. **19 testes novos:** sete para o achado e scanner, seis para o gate, mais seis de auditoria do ZIP (**19 no total**, 262 → 281). O guard de F04 impede evidências com segredo no próprio relatório e não permite alegar que a chave está ativa.
5. **Novo roteiro local e CI:** `scripts/verify_local_v19_5.sh`, `scripts/release_gate_v19_5.py` e workflow CI atualizado. Consertei uma lacuna no novo roteiro: executar apenas `scripts/verify.sh` não gera o registro de evidência com os hashes atuais; a versão final usa `python3 -m scripts.record_offline_v16` para gerar e verificar resultados atuais.
6. **Relatório conservador:** `docs/RELATORIO_APPSEC_V19_5.md` separa F04 como exposição estática; não trata F01/F02 como vulnerabilidades automaticamente comprovadas ou F04 como credencial ativa.

## 3. O que foi REALMENTE executado nesta sessão

| Verificação | Resultado |
| --- | --- |
| Regressões Python offline | **281/281 PASS**, sem `FAILED` |
| Node: sessão, UserChats, perfil | **3 scripts PASS** (assertivas e testes controlados de respostas atrasadas) |
| Nginx instalado, configuração do próprio projeto | **PASS** (`nginx -t` e execução loopback) |
| Balanceamento local Nginx | **20/20 entre api-a e api-b**, 40 requisições totais |
| Failover Nginx sintético | **8/8 respostas HTTP corretas** após terminar uma réplica |
| Proteção do gateway e logs | token sintético rejeitado, query strings não encaminhadas, 55 entradas JSON sem token |
| F04 — leitura local do ZIP original | **CONFIRMADA a exposição de material com aparência de credenciais**, validade não testada |
| Pré-verificação de segredos da derivação | **PASS** após reconhecer placeholders do exemplo existente |
| Flask HTTP/WSGI nesta sessão | **NÃO EXECUTADO**, Flask/Flask-Cors não instalados e pip indisponível por resolução de DNS |
| Firebase Emulator nesta sessão | **NÃO EXECUTADO** |
| React `npm ci` / build nesta sessão | **NÃO EXECUTADO** (Node testes apenas) |
| Docker/Grafana/Prometheus nesta sessão | **NÃO EXECUTADO** |

**Não confundir histórico:** os 15 testes Flask realizados no Fedora na V14.1 e os testes integrados do Work V19.1 são evidências históricas, não nova execução sobre o código atual. O Nginx aqui prova réplicas **do laboratório Python sintético**; as réplicas Flask oficiais são outro teste.

## 4. Indicadores de progresso (estimativas internas, não nota da banca)

- **Implementação estimada: 69%**, mantida porque melhorias de evidência não concluem as integrações ainda abertas.
- **Aceite ponderado confirmado para esta cópia: 15%, 2 de 8 grupos**. Correspondem às regressões offline (7 pontos internos) e Nginx sintético (8 pontos internos). Os pesos são internos e **NÃO** são os pesos oficiais da banca.
- **`ready_for_submission`: false**. O F04 é adicional e não recebe pontos automaticamente no gate ponderado.

## 5. Matriz atual de achados do upstream

- **F01** cadastro com Firebase Admin sem autenticação upstream: comportamento demonstrado, **violação de negócio condicional** (cadastro aberto pode ser permitido).
- **F02** recomendações sem login upstream: demonstrado, **violação condicional** (política de acesso não conhecida).
- **F03** token em URL: comportamento reproduzido e corrigido.
- **F04** arquivo de credencial semelhante a segredo no código: **presença de material confirmada**; validade/impacto externos desconhecidos, nunca testados.
- **F05** informações internas em erros: reprodução sintética antes/depois.
- **F06** ausência de tipos/limites de entrada: reprodução sintética antes/depois.

Os principais **três eixos de correção** são Bearer no cabeçalho, saneamento de erros e validação no backend; a derivação também removeu o arquivo sensível, acrescentou quotas e limitou regras RTDB. **A banca ainda deve validar cinco vulnerabilidades independentes sob a política funcional efetiva**, e precisamos ligar cada correção ao achado correspondente e à evidência antes/depois mais atual.

## 6. Principais bloqueios e riscos

P0 — confirmação de **cinco achados realmente aplicáveis ao sistema original**, incluindo F01/F02 ou sua substituição; prova recente de três correções, impacto sem exagero. P0 — não divulgar material de segredos nem expor laboratório vulnerável publicamente. P0 — informar proprietário e solicitar revogação/rotação da credencial caso legítima. P0 — verificar licença e permissão de distribuição (ZIP upstream não mostrou licença explícita na raiz).

P1 — Firebase Auth/RTDB Emulator com regras de escrita e quotas reais, React build e sessão, Flask com duas instâncias, Docker Compose duas réplicas e Grafana/Prometheus, logs/SLOs, CI executado no GitHub. P2 — acabamento de documentação e demonstração final.

## 7. Quando voltar ao Fedora / Work

Primeiro valide o estado atual sem serviços externos:

```bash
bash scripts/verify_local_v19_5.sh
```

Se Python/Java/Node/Docker estiverem disponíveis, depois execute separadamente (sem credenciais reais):

```bash
.venv/bin/python -m integration.run_original_http_stubbed
.venv/bin/python -m integration.run_v19_4_flask_wsgitest
bash scripts/verify_official_emulators.sh
bash scripts/verify_frontend_build_v14_2.sh
# somente após instalar e iniciar Docker:
docker compose --profile observability up -d --build
python3 scripts/verify_docker_stack.py --failover
```

Qualquer falha implica `NOT VERIFIED`, nunca PASS. Scripts de instalação podem demandar downloads; execução com o Firebase Emulator usa `demo-*` e só loopback.

Se tiver acesso a uma cópia privada **autorizada** do ZIP original, pode reproduzir F04 sem expor o conteúdo:

```bash
python3 scripts/prove_upstream_credential_f04.py --source /caminho/CourseSphere-main.zip
```

Para a entrega final no GitHub, nunca reintroduzir o ZIP upstream com segredo e confirmar autorização/licença antes de publicar a derivação.

## 8. Próxima decisão técnica recomendada

**NÃO começar outra UI nem feature ornamental.** Primeiro fechar os gates Flask/Firebase reais e, se F01/F02 continuarem condicionais, encontrar outras vulnerabilidades upstream independentes e reproduzíveis. Quando o Work ou Fedora puderem executar dependências, salvar evidências vinculadas aos hashes atuais. Revisar direitos de distribuição e comunicar a credencial ao proprietário por canal privado sem copiar valores.

A V19.5 é checkpoint seguro de desenvolvimento, não entrega definitiva.
