"""Local real Gunicorn/Flask + Nginx + Firebase Emulators + Prometheus.

No Docker claim, no synthetic Firebase adapters, no external credentials.
Run using scripts/verify_integrated_native_work.sh.
"""
import concurrent.futures, hashlib, json, os, re, shutil, signal, socket
import subprocess, sys, tempfile, time, traceback, uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import build_opener, ProxyHandler, Request
from urllib.error import HTTPError
from urllib.parse import urlencode
from integration.test_official_emulators import require_emulator_environment
from integration.emulator_fixture_cleanup_r14 import SyntheticAccount, cleanup
from scripts.source_fingerprint import frontend_fingerprint
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/INTEGRATED_NATIVE_WORK.json'
http=build_opener(ProxyHandler({}))
def call(base,path,method='GET',payload=None,token=None,headers=None):
    hdr=dict(headers or {})
    if token: hdr['Authorization']='Bearer '+token
    body=None if payload is None else json.dumps(payload).encode()
    if body is not None: hdr['Content-Type']='application/json'
    req=Request(base+path,data=body,headers=hdr,method=method)
    try: response=http.open(req,timeout=8)
    except HTTPError as error: response=error
    with response:
        raw=response.read();ctype=response.headers.get('Content-Type','')
        return response.status, json.loads(raw) if 'application/json' in ctype else raw.decode(errors='replace'),dict(response.headers)
def wait(fn,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            if fn(): return
        except (OSError,ValueError): pass
        time.sleep(.2)
    raise AssertionError('Service state deadline exceeded')
def ports(n):
    sockets=[]
    try:
        for _ in range(n):
            s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s)
        return [s.getsockname()[1] for s in sockets]
    finally:
        for s in sockets:s.close()
def stop(p):
    if p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=8)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
def main():
    report={'version':'R15 Work (base R14)','validated':False,'generated_utc':datetime.now(timezone.utc).isoformat(),'scope':'Two independent real Gunicorn/Flask processes, Nginx original routing, Firebase Auth/RTDB Emulators, native Prometheus and built React assets. No Docker, Grafana or browser.','tests':{},'source_sha256':{}}
    files=['scripts/prove_integrated_native_work.py','scripts/verify_integrated_native_work.sh','ops/nginx/gateway.official.conf','ops/nginx/frontend.official.conf','ops/prometheus/alerts.official.yml','ops/firebase/database.rules.json','firebase.json','integration/emulator_fixture_cleanup_r14.py']
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'backend').glob('*.py')]
    for name in files:report['source_sha256'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    processes=[];logs=[];accounts=[]
    report["frontend_source_fingerprint"]=frontend_fingerprint()
    try:
        require_emulator_environment()
        assert not any(os.getenv(k) for k in ('GOOGLE_APPLICATION_CREDENTIALS','OPENAI_API_KEY','FIREBASE_DATABASE_URL'))
        assert shutil.which('nginx') and shutil.which('prometheus'),'Nginx and Prometheus required on PATH'
        import gunicorn
        report['gunicorn_version']=gunicorn.__version__
        assert (ROOT/'frontend/dist/index.html').is_file(),'Build React first'
        with tempfile.TemporaryDirectory(prefix='coursesphere-integrated-') as temp:
            home=Path(temp);a,b,edge,web,prom=ports(5)
            def start(args,name,cwd=ROOT,env=None):
                log=(home/(name+'.log')).open('w');logs.append(log)
                p=subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=log,start_new_session=True);processes.append(p);return p
            def backend(port,name):
                env={**os.environ,'COURSESPHERE_METRICS_ENABLED':'1','ALLOWED_ORIGINS':f'http://127.0.0.1:{edge}','COURSESPHERE_REPLICA_NAME': 'api-a' if port==a else 'api-b'}
                p=start([sys.executable,'-m','gunicorn','--bind',f'127.0.0.1:{port}','--workers','1','--threads','4','--timeout','30','endpoints:app'],name,ROOT/'backend',env)
                wait(lambda:call(f'http://127.0.0.1:{port}','/health')[0]==200)
                return p
            api_a=backend(a,'api-a');report['tests']['gunicorn_a_ready']='pass'
            api_b=backend(b,'api-b');report['tests']['gunicorn_b_ready']='pass'
            gateway=(ROOT/'ops/nginx/gateway.official.conf').read_text().replace('official_api_a:8091',f'127.0.0.1:{a}').replace('official_api_b:8091',f'127.0.0.1:{b}').replace('official_frontend:8082',f'127.0.0.1:{web}').replace('listen 8081;',f'listen 127.0.0.1:{edge};')
            frontend=(ROOT/'ops/nginx/frontend.official.conf').read_text().replace('listen 8082;',f'listen 127.0.0.1:{web};').replace('/usr/share/nginx/html',str(ROOT/'frontend/dist'))
            config=f'''{'user root;' if os.geteuid()==0 else ''}
worker_processes 1;
pid {home}/nginx.pid;
error_log {home}/nginx-error.log warn;
events {{ worker_connections 256; }}
http {{
client_body_temp_path {home}/body;
proxy_temp_path {home}/proxy;
fastcgi_temp_path {home}/fastcgi;
uwsgi_temp_path {home}/uwsgi;
scgi_temp_path {home}/scgi;
log_format proof escape=json '{{"path":"$uri","status":$status,"upstream":"$upstream_addr"}}';
access_log {home}/access.log proof;
{frontend}
{gateway}
}}
'''
            conf=home/'nginx.conf';conf.write_text(config)
            checked=subprocess.run(['nginx','-t','-p',str(home)+'/', '-c',str(conf)],capture_output=True,text=True)
            if checked.returncode: print(checked.stderr);raise AssertionError('Nginx configuration rejected')
            p=start(['nginx','-p',str(home)+'/', '-c',str(conf),'-g','daemon off;'],'nginx')
            base=f'http://127.0.0.1:{edge}';wait(lambda:call(base,'/health')[0]==200)
            report['tests']['two_independent_gunicorn_instances']='pass'
            wait(lambda:call(base,'/ready')[0]==200)
            report['tests']['real_firebase_readiness']='pass'
            code,html,_=call(base,'/');assert code==200 and '<div id="root">' in html
            assets=re.findall(r'(?:src|href)="(/assets/[^" ]+)"',html);assert assets
            for asset in assets:assert call(base,asset)[0]==200
            report['tests']['built_react_assets_through_original_gateway']='pass'
            def signup(name):
                code,data,_=call('http://127.0.0.1:9099','/identitytoolkit.googleapis.com/v1/accounts:signUp?key=demo-key','POST',{'email':name+'-'+uuid.uuid4().hex+'@synthetic.example.invalid','password':'Local_Only_123456789','returnSecureToken':True})
                assert code==200,'Local signup failed'
                accounts.append(SyntheticAccount(data['localId'],data['idToken']))
                return data['localId'],data['idToken']
            uid,alice=signup('integrated-alice');_,bob=signup('integrated-bob')
            profile={'majors':[],'minors':[],'courses':[],'year':'2026','college':'Synthetic','about':'ALICE_LOCAL_PROFILE'}
            assert call(base,'/users/info')[0]==401
            assert call(base,'/users/info',token='SYNTHETIC_INVALID')[0]==401
            assert call(base,'/users/info','POST',profile,alice)[0]==200
            for _ in range(16):assert call(base,'/users/info',token=alice)[1]['about']==profile['about']
            code,data,_=call(base,'/users/info',token=bob);assert code==200 and (not data or data.get('about')!=profile['about'])
            report['tests']['real_auth_persistence_and_account_isolation']='pass'
            code,_,headers=call(base,'/users/info',token=alice,headers={'Origin':'https://untrusted.invalid'})
            assert code==200 and 'Access-Control-Allow-Origin' not in headers
            assert call(base,'/metrics')[0]==403
            assert call(base,'/users/info?id_token=SYNTHETIC_EDGE_MARKER')[0]==401
            report['tests']['cors_and_private_metrics_and_query_token_rejection']='pass'
            # Separate user, fixed-window boundary guarded; concurrent writes through both replicas.
            _,quota_token=signup('integrated-quota')
            if int(time.time())%60>45:time.sleep(61-int(time.time())%60)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                statuses=list(pool.map(lambda _:call(base,'/users/info','POST',profile,quota_token)[0],range(24)))
            assert statuses.count(200)==20 and statuses.count(429)==4,{'statuses':{str(k):statuses.count(k) for k in set(statuses)}}
            report['tests']['shared_quota_across_independent_processes']={'accepted':20,'rate_limited':4}
            rows=[json.loads(line) for line in (home/'access.log').read_text().splitlines()]
            targets={row['upstream'] for row in rows if row['path']=='/users/info' and row['status']==200}
            assert f'127.0.0.1:{a}' in targets and f'127.0.0.1:{b}' in targets
            report['tests']['gateway_distributed_authenticated_requests']='pass'
            confp=home/'prometheus.json';confp.write_text(json.dumps({'global':{'scrape_interval':'1s','evaluation_interval':'1s'},'rule_files':[str(ROOT/'ops/prometheus/alerts.official.yml')],'scrape_configs':[{'job_name':'coursesphere-original','static_configs':[{'targets':[f'127.0.0.1:{a}',f'127.0.0.1:{b}']}]}]}))
            start(['prometheus',f'--config.file={confp}',f'--storage.tsdb.path={home}/tsdb',f'--web.listen-address=127.0.0.1:{prom}'],'prometheus')
            def query(expr):return call(f'http://127.0.0.1:{prom}','/api/v1/query?'+urlencode({'query':expr}))[1]['data']['result']
            def up():return {v['metric']['instance']:v['value'][1] for v in query('up{job="coursesphere-original"}')}
            wait(lambda:list(up().values()).count('1')==2)
            wait(lambda:len(query('coursesphere_original_auth_attempts_total{result="accepted"}'))>=2)
            report['tests']['prometheus_collects_real_authenticated_traffic']='pass'
            stop(api_a)
            wait(lambda:up().get(f'127.0.0.1:{a}')=='0')
            for _ in range(8):assert call(base,'/users/info',token=alice)[1]['about']==profile['about']
            report['tests']['authenticated_failover_preserves_profile']='8/8 pass'
            backend(a,'api-a-recovered')
            wait(lambda:list(up().values()).count('1')==2)
            wait(lambda:call(f'http://127.0.0.1:{a}','/users/info',token=alice)[1]['about']==profile['about'])
            report['tests']['recovered_process_reads_persisted_profile']='pass'
            for p in processes:stop(p)
            for log in logs:log.flush()
            combined='\n'.join(p.read_text(errors='replace') for p in home.glob('*.log'))
            assert not any(marker in combined for marker in (alice,bob,quota_token,'SYNTHETIC_EDGE_MARKER','ALICE_LOCAL_PROFILE'))
            report['tests']['logs_exclude_tokens_queries_and_profile_content']='pass'
            report['validated']=True
    except Exception as exc:
        report['error_type']=type(exc).__name__
        report['failure_locations']=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(exc.__traceback__)]
        # Never persist response bodies, tokens or arbitrary exception strings.
        report['failed_after']=list(report['tests'])[-1:]
    finally:
        for p in reversed(processes):stop(p)
        for log in logs:log.close()
        cleaned=True
        for account in accounts:
            try:cleanup(account,dict(os.environ))
            except Exception:cleaned=False
        report["scoped_fixture_cleanup"]="PASS" if cleaned and accounts else "FAIL"
        if not cleaned or not accounts:report["validated"]=False
        OUT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['validated'] else 1
if __name__=='__main__':
    if sys.flags.optimize:raise SystemExit('Do not disable verification assertions')
    sys.exit(main())
