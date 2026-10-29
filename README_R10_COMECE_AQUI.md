# CourseSphere V-Lab R10 — orçamento absoluto de leitura HTTP

**Escopo:** evolução R9 → R10 da **derivação V19.9**, e não do checkout principal V19.15. O servidor sintético do laboratório permanece separado do backend Flask/Firebase original. **Nunca publique a API sintética diretamente na internet.**

## Correção funcional

A R9 tinha timeout por chamada de leitura (`DEFAULT_CLIENT_READ_TIMEOUT=5s`) e limite de handlers. Entretanto, um cliente que transmitisse poucos bytes regularmente poderia continuar ocupando um handler por tempo indeterminado. A R10 aplica um limite monotônico de **10 segundos de leitura total por conexão**, além do timeout por leitura. O tempo começa antes da primeira linha HTTP, atravessa a interpretação de cabeçalhos e termina no corpo. Quando expira no corpo, a API devolve HTTP 408; quando expira durante cabeçalhos incompletos, a conexão é encerrada. Nada é gravado se uma requisição autenticada for interrompida.

O mecanismo usa uma fonte de leitura com prazo absoluto integrada ao `io.BufferedReader` do servidor HTTP. Não altera o contrato das rotas. A configuração programática de testes aceita `request_read_budget` entre 0,1 e 120 segundos, enquanto a execução normal mantém o limite fixo de 10 segundos.

O limite se refere às leituras de rede; **não** impõe deadline de CPU, de consultas SQLite ou de resposta. Não substitui rate limiting por IP, timeouts e orçamento de conexão do proxy, nem a proteção distribuída no gateway.

## Validação independente

```bash
bash scripts/verify.sh
python3 -m scripts.prove_r8_atomic_audit
python3 -m scripts.prove_r9_transport
python3 -m scripts.prove_r10_deadline
python3 scripts/prove_nginx_native.py
python3 -m scripts.release_gate_r10 --require-r10
```

A prova R10 cria **dois servidores Python de verdade, em loopback, compartilhando SQLite temporário**. Exercita envio lento de cabeçalhos, envio lento de corpo, requisição autenticada incompleta, integridade da auditoria e recuperação da disponibilidade. O relatório é vinculado a SHA-256 de backend, scripts de prova/gate, testes e CI. Toda essa evidência vale **zero pontos no aceite Flask/Firebase/Docker**.

## Portabilidade para a V19.15

- **Não** aplique o patch R9→R10 diretamente sobre o checkout V19.15 sem revisão: o patch foi verificado apenas para a derivação V19.9/R9.
- Analise primeiro o endurecimento da camada de transporte sintética; para o Flask original, os timeouts equivalentes devem ser definidos no Nginx/Werkzeug/Gunicorn conforme o contrato verdadeiro.
- Não reaproveite provas HTTP e Docker antigas após alterações nos módulos verificados por hash.
- Valide as regras Firebase Auth/RTDB, a quota compartilhada nas duas réplicas e o fluxo React; documente cinco achados upstream genuínos e três correções de causa raiz antes da submissão.
