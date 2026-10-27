#!/usr/bin/env python3
"""Live, isolated Nginx proof against two real CourseSphere Python replicas.

Does not require Docker, Firebase or public network. Binds exclusively to loopback.
Writes a redacted, structured evidence file. Requires nginx installed locally.
"""
import json, os, signal, socket, subprocess, sys, tempfile, time, urllib.request, math, hashlib
from source_fingerprint import nginx_fingerprint
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence'/'generated'/'NGINX_LIVE_V9.json'

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]

def request(url, method='GET', data=None, headers=None):
    req=urllib.request.Request(url,data=data,method=method,headers=headers or {})
    with urllib.request.urlopen(req,timeout=3) as resp:
        return resp.status, dict(resp.headers), json.load(resp)

def wait_ready(url,proc,seconds=10):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if proc.poll() is not None:
            raise RuntimeError(f'Process exited before readiness, code={proc.returncode}')
        try:
            if request(url)[0]==200: return
        except (OSError,ValueError): time.sleep(.12)
    raise RuntimeError(f'Timeout waiting for {url}')

def main():
    if not shutil_which('nginx'):
        print('SKIPPED: nginx binary not installed (not a passing runtime proof).')
        return 2
    env=os.environ.copy()
    secret='A-local-test-only-shared-signing-key-which-is-long-enough'
    ports = set()
    while len(ports) < 3:
        ports.add(free_port())
    p_a,p_b,p_nginx=sorted(ports)
    evidence={'proof':'real native Nginx with two local CourseSphere Python servers',
              'scope':'synthetic demo; not Docker or Flask/Firebase', 'nginx':True,
              'ports':{'gateway':p_nginx,'api_a':p_a,'api_b':p_b},'cases':{},
              'source_fingerprint':nginx_fingerprint(),
              'source_sha256': {key:hashlib.sha256((ROOT / src).read_bytes()).hexdigest() for key,src in {
                  'nginx':'ops/nginx/gateway.conf',
                  'nginx_main':'ops/nginx/nginx.conf',
                  'local_server':'backend/local_server.py',
                  'harness':'scripts/prove_nginx_native.py',
              }.items()}}
    procs=[]
    with tempfile.TemporaryDirectory(prefix='coursesphere-nginx-') as tmp:
        base=Path(tmp)
        (base/'logs').mkdir()
        db=str(base/'demo.sqlite3')
        for name,port in [('api-a',p_a),('api-b',p_b)]:
            local={**env,'APP_MODE':'demo','PORT':str(port),'INSTANCE_ID':name,
                   'DEMO_DB_PATH':db,'DEMO_SIGNING_KEY':secret,'BIND_HOST':'127.0.0.1'}
            proc=subprocess.Popen([sys.executable,'-m','backend.local_server'], cwd=ROOT,
                      env=local,stdout=subprocess.DEVNULL,stderr=(base/f'{name}.log').open('w'))
            procs.append(proc)
        # Import the SAME gateway config that Docker Compose mounts, replacing
        # only container DNS, bound port and static asset path for a host-native run.
        service_conf=(ROOT/'ops/nginx/gateway.conf').read_text()
        service_conf=(service_conf
            .replace('api_a:8091',f'127.0.0.1:{p_a}')
            .replace('api_b:8091',f'127.0.0.1:{p_b}')
            .replace('listen 8080;',f'listen 127.0.0.1:{p_nginx};')
            .replace('/usr/share/nginx/html/lab/',str(ROOT/'dashboard')+'/'))
        assert f'127.0.0.1:{p_a}' in service_conf and f'127.0.0.1:{p_b}' in service_conf
        (base/'gateway.conf').write_text(service_conf)
        nginx_conf=f'''{'user root;' if os.geteuid() == 0 else ''}
worker_processes 1;
pid {base}/nginx.pid;
error_log {base}/logs/error.log notice;
events {{ worker_connections 128; }}
http {{
  client_body_temp_path {tmp}/body;
  proxy_temp_path {tmp}/proxy;
  fastcgi_temp_path {tmp}/fastcgi;
  uwsgi_temp_path {tmp}/uwsgi;
  scgi_temp_path {tmp}/scgi;
  types {{ text/html html; text/css css; application/javascript js; application/json json; }}
  log_format coursesphere_json escape=json
    '{{"event":"edge_http","path":"$uri","method":"$request_method","status":$status,"request_id":"$request_id"}}';
  access_log {base}/logs/access.log coursesphere_json;
  include {base}/gateway.conf;
}}
'''
        conf=base/'nginx.conf';conf.write_text(nginx_conf)
        try:
            for port,proc in [(p_a,procs[0]),(p_b,procs[1])]:
                wait_ready(f'http://127.0.0.1:{port}/api/ready',proc)
            check=subprocess.run(['nginx','-p',str(base)+'/','-c',str(conf),'-t'],capture_output=True,text=True)
            if check.returncode: raise RuntimeError(f'nginx -t failed: {check.stderr[:450]}')
            evidence['cases']['nginx_config_test']='passed: using checked-in ops/nginx/gateway.conf'
            nginx=subprocess.Popen(['nginx','-p',str(base)+'/','-c',str(conf),'-g','daemon off;'],
                                   stdout=subprocess.DEVNULL,stderr=(base/'nginx-stderr.log').open('w'))
            procs.append(nginx)
            gateway=f'http://127.0.0.1:{p_nginx}'
            wait_ready(gateway+'/api/ready',nginx)
            with urllib.request.urlopen(gateway+'/lab/', timeout=3) as html:
                assert html.status==200 and b'CourseSphere' in html.read(), 'Dashboard not served from project assets'
            evidence['cases']['static_dashboard']='passed'
            # Both the edge rejection and actual access-log redaction must hold.
            marker='SYNTHETIC_NON_SECRET_TOKEN_V19_3'
            try:
                urllib.request.urlopen(gateway+'/api/ready?id_token='+marker, timeout=3)
            except urllib.error.HTTPError as err:
                assert err.code==401, f'token-bearing URL returned HTTP {err.code}'
            else:
                raise AssertionError('Nginx allowed a token-bearing URL')
            evidence['cases']['query_token_blocked_at_edge']={'result':'passed','status':401}
            # Encoded key names and unrelated query strings must never reach
            # upstream Werkzeug logs through the API gateway either.
            for attempted in ('/api/ready?id%5Ftoken='+marker,
                              '/api/ready?arbitrary='+marker):
                try:
                    urllib.request.urlopen(gateway+attempted, timeout=3)
                except urllib.error.HTTPError as err:
                    assert err.code==400, (attempted,err.code)
                else:
                    raise AssertionError('Nginx forwarded a query string to the API')
            evidence['cases']['all_api_query_strings_blocked']={'result':'passed','status':400}


            seen={}
            latencies_ms=[]
            for _ in range(40):
                started=time.perf_counter()
                code,heads,body=request(gateway+'/api/health')
                latencies_ms.append((time.perf_counter()-started)*1000)
                assert code==200 and body['status']=='ok'
                inst=body['instance'];seen[inst]=seen.get(inst,0)+1
            assert set(seen)=={'api-a','api-b'},f'Not balanced between replicas: {seen}'
            evidence['cases']['request_distribution']={'result':'passed','counts':seen}
            ordered=sorted(latencies_ms)
            evidence['cases']['synthetic_health_sli_sample']={
                'scope':'40 sequential loopback requests; not a production SLO measurement',
                'sample_size':len(ordered),
                'success_rate':1.0,
                'p95_latency_ms':round(ordered[math.ceil(.95*len(ordered))-1],2),
                'max_latency_ms':round(ordered[-1],2),
            }
            first='api-a' if seen['api-a'] else 'api-b'
            killed=procs[0] if first=='api-a' else procs[1]
            killed.terminate();killed.wait(timeout=4)
            remaining='api-b' if first=='api-a' else 'api-a'
            # Exercise immediate Nginx retry and eventual stable routing to surviving replica.
            failover=[]
            for _ in range(8):
                code,_,body=request(gateway+'/api/ready')
                failover.append({'status':code,'instance':body['instance']})
                assert code==200 and body['instance']==remaining
            evidence['cases']['failover_after_process_crash']={'result':'passed','survivor':remaining,'requests':len(failover)}
            evidence['cases']['metrics_not_public']={'expected_status':403}
            try: urllib.request.urlopen(gateway+'/metrics',timeout=3)
            except urllib.error.HTTPError as err:
                assert err.code==403
                evidence['cases']['metrics_not_public']['result']='passed'
            else: raise AssertionError('/metrics should be 403')
            # Flush one ordinary request after the synthetic token attempt.
            request(gateway+'/api/ready')
            log_path=base/'logs/access.log'
            entries=[json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
            assert entries and all('?' not in item['path'] for item in entries)
            assert marker not in log_path.read_text(), 'Query token leaked into Nginx access log'
            assert any(item['status']==401 for item in entries), 'Denied request was not logged'
            evidence['cases']['query_free_structured_edge_logs']={'result':'passed','entries_checked':len(entries)}
            evidence['result']='PASSED'
            OUT.parent.mkdir(parents=True,exist_ok=True)
            OUT.write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n')
            print(json.dumps(evidence,indent=2,ensure_ascii=False))
            return 0
        except Exception as exc:
            evidence['result']='FAILED'
            evidence['reason']=f'{type(exc).__name__}: {str(exc)[:250]}'
            OUT.parent.mkdir(parents=True,exist_ok=True)
            OUT.write_text(json.dumps(evidence,indent=2)+'\n')
            print(json.dumps(evidence,indent=2),file=sys.stderr)
            return 1
        finally:
            for proc in reversed(procs):
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()

def shutil_which(binary):
    from shutil import which
    return which(binary)

if __name__=='__main__':
    raise SystemExit(main())
