# V19 — Alterações verificáveis

Data: 2026-10-23. Base: CourseSphere_V18_APPSEC_SRE_AUDITADA.zip.

## Segurança: fronteira de autorização do Firebase

1. **Problema encontrado na versão derivada**: `ops/firebase/database.rules.json` autorizava `.write` para `users/$uid` sempre que o cliente se autenticava como o próprio UID. Assim, um usuário autenticado poderia escrever perfil ou mensagens diretamente pelo SDK/REST do Firebase, contornando `validate_profile`, `validate_messages` e `Firebase.enforce_quota` do Flask. As regras da V18 de fato continham essa permissão; a exploração **não foi executada** contra um RTDB real nem contra terceiros.
2. **Correção**: cliente pode ler exclusivamente seu UID, mas `.write` está `false` no namespace `users` e na raiz. Somente os endpoints Flask, após verificar identidade, limites e campos, gravam com a API Firebase Admin. As quotas em `server_security` continuam sem acesso de clientes.
3. **Provas offline**: novos testes de contrato verificam a restrição e a ordem de validação→quota→gravação.
4. **Prova integrada pendente**: `test_21_rtdb_client_cannot_bypass_flask_validation_and_quota` usa Auth + RTDB Emulator reais, testa leitura permitida, leitura cruzada negada, escrita direta negada e gravação pelo Flask autorizada. O relatório da suíte agora exige **21/21** cenários e hashes atualizados; antigos 20/20 não são suficientes.

Esse endurecimento pertence ao código derivado V18 e **não deve ser apresentado como vulnerabilidade comprovada do repositório upstream**.

## Infraestrutura e evidência da aplicação original

- `scripts/flask_replica_stub_worker.py`: duas réplicas em processos separados, servindo rotas do Flask corrigido. Firebase e recomendador são simulados, e o servidor aceita conexões somente em `127.0.0.1`.
- `scripts/prove_original_flask_nginx.py`: importa a **configuração Nginx do projeto**, substitui endereços/porta apenas no teste, compara respostas de ambas as instâncias, verifica autorização por header, rejeição de token pela URL, acesso restrito a `/metrics` e oito respostas após derrubar uma instância.
- Job `original-flask-nginx-replication` no GitHub Actions para executar Flask + Nginx reais e publicar evidência sanitizada.
- `scripts/release_gate_v19.py` verifica hashes, contagem de respostas, autenticação e failover. Sua prova é **suplementar e não aumenta automaticamente** os oito pesos de aceite.
- **Não executado nesta sessão**: prova original Flask/Nginx (Flask não instalado), Firebase Emulator, React build, Docker/Prometheus/Grafana.

## Qualidade e rastreabilidade

- Novos testes sobre regras RTDB, exposição de dados, comportamento do gateway Flask e rejeição de artefatos antigos.
- `scripts/verify_v19.sh`: testes sem rede e prova Nginx local, com skip explicitamente reportado quando Flask não estiver instalado.
- `scripts/doctor_v19.py`: painel e status da revisão atual.
- As versões históricas permanecem para auditoria; consultar `README_V19_COMECE_AQUI.md` antes de qualquer roteiro antigo.
