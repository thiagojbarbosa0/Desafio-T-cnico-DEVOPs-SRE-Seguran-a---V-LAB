"""Execute the current offline suite once and write source-bound, truthful proof."""
from __future__ import annotations
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from scripts.release_gate_v13 import offline_fingerprint
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/TESTES_OFFLINE_V13.json'
LOG=ROOT/'evidence/generated/TESTES_OFFLINE_V13.log'


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        process=subprocess.run(['bash','scripts/verify.sh'],cwd=ROOT,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=45)
        transcript=process.stdout
        return_code=process.returncode
    except subprocess.TimeoutExpired as exc:
        transcript=(exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout,bytes) else (exc.stdout or '')
        transcript+='\nTIMEOUT: offline suite did not finish within 45s\n'
        return_code=124
    LOG.write_text(transcript, encoding='utf-8')
    matches=re.findall(r'Ran (\d+) tests.*?\n\nOK\b', transcript, flags=re.S)
    count=int(matches[-1]) if matches else 0
    passed=(return_code==0 and count>=134 and 'FAILED (' not in transcript)
    proof={'validated':passed, 'tests_run':count, 'failures':0 if passed else 1,
           'errors':0 if passed else 1, 'source_fingerprint':offline_fingerprint(),
           'generated_utc':datetime.now(timezone.utc).isoformat(),
           'command':'bash scripts/verify.sh','exit_code':return_code}
    OUT.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('\n'.join(transcript.splitlines()[-8:]))
    print(f'Offline regressions: {count} tests; validated={passed}.')
    return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
