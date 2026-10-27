#!/usr/bin/env python3
"""Explicit, honest runtime smoke test for the V-Lab Docker stack.

Use after `docker compose --profile observability up -d --build`. This script
never contacts external services. Add --failover for controlled stop/restart of
api_a. Credentials/tokens are not written to the evidence JSON.
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/runtime/DOCKER_STACK_V13.json'
from source_fingerprint import docker_fingerprint

def get(url,headers=None):
    req=urllib.request.Request(url,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=4) as r:
            raw=r.read()
            try: obj=json.loads(raw)
            except (ValueError,UnicodeDecodeError): obj={}
            return r.status,dict(r.headers),obj
    except urllib.error.HTTPError as exc:
        return exc.code,dict(exc.headers),{}

def wait(fn,timeout=65):
    end=time.monotonic()+timeout
    last=None
    while time.monotonic()<end:
        try:
            val=fn()
            if val: return val
        except (OSError,ValueError,AssertionError) as exc:
            last=str(exc)
        time.sleep(1)
    raise RuntimeError(f'Service readiness was not demonstrated: {str(last)[:150]}')

def compose(*args):
    cp=subprocess.run(['docker','compose',*args],cwd=ROOT,capture_output=True,text=True)
    if cp.returncode:
        raise RuntimeError('docker compose '+ ' '.join(args)+' failed: '+(cp.stderr or '')[:200])

def creds():
    env=ROOT/'.env'
    if not env.exists(): return None
    values={}
    for line in env.read_text().splitlines():
        if line and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1);values[k.strip()]=v.strip().strip('"\'')
    if not values.get('GRAFANA_ADMIN_PASSWORD'):return None
    value=base64.b64encode(('admin:'+values['GRAFANA_ADMIN_PASSWORD']).encode()).decode()
    return {'Authorization':'Basic '+value}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--failover',action='store_true',help='Temporarily stop api_a and restart it after checking')
    args=parser.parse_args()
    result={'scope':'Docker Compose V-Lab sandbox (not original Flask/Firebase)',
            'validated':False,'tests':{}, 'source_fingerprint': docker_fingerprint()}
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
    stopped=False
    try:
        compose('--profile','observability','config','--quiet')
        result['tests']['compose_config']='pass'
        wait(lambda: get('http://127.0.0.1:8080/api/ready')[0]==200)
        status,_,_=get('http://127.0.0.1:8080/lab/')
        assert status==200
        result['tests']['dashboard']='pass'
        instances={}
        for _ in range(40):
            code,headers,body=get('http://127.0.0.1:8080/api/ready')
            assert code==200 and body.get('status')=='ok'
            name=headers.get('X-CourseSphere-Instance') or body.get('instance','unknown')
            instances[name]=instances.get(name,0)+1
        assert set(instances)=={'api-a','api-b'},f'Missing replica: {instances}'
        result['tests']['replica_distribution']=instances
        code,_,_=get('http://127.0.0.1:8080/metrics')
        assert code==403
        result['tests']['metrics_not_public']='pass'
        query=urllib.parse.urlencode({'query':'up{job="coursesphere-demo"}'})
        prometheus_url='http://127.0.0.1:9090/api/v1/query?'+query
        def prom_ok():
            code,_,resp=get(prometheus_url)
            if code!=200 or resp.get('status')!='success':return False
            vector=resp.get('data',{}).get('result',[])
            return (len(vector)==2 and all(float(item['value'][1])==1 for item in vector))
        wait(prom_ok)
        result['tests']['prometheus_scrapes_two']='pass'
        status,_,body=wait(lambda: (lambda response: response if response[0]==200 and response[2].get('database')=='ok' else False)(get('http://127.0.0.1:3000/api/health')))
        result['tests']['grafana_database_health']='pass'
        auth=creds()
        if auth:
            def dash_ready():
                code,_,obj=get('http://127.0.0.1:3000/api/search?query=CourseSphere',auth)
                return code==200 and any('CourseSphere' in str(item.get('title','')) for item in obj if isinstance(item,dict))
            wait(dash_ready)
            result['tests']['grafana_provisioned_dashboard']='pass'
        else:
            result['tests']['grafana_provisioned_dashboard']='not_checked_no_local_admin_secret'
        if args.failover:
            compose('stop','api_a');stopped=True
            survivors=[]
            for _ in range(8):
                code,_,body=get('http://127.0.0.1:8080/api/ready')
                assert code==200 and body.get('instance')=='api-b'
                survivors.append(code)
            result['tests']['nginx_failover_after_api_a_stop']={'result':'pass','responses':len(survivors)}
        # Full validation requires all expected operational checks, including
        # dashboard provisioning and failover when explicitly requested.
        required = ('compose_config', 'dashboard', 'metrics_not_public',
                    'prometheus_scrapes_two', 'grafana_database_health',
                    'grafana_provisioned_dashboard')
        if not all(result['tests'].get(k) == 'pass' for k in required):
            raise RuntimeError('Incomplete operational evidence; required checks absent')
        if args.failover and result['tests'].get('nginx_failover_after_api_a_stop', {}).get('result') != 'pass':
            raise RuntimeError('Failover was requested but not proved')
        result['validated']=True
    except Exception as exc:
        result['error_type']=type(exc).__name__
        result['failure']=str(exc)[:260]
        result['validated']=False
    finally:
        if stopped:
            try:
                compose('start','api_a')
                # A successful `docker compose start` only means the process was
                # launched. Verify that requests reach the recovered replica.
                wait(lambda: (lambda response: response[0] == 200
                              and response[2].get('instance') == 'api-a')(
                                  get('http://127.0.0.1:8080/api/ready')), timeout=65)
                result['tests']['api_a_restarted']='pass'
            except Exception:
                result['tests']['api_a_restarted']='FAILED_RESTART_MANUALLY'
                result['validated']=False
        EVIDENCE.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(result,indent=2,ensure_ascii=False))
    # Decide the process exit status only AFTER final cleanup and restart.
    # Returning from inside `try` could falsely signal success on restart failure.
    return 0 if result['validated'] else 1

if __name__=='__main__':
    sys.exit(main())
