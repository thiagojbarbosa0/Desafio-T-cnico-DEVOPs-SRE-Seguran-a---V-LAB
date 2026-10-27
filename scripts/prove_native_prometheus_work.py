"""Real local Prometheus + patched Flask; Firebase remains synthetic, no Docker proof."""
import hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import build_opener, ProxyHandler
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/generated/NATIVE_PROMETHEUS_WORK.json'
http=build_opener(ProxyHandler({}))
def get(url):
    with http.open(url, timeout=2) as r: return r.read().decode()
def port():
    with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def wait(predicate):
    end=time.monotonic()+35
    while time.monotonic()<end:
        try:
            if predicate(): return
        except (OSError, ValueError): pass
        time.sleep(.3)
    raise AssertionError('Timed out waiting for observable state')
def main():
    report={'validated':False,'scope':'Real native Prometheus and two patched Flask processes; synthetic Firebase, no Docker or Grafana', 'tests':{},'source_sha256':{}}
    for name in ['backend/endpoints.py','backend/observability.py','backend/metrics_access.py','integration/test_original_http_stubbed.py','scripts/flask_replica_stub_worker.py','scripts/prove_native_prometheus_work.py','ops/prometheus/alerts.official.yml']:
        report['source_sha256'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    procs=[]; logs=[]
    try:
        prometheus=shutil.which('prometheus'); promtool=shutil.which('promtool')
        assert prometheus and promtool, 'Install prometheus/promtool on PATH'
        checked=subprocess.run([promtool,'check','rules',str(ROOT/'ops/prometheus/alerts.official.yml')],capture_output=True,text=True)
        assert checked.returncode==0,checked.stdout+checked.stderr
        report['tests']['official_rules_syntax']='pass'
        with tempfile.TemporaryDirectory(prefix='coursesphere-prometheus-') as tmp:
            tmp=Path(tmp); ports=[port() for _ in range(3)]
            def worker(i):
                env={**os.environ,'COURSESPHERE_TEST_PORT':str(ports[i]),'COURSESPHERE_TEST_INSTANCE':('flask-a','flask-b')[i],'COURSESPHERE_METRICS_ENABLED':'1'}
                log=(tmp/f'flask-{i}-{len(procs)}.log').open('w');logs.append(log)
                p=subprocess.Popen([sys.executable,'-m','scripts.flask_replica_stub_worker'],cwd=ROOT,env=env,stdout=log,stderr=log);procs.append(p)
                wait(lambda: 'ok' in get(f'http://127.0.0.1:{ports[i]}/health').lower())
                return p
            a=worker(0); b=worker(1)
            config={'global':{'scrape_interval':'1s','evaluation_interval':'1s'},'rule_files':[str(ROOT/'ops/prometheus/alerts.official.yml')],'scrape_configs':[{'job_name':'coursesphere-original','static_configs':[{'targets':[f'127.0.0.1:{p}' for p in ports[:2]]}]}]}
            conf=tmp/'prometheus.json';conf.write_text(json.dumps(config))
            log=(tmp/'prometheus.log').open('w');logs.append(log)
            p=subprocess.Popen([prometheus,f'--config.file={conf}',f'--storage.tsdb.path={tmp}/data',f'--web.listen-address=127.0.0.1:{ports[2]}'],stdout=log,stderr=log);procs.append(p)
            base=f'http://127.0.0.1:{ports[2]}'
            def query(expr): return json.loads(get(base+'/api/v1/query?'+urlencode({'query':expr})))['data']['result']
            def values(): return {row['metric']['instance']:row['value'][1] for row in query('up{job="coursesphere-original"}')}
            wait(lambda: list(values().values()).count('1')==2)
            report['tests']['two_real_scrape_targets']='pass'
            for i in range(2):
                for _ in range(10): get(f'http://127.0.0.1:{ports[i]}/health')
            wait(lambda: len(query('coursesphere_original_http_requests_total{route="/health",status_class="2xx"}'))==2)
            report['tests']['http_counters_both_replicas']='pass'
            rules=json.loads(get(base+'/api/v1/rules'))['data']['groups']
            assert sum(len(g['rules']) for g in rules)==3
            report['tests']['two_slo_rules_and_replica_rule_loaded']='pass'
            a.terminate();a.wait(timeout=5)
            wait(lambda: values().get(f'127.0.0.1:{ports[0]}')=='0' and values().get(f'127.0.0.1:{ports[1]}')=='1')
            report['tests']['scrape_detects_failure']='pass'
            worker(0)
            wait(lambda: list(values().values()).count('1')==2)
            report['tests']['scrape_recovers']='pass'
            report['validated']=True
    except Exception as e: report['error']=str(e)
    finally:
        for p in reversed(procs):
            if p.poll() is None:
                p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill();p.wait()
        for log in logs: log.close()
        OUT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['validated'] else 1
if __name__=='__main__': sys.exit(main())
