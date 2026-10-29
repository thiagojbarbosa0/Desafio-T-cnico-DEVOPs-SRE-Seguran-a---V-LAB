# V14.2 — frontend React compilável (correção direcionada)

**Motivo:** o Fedora executou 15/15 cenários HTTP Flask com sucesso, mas falhou no TypeScript com 11 erros.

**Mudanças:** removidos imports e parâmetros não utilizados; eliminada a necessidade de tipos jQuery no código; corrigido contrato de propriedades do perfil; migrado salvamento de ano/college/sobre para estado React; `sectionNumber` tornou-se opcional nas cartas; verificador de build fail-closed, regressões e documentação adicionadas.

**Validação realizada:** suíte Python completa e checagem de sintaxe TypeScript/TSX. **Pendente:** `npm ci && npm run build` no Fedora; Firebase Emulator; Docker/Prometheus/Grafana.

**Não se alterou:** achados do pentest, APIs principais, mecanismos de login Firebase, estilo SaaS sem neon, políticas de publicação.
