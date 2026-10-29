# Revisão AppSec — R15 Work sobre R14

O dossiê R13 permanece histórico. Não adotamos sua contagem de cinco achados sem ressalvas: cadastro público não prova violação de política; tamanho de mensagens e tamanho de perfil não devem contar automaticamente como duas causas raiz independentes.

| Candidato upstream | Origem e prova | Correção / risco residual |
|---|---|---|
| Token em URL | `audit/baseline/endpoints_original.txt`, GET `/users/info` | Bearer e bloqueio no gateway; prova local, sem token real vazado |
| Exceções em respostas | mesmo baseline, `str(e)` | Respostas genéricas; impacto depende dos detalhes da exceção |
| Entradas sem limites | handlers de perfil/mensagens no baseline | Tipos, limites e quotas RTDB; não houve prova de DoS |
| Segredo no snapshot | metadados sanitizados `F04_UPSTREAM_CREDENTIAL_EXPOSURE.json` | Arquivo removido; validade/rotação desconhecidas; prova histórica identificada |
| Perfil de sessão anterior | `audit/baseline/profile_api_original.ts.txt` e `scripts/prove_profile_race_work.cjs` | Callback atrasado A→B descartado no código atual; teste controlado, sem navegador/produção |

Três eixos independentes de correção: transporte de token, saneamento de erros e validação/limitação. A quota agora foi executada com Firebase Emulator real em processos independentes. A nova prova nativa não converte esses achados em explorações de produção.

A liberação formal dos cinco achados continua PENDENTE; não foram atribuídos pontos adicionais. Nenhum problema novo de instalador/testes foi atribuído ao upstream. Os alertas npm correspondem a dependências da derivação e têm relatório antes/depois separado; ausência de alertas nunca equivale a segurança completa.
