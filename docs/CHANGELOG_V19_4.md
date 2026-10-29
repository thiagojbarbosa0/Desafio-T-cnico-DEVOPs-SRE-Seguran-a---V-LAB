# V19.4 — correções demonstráveis, 23/10/2026

- GitHub Actions: corrigida a execução acidental de dois comandos Python como uma linha shell na prova original Flask/Nginx.
- Adicionadas quotas transacionais de `profile_write` (20/min) e `chat_delete` (30/min) antes das escritas do Flask; 429 quando excedidas, 503 se RTDB indisponível.
- Logging estruturado de autenticação (`accepted`/`denied`) e contador Prometheus sem tokens/UIDs/IPs/URLs reais.
- +22 testes offline (240 → 262). 7 novos testes Flask WSGI preparados para execução onde Flask existe. Teste 20 do Emulator complementado com os novos limites sem aumentar artificialmente a contagem de cenários.
- Gate fail-closed para provas WSGI, com validação dos hashes de origem e proibição de skips.
- Verificação local unificada e handoff atualizados.

**Não é uma nova descoberta de vulnerabilidade upstream.** O Flask WSGI da V19.4, emuladores Firebase, build React e Docker não foram executados nesta sessão. O Nginx sintético foi executado.
