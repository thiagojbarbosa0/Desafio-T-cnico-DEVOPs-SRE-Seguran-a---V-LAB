"""Read-only evidence collection, no credentials or tokens written to output."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'evidence'/'runtime'
OUTPUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8080'

def get(path):
    try:
        with urlopen(BASE+path,timeout=3) as r:
            return {'status':r.status,'body':r.read().decode()[:1000], 'instance':r.headers.get('X-CourseSphere-Instance')}
    except Exception as exc:
        return {'error':type(exc).__name__,'detail':str(exc)[:200]}

def main():
    checks={'ready':get('/api/ready'),'health':get('/api/health'), 'sampled_replicas':[]}
    for _ in range(16):
        result=get('/api/ready')
        checks['sampled_replicas'].append(result.get('instance','not-reached'))
    checks['unique_replicas']=sorted(set(checks['sampled_replicas']))
    checks['collected_at_utc']=datetime.now(timezone.utc).isoformat()
    checks['note']='Observations only: no claim of two replicas unless both instance IDs appear.'
    file=OUTPUT/'operational_checks.json'
    file.write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
    print(file)
    for id in checks['unique_replicas']:print('observed instance:',id)

if __name__=='__main__': main()
