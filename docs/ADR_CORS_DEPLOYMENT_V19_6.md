# ADR V19.6 — configuração CORS estrita no Flask original

**Decisão:** validar `ALLOWED_ORIGINS` antes de configurar `Flask-Cors`. A lista é explícita, com 1 a 16 origens HTTP(S) de formato canônico. `*`/regex, origens nulas/opacas, caminhos, query strings, fragmentos, credenciais e HTTP remoto são rejeitados por `ValueError`, bloqueando o boot com configuração insegura. HTTP em loopback é permitido para Vite/Firebase Emulator local; HTTPS para acesso remoto.

**Contexto:** `ALLOWED_ORIGINS` anterior era passado diretamente como lista ao Flask-Cors. Uma configuração `*` poderia reabrir CORS a qualquer origem. CORS não substitui autenticação; o ajuste é **hardening de configuração da derivação**, não mais um achado independente no ZIP original.

**Compatibilidade:** por padrão, mantém `http://localhost:5173`. Para uso com Vite em 127.0.0.1, definir as duas origens. Uma origem com barra final deve ser convertida para apenas o esquema/host/porta; uma origem HTTP numa rede remota exige configuração HTTPS.

**Evidência:** 13 testes Python offline V19.6 passaram; cinco cenários Flask+Flask-Cors WSGI aguardam instalação/execução. Testes HTTP/Emulator/replícas incluem agora hash da política; hashes históricos deixam de contar após a alteração.

**Riscos residuais:** CORS não impede um cliente HTTP de chamar uma API. A autorização deve continuar em `verified_uid()`/Firebase, rate limiting distribuído e regras RTDB. HSTS somente em HTTPS e segredo em variáveis de ambiente. Testar as configurações de CORS também no gateway de produção.
