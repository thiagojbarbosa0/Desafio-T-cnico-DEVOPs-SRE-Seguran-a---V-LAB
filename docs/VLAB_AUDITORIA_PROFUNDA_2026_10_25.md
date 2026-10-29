# CourseSphere — auditoria aprofundada e engenharia complementar

**Corte:** 2026-10-25 UTC. **Base realmente aberta nesta sessão:** `CourseSphere_V19_9_WORK.zip` recuperado da Biblioteca (487 entradas, CRC íntegro). **Não** corresponde ao checkout V19.15. Não promover evidências entre versões sem comparação de hashes e runtime atestado.

## 1. Mudanças efetivas nesta cópia V19.9

- `scripts/evidence_integrity_vlab.py`: verificação offline rigorosa e autocontida de evidências JSON, com recusa de chaves duplicadas, NaN, artefatos grandes, symlinks, traversal, versões erradas, timestamps inválidos (quando exigidos), hashes alterados e testes obrigatórios ausentes.
- `scripts/npm_audit_triage_vlab.py`: leitura sanitizada de relatórios completos e `--omit=dev`, prioridade contextual por gravidade e exposição, sem downloads ou `audit fix --force`. Sem relatório de produção, exposição aparece como **não medida**, jamais presumida.
- `scripts/npm_lock_integrity_vlab.py`: revisão estrutural de `package-lock` v3: dependências travadas, HTTPS sem credenciais na URL, hash de integridade forte, scripts de instalação contabilizados. Não é análise de CVEs.
- `scripts/release_gate_v19_7.py` e `scripts/release_gate_v19_8.py`: provas com arquivos ausentes agora retornam falso em vez de interromper o avaliador com traceback.
- 44 testes novos e mutações de casos hostis para as ferramentas acima, incluindo caminho fora da raiz, symlink, hash antigo, classificação incompleta, porta URL inválida, relatório adulterado.
- `.github/workflows/ci.yml`: verificações extras integradas ao job existente; novos artefatos sanitizados de integridade e lockfile.

## 2. Execução observada nesta sessão

| Prova | Resultado e escopo |
|---|---|
| Python stdlib (cópia V19.9 adaptada) | **383/383 PASSOU** (`python -m unittest discover -s tests -p 'test_*.py' -q`) |
| Runner offline com evidência assinada por hash de fonte, não criptograficamente | **383 PASSOU**, `scripts.record_offline_v16` |
| Nginx real + upstreams sintéticos do contrato original | **PASSOU**, distribuição A/B **21/20**, failover **8/8**, proteção query/log e `/metrics` |
| Nginx nativo do laboratório independente | **PASSOU**, **40/40**, failover **8/8** |
| Node session/user chats/profile | **3 scripts PASSARAM**, callback e fetch controlados |
| Comparativo perfil upstream/corrigido | **PASSOU** com fetch/Firebase simulados, sem navegador real |
| Segredos conhecidos e preflight amplo | **PASSOU**, preflight analisou **335 arquivos texto**, zero achados; não é scanner completo de segredo nem Git history |
| Config Nginx nativa | **PASSOU**, parser real disponível |
| Lockfile npm V19.9 | **412 pacotes** estruturados, **0 problemas estruturais**, **3 com scripts de instalação** |
| CycloneDX a partir do npm lock | **397 componentes distintos por nome/versão**, não uma análise de CVE |
| `npm audit` | **NÃO EXECUTADO NESTA SESSÃO** — relatório anterior V19.12 referiu 39 avisos; não reutilizar como resultado atual |
| Flask HTTP antes/depois, aqui | **BLOQUEADO**: Flask/Flask-Cors ausentes; 15 casos foram ignorados. Um relatório desta tentativa foi preservado com `validated=false`; a evidência histórica original foi restaurada separadamente. |
| Docker/Flask real/Firebase Emulator/Grafana | **BLOQUEADO**, sem Docker/Firebase Admin neste ambiente |

O gate interno recalculado da **V19.9 recuperada e ajustada** é **60/100 (5/8)**, usando provas históricas de Flask/Firebase/React da mesma linhagem e provas recém-executadas de offline/Nginx. Ele **não é um resultado da V19.15**, nem significa que os serviços originais foram executados aqui. Não confundir com 383/383 de Python.

## 3. Revisão técnica dos achados upstream (escopo correto)

1. **F03: token em query** — risco demonstrável de exposição do token em URL; comparação antes/depois prévia com Bearer; sem prova de vazamento real.
2. **F04: material de credencial no ZIP original** — presença estática anteriormente comprovada; **não testar** valores nem assumir validade. Revogação/rotação depende do proprietário.
3. **F05: detalhe de exceção em resposta** — causa raiz corrigida com resposta genérica; impacto real depende do detalhe exposto.
4. **F06: entrada não limitada/homogeneizada** — limites de tipo/tamanho adicionados; DoS em produção **não demonstrado**.
5. **P-PROFILE: corrida A→B na UI** — reprodução determinística do callback original e da proteção de sessão derivada; é uma exposição de estado no mesmo navegador/cliente, não autorização Firebase quebrada no servidor.

F01 (cadastro público) e F02 (recomendação anônima) continuam **condicionados à política de negócios**. D01/D02 surgiram na derivação e não devem contar como vulnerabilidades do upstream. Cinco achados com evidências distintas **não equivalem a cinco explorações externas demonstradas**; revisão humana exigida.

## 4. Riscos técnicos que persistem

**P0** — Validar o checkout exato V19.15 com `npm ci`, triagem atual `npm audit`, frontend build e Firebase emulado; reconstruir as imagens. Fazer attestation de conteúdo dentro dos contêineres, incluindo Nginx configurado e marcador React, antes de validar isolamento, escrita negada e quotas 20/21. Registrar tempos, réplicas e SHA.

**P0** — Formalizar cinco achados upstream e três correções com diferenças de código e material de reprodução. Revisar licenças e histórico do repositório e notificar o proprietário sobre o arquivo F04, sem verificar segredo.

**P1** — Verificar se o limite de quota 20/21 se aplica a requisições balanceadas entre A/B e não apenas por meio do gateway; registrar qual réplica processou cada requisição sem registrar UID ou token. Completar prova de recuperação de A antes de declarar SRE encerrado.

**P1** — Validar dois SLIs/SLOs numa janela operacional, não apenas regras Prometheus carregadas. Conferir que dashboard Grafana é provisionado a partir da versão implantada.

**P1** — Conferir scripts npm de instalação e advisories separando runtime/dev; não executar upgrades major automáticos e preservar lockfile do checkout atual.

## 5. Portabilidade e instruções seguras para V19.15

O addon `CourseSphere_V19_15_PORTABLE_AUDIT_ADDON.zip` contém apenas **novos scripts de verificação e novos testes**, não sobrepõe Flask, Firebase, frontend, Compose, CI ou release gate V19.15. Copiar seletivamente e executar:

```bash
python3 -m unittest tests.test_evidence_integrity_vlab tests.test_npm_audit_triage_vlab tests.test_npm_lock_integrity_vlab -q
python3 scripts/npm_lock_integrity_vlab.py --output evidence/generated/NPM_LOCK_INTEGRITY_VLAB.json
# Opcional, em checkout imutável; npm audit normalmente retorna código != 0 quando encontra avisos:
(cd frontend && npm audit --json > ../.local/npm-audit-full.json || true)
(cd frontend && npm audit --omit=dev --json > ../.local/npm-audit-production.json || true)
python3 scripts/npm_audit_triage_vlab.py --full .local/npm-audit-full.json --production .local/npm-audit-production.json --output evidence/generated/NPM_AUDIT_TRIAGE_VLAB.json
```

Antes de criar `.local` para os JSONs, use `mkdir -p .local && chmod 700 .local`; ela deve permanecer ignorada pelo Git. Não inclua resultados brutos do npm audit em ZIP de entrega sem revisar conteúdos. O comando `|| true` só preserva a saída JSON para triagem; **não converte advisories em sucesso** e o classificador reprova saída incompleta.

Para `evidence_integrity_vlab.py`, informe a evidência, a versão **exata** do checkout e todos os arquivos relevantes que devem estar vinculados; para prova Docker use `--require-runtime-attestation` e as chaves exigidas. Esse verificador valida **consistência de evidência**, não prova autenticidade do executor; combine-o com a atestação de runtime já existente na V19.14/15.

**Não** usar o ZIP V19.9 desta sessão para substituir a V19.15. **Não** publicar automaticamente o fork. O requisito de licença/rotação permanece pendente.
