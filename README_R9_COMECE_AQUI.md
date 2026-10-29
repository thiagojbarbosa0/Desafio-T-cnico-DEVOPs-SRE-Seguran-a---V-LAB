# CourseSphere R9 — proteção de transporte HTTP no laboratório

**Base efetiva:** R8, derivada da CourseSphere V19.9; esta não é a versão principal V19.15.
O servidor modificado é `backend/local_server.py` (Python HTTP + SQLite sintéticos),
**não** o Flask/Firebase original. As rotas originais foram preservadas.

## Problema reproduzido e correções

- Antes, `rfile.read(Content-Length)` podia aguardar o cliente por tempo indeterminado,
  consumindo threads; um cliente que encerrasse a conexão podia enviar menos bytes do
  que declarou e o prefixo ainda ser aceito como JSON válido.
- Agora, cada socket tem timeout de leitura antes do parser ler cabeçalhos (`5s` por
  padrão), corpos incompletos terminados por EOF retornam **400**, um envio que
  ultrapassa o timeout retorna **408**, e corpos maiores que 32 KiB retornam **413**.
- Um `BoundedSemaphore` limita a **64 handlers simultâneos** por processo (padrão).
  Quando o limite é atingido, a conexão excedente é encerrada imediatamente;
  o cliente pode receber EOF/reset, não HTTP 503.
- As conexões são encerradas em erros de enquadramento/timeouts, mantendo as
  respostas genéricas e sem registrar corpo ou token.
- O limite pode ser definido no construtor `make_server(..., max_active_clients=...)`,
  com faixa inteira 1–512; timeout de leitura válido entre 0,1 e 30 s. Esses são
  controles do **laboratório** para testes e não novos endpoints expostos.

**Limites:** o timeout é por operação de socket, não tempo absoluto da requisição.
Um cliente que transmita bytes de forma contínua logo antes do timeout ainda pode
ocupar um handler até ser bloqueado por outra camada. O servidor local continua
não preparado para exposição pública (inclusive a rota deliberadamente sintética
`/api/demo/session` permite escolher usuários de demonstração). DDoS exige
proteções de borda, reverse proxy e controle operacional.

## Validar

```bash
bash scripts/verify.sh
python3 -m scripts.prove_r8_atomic_audit
python3 -m scripts.prove_r9_transport
python3 -m scripts.record_offline_v16
python3 -m scripts.release_gate_r9 --require-r9
```

Os testes de transporte usam **sockets TCP reais na interface 127.0.0.1**,
um SQLite temporário e até duas réplicas; não necessitam Flask/Firebase/Docker.
A prova `R9_SYNTHETIC_HTTP_TRANSPORT.json` vincula dez critérios à árvore de
fontes, testes, gate e CI via SHA-256. O gate é *fail-closed* em evidência faltante,
desatualizada ou contraditória e acrescenta **0 pontos formais de aceite**.

**Portabilidade para V19.15:** faça comparação e merge por trecho. Não copie
`backend/local_server.py` ou `.github/workflows/ci.yml` cegamente; preserve a
stack original e reexecute as provas no código efetivamente integrado.
