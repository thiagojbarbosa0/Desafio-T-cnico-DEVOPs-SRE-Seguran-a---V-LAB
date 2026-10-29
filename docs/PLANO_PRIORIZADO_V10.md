# Roadmap guiado pelos critérios da banca

| Ordem | Item | Prioridade edital | Evidência de aceite | Situação V10 |
|---|---|---|---|---|
| 1 | 5 vulnerabilidades reais do upstream (2+ OWASP) | ALTA | Provas HTTP antes da correção + severidade e impacto | PENDENTE; evidências de handler offline |
| 2 | 3 correções de causa raiz | ALTA | HTTP antes/depois, testes regressão | PARCIAL; mudanças no código e testes offline |
| 3 | Hardening | MÉDIA | Política CORS, tokens fora da URL, validação e headers observados por HTTP | PARCIAL: código + testes isolados |
| 4 | Relatório acessível à gestão/dev | MÉDIA | Achados priorizados, passos, prova e SRE | PRELIMINAR |
| 5 | Duas instâncias + balanceamento | MÉDIA | log/headers mostrando instâncias diferentes | Nginx NATIVO APROVADO; Docker pendente |
| 6 | Docker + observabilidade | MÍNIMO | health, métricas, Prometheus/Grafana, CI runtime | CONFIGURADO, SEM EXECUÇÃO DOCKER |
| 7 | Diferenciais | OPCIONAL | STRIDE, CI, SCA/SAST, SBOM, resiliência | MISTO: artefatos + Nginx nativo testado |

### Definição de pronto

- Código + teste isolado **não bastam** para declarar vulnerabilidade reproduzida no original em execução.
- Docker Compose YAML **não basta** para afirmar duas instâncias Docker funcionando.
- Script CI **não basta** para afirmar pipeline executado: requer run verde público/registrado.
- Matriz `RELEASE_GATE_V10.json` diferencia ambos e exige confirmação humana de licença e revogação de credenciais.
