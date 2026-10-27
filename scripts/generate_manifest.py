"""Evidence integrity inventory (SHA-256 does NOT imply trusted signing)."""
from pathlib import Path
import hashlib
import json
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
filelist=[root/'evidence/TESTES_V6.txt',root/'evidence/STRESS_CONCORRENCIA_20_RUNS.txt',root/'evidence/PROVAS_HTTP_LOCAL.json',
          root/'evidence/PROVENIENCIA_ORIGINAL.json',root/'evidence/DIFF_UPSTREAM_V6.patch',
          root/'evidence/PRINT_V6_LAYOUT_RENDERIZADO.png',root/'evidence/PRINT_V6_COM_DADOS_API_VERIFICADOS.png',
          root/'docs/HANDOFF_MASTER_V6.md',root/'docs/RELATORIO_PENTEST.md',root/'compose.yaml']
manifest={'collected_at_utc':datetime.now(timezone.utc).isoformat(),
          'note':'Content inventory, not authenticity signature; no proof a source is exploitable.',
          'files':[]}
for file in filelist:
    if file.exists():
        manifest['files'].append({'path':str(file.relative_to(root)),
                                  'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                                  'size_bytes':file.stat().st_size})
output=root/'evidence/MANIFEST_SHA256.json'
output.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'Wrote {len(manifest["files"])} records: {output}')
