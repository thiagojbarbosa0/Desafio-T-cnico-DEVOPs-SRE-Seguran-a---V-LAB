#!/usr/bin/env python3
"""Generate sanitized, real HTTP evidence through the stdlib dev gateway.

Runs two local loopback HTTP servers with a disposable SQLite DB.
No Docker, Flask, Firebase, API keys or third-party networks involved.
"""
from __future__ import annotations
import http.client
import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.dev_gateway import Gateway
from backend.local_server import make_server
OUT=ROOT/'evidence'/'generated'/'HTTP_GATEWAY_V8.json'


def main():
    with tempfile.TemporaryDirectory(prefix='cs-v8-evidence-') as directory:
        api=make_server('127.0.0.1',0,str(Path(directory)/'data.db'),secret='G'*48,instance='v8-loopback-evidence')
        old=os.environ.get('PORT')
        os.environ['PORT']=str(api.server_address[1])
        gateway=ThreadingHTTPServer(('127.0.0.1',0),Gateway)
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in (api,gateway)]
        for t in threads:t.start()
        try:
            def call(method,path,payload=None,token=None):
                c=http.client.HTTPConnection('127.0.0.1',gateway.server_address[1],timeout=4)
                headers={'Content-Type':'application/json'} if payload is not None else {}
                if token: headers['Authorization']='Bearer '+token
                c.request(method,path,body=json.dumps(payload).encode() if payload is not None else None,headers=headers)
                response=c.getresponse()
                body=response.read()
                record={'method':method,'path':path,'status':response.status,
                        'instance':response.getheader('X-CourseSphere-Instance'),
                        'request_id':response.getheader('X-Request-ID')}
                c.close()
                return record,json.loads(body) if 'application/json' in (response.getheader('Content-Type') or '') else None
            checks=[]
            row,_=call('GET','/lab/');checks.append({**row,'expected':200,'name':'dashboard'})
            row,_=call('GET','/api/ready');checks.append({**row,'expected':200,'name':'readiness'})
            row,_=call('GET','/metrics');checks.append({**row,'expected':403,'name':'metrics gateway restriction'})
            login,body=call('POST','/api/demo/session',{'uid':'alice'})
            checks.append({**login,'expected':200,'name':'synthetic login'})
            token=body['access_token']
            courses,body=call('GET','/api/courses',token=token)
            checks.append({**courses,'expected':200,'name':'synthetic catalog'})
            alice=next(x for x in body['courses'] if x['owner_uid']=='alice')
            bob=next(x for x in body['courses'] if x['owner_uid']=='bob')
            denied,_=call('PUT',f"/api/courses/{bob['id']}",{'title':bob['title'],'description':bob['description']},token)
            checks.append({**denied,'expected':403,'name':'BOLA denied via gateway'})
            allowed,_=call('PUT',f"/api/courses/{alice['id']}",{'title':alice['title'],'description':alice['description']},token)
            checks.append({**allowed,'expected':200,'name':'owner allowed via gateway'})
            assert all(row['status']==row['expected'] for row in checks),checks
            report={'schema':'coursesphere.gateway-evidence.v8',
                    'scope':'synthetic local stdlib backend + development gateway, not Flask/Firebase original',
                    'network':'loopback only','test_data':'synthetic','checks':checks,
                    'pass_count':len(checks),'total_count':len(checks),
                    'limitations':['No Docker or Nginx exercised','No Firebase/Flask original app exercised','Browser navigation not exercised']}
            OUT.parent.mkdir(parents=True,exist_ok=True)
            OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(f'Gateway evidence: {len(checks)}/{len(checks)} checks passed → {OUT.relative_to(ROOT)}')
        finally:
            for s in (gateway,api):s.shutdown();s.server_close()
            for t in threads:t.join(timeout=4)
            if old is None:os.environ.pop('PORT',None)
            else:os.environ['PORT']=old

if __name__=='__main__':main()
