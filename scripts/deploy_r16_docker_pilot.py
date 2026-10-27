#!/usr/bin/env python3
"""R16 opt-in Docker pilot, isolated from the previous CourseSphere/Superset stacks.

Uses an EXISTING, healthy demo Firebase container and its already-created network.
All newly managed Docker resources are under the dedicated coursesphere-r16-pilot
project. Never calls `down`, deletes volumes, or changes the old project.
"""
from __future__ import annotations
import argparse, base64, hashlib, http.client, json, os, re, secrets, shutil, socket, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
BASE=Path.home()/'V-Lab DevOps'
EVIDENCE=BASE/'CourseSphere_EVIDENCIAS'
EMULATOR='coursesphere-official-local-official_firebase_emulators-1'
PROJECT='coursesphere-r16-pilot'
COMPOSE='compose.r16.existing-emulator.yaml'
PORTS=(18081, 18091, 18092, 19092, 13001)
PUBLIC='http://127.0.0.1:18081'
A='http://127.0.0.1:18091'
B='http://127.0.0.1:18092'
PROM='http://127.0.0.1:19092'
GRAF='http://127.0.0.1:13001'
OPENER=build_opener(ProxyHandler({}))

class GateError(RuntimeError):pass

def docker(*args, timeout=90):
    result=subprocess.run(['docker',*args],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise GateError('Docker operation failed: '+args[0])
    return result.stdout

def http(url,method='GET', body=None, headers=None, timeout=5):
    data=json.dumps(body).encode('utf-8') if body is not None else None
    req=Request(url,data=data,headers={'Content-Type':'application/json',**(headers or {})},method=method)
    try:r=OPENER.open(req,timeout=timeout)
    except HTTPError as ex:r=ex
    with r:
        raw=r.read(65537)
        if len(raw)>65536:raise GateError('Oversized response from local service')
        return r.status, dict(r.headers), raw

def wait(check,seconds=90):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            value=check()
            if value:return value
        except (OSError,ValueError,KeyError,GateError,AssertionError,TimeoutError):pass
        time.sleep(1.2)
    raise GateError('Local integration condition was not observed in time')

def prom_query(query):
    status,_,raw=http(PROM+'/api/v1/query?'+urlencode({'query':query}))
    if status!=200:raise GateError('Prometheus query unavailable')
    payload=json.loads(raw)
    if payload.get('status')!='success':raise GateError('Prometheus query failed')
    return {item['metric'].get('instance'):float(item['value'][1]) for item in payload['data']['result']}

def compose(*args, env):
    # The compose input is owned by the R16 archive. The project name is fixed.
    return docker('compose','-p',PROJECT,'--env-file','.env.r16.local','-f',COMPOSE,*args,timeout=1100)

def check_emulator():
    info=json.loads(docker('inspect',EMULATOR))[0]
    labels=info.get('Config',{}).get('Labels') or {}
    if (labels.get('com.docker.compose.project')!='coursesphere-official-local'
        or labels.get('com.docker.compose.service')!='official_firebase_emulators'
        or (info.get('State',{}).get('Health') or {}).get('Status')!='healthy'
        or not info.get('State',{}).get('Running')):
        raise GateError('Existing emulator ownership, service or health did not match')
    networks=info.get('NetworkSettings',{}).get('Networks') or {}
    candidates=[]
    for name,attributes in networks.items():
        aliases=attributes.get('Aliases') or []
        if 'official_firebase_emulators' in aliases:
            detail=json.loads(docker('network','inspect',name))[0]
            if (detail.get('Driver')=='bridge' and detail.get('Scope')=='local'
                and (detail.get('Labels') or {}).get('com.docker.compose.project')=='coursesphere-official-local'):
                candidates.append(name)
    if len(candidates)!=1:raise GateError('Expected exactly one owned emulator bridge network and DNS alias')
    # The browser frontend uses these already-existing ports. Require loopback listener.
    for port in (9000,9099):
        with socket.create_connection(('127.0.0.1',port),timeout=3):pass
    return candidates[0]

def preflight_ports():
    # Even an old R16 pilot should not be replaced without an explicit action.
    existing=docker('ps','-a','--filter',f'label=com.docker.compose.project={PROJECT}','--format','{{.ID}}').strip()
    if existing:raise GateError('A R16 pilot already exists. Preserve it; inspect before a deliberate update')
    for port in PORTS:
        sock=socket.socket();sock.settimeout(.3)
        try:
            if sock.connect_ex(('127.0.0.1',port))==0:raise GateError(f'Pilot port {port} is already taken')
        finally:sock.close()

def prepare_secrets(network):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',network):
        raise GateError('Unexpected Docker network name')
    folder=ROOT/'.local'
    if folder.is_symlink():raise GateError('Local secrets directory is a symbolic link')
    folder.mkdir(exist_ok=True,mode=0o700)
    secret=folder/'official_metrics_token'
    settings=ROOT/'.env.r16.local'
    for path in (secret,settings):
        if path.is_symlink():raise GateError('Local secret is a symbolic link')
        if path.exists() and path.stat().st_mode & 0o077:raise GateError('Local secret has unsafe permissions')
    if not secret.exists():
        secret.write_text(secrets.token_urlsafe(48)+'\n');secret.chmod(0o600)
    if not settings.exists():
        settings.write_text('OFFICIAL_GRAFANA_ADMIN_PASSWORD='+secrets.token_urlsafe(36)+'\n')
        settings.chmod(0o600)
    # The network is checked from the owned emulator; avoid arbitrary env interpolation.
    current=settings.read_text().splitlines()
    current=[line for line in current if not line.startswith('R16_FIREBASE_NETWORK=')]
    if len(current)!=1 or not current[0].startswith('OFFICIAL_GRAFANA_ADMIN_PASSWORD='):
        raise GateError('Unexpected local Grafana settings')
    settings.write_text(current[0]+'\nR16_FIREBASE_NETWORK='+network+'\n')
    settings.chmod(0o600)

def proof_quota():
    # All authentication requests target a prevalidated local Firebase Emulator.
    from integration.emulator_fixture_cleanup_r14 import SyntheticAccount,cleanup
    from scripts.verify_official_replica_quota_r11 import run as run_quota
    import uuid
    email='r16-'+uuid.uuid4().hex+'@example.invalid'
    status,_,raw=http('http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=demo-key',
                      'POST',{'email':email,'password':secrets.token_urlsafe(25),'returnSecureToken':True})
    if status!=200:raise GateError('Synthetic demo user could not be created')
    identity=json.loads(raw)
    account=SyntheticAccount(identity['localId'],identity['idToken'])
    clean=False;test=None
    env={k:v for k,v in os.environ.items() if k not in ('FIREBASE_CREDENTIALS_FILE','FIREBASE_DATABASE_URL','GOOGLE_APPLICATION_CREDENTIALS','OPENAI_API_KEY')}
    env.update({'COURSESPHERE_USE_FIREBASE_EMULATORS':'1','GCLOUD_PROJECT':'demo-coursesphere-vlab',
        'FIREBASE_AUTH_EMULATOR_HOST':'127.0.0.1:9099','FIREBASE_DATABASE_EMULATOR_HOST':'127.0.0.1:9000',
        'COURSESPHERE_R11_FIREBASE_ID_TOKEN':account.token,'COURSESPHERE_DOCKER_EMULATOR_MODE':'0'})
    try:
        if int(time.time())%60>=44:time.sleep(61-int(time.time())%60)
        test=run_quota(A,B,env=env)
    finally:
        try:cleanup(account,env);clean=True
        except Exception as exc:raise GateError('Synthetic emulator fixture cleanup did not complete') from None
    if not clean or not test or not test.get('validated'):
        raise GateError('Distributed quota proof failed')
    return {k:v for k,v in test['checks'].items()} | {'fixture_cleanup':clean}

def verify(failover=True):
    result={}
    expected={'official_api_a','official_api_b'}
    def alive(url):
        status,head,raw=http(url+'/health')
        return status==200 and {k.lower():v for k,v in head.items()}.get('x-coursesphere-replica') in expected
    wait(lambda:alive(A) and alive(B) and http(PUBLIC+'/health')[0]==200,120)
    result['both_real_flask_replicas_and_nginx']='PASS'
    wait(lambda:http(A+'/ready')[0]==200 and http(B+'/ready')[0]==200,80)
    result['firebase_auth_and_rtdb_ready_on_both']='PASS'
    for endpoint,required in [('/metrics',403),('/users/info',401),('/users/info?id_token=fake',401)]:
        status,_,_=http(PUBLIC+endpoint)
        if status!=required:raise GateError('Edge security invariant failed')
    result['edge_security']='PASS'
    targets={'official_api_a:8091','official_api_b:8091'}
    wait(lambda:set(prom_query('up{job="coursesphere-original"}'))==targets and
         all(v==1 for v in prom_query('up{job="coursesphere-original"}').values()),120)
    wait(lambda:set(prom_query('coursesphere_original_firebase_ready{job="coursesphere-original"}'))==targets and
         all(v==1 for v in prom_query('coursesphere_original_firebase_ready{job="coursesphere-original"}').values()),80)
    result['prometheus_two_authenticated_scrapes_and_ready']='PASS'
    status,_,raw=http(GRAF+'/api/health')
    if status!=200 or json.loads(raw).get('database')!='ok':raise GateError('Grafana readiness failed')
    settings=dict(line.split('=',1) for line in (ROOT/'.env.r16.local').read_text().splitlines())
    auth=base64.b64encode(('admin:'+settings['OFFICIAL_GRAFANA_ADMIN_PASSWORD']).encode()).decode()
    status,_,raw=http(GRAF+'/api/dashboards/uid/coursesphere-original-v19-8',headers={'Authorization':'Basic '+auth})
    if status!=200 or json.loads(raw).get('dashboard',{}).get('uid')!='coursesphere-original-v19-8':
        raise GateError('Grafana dashboard missing')
    result['grafana_and_original_dashboard']='PASS'
    status,_,raw=http(PROM+'/api/v1/rules?type=alert')
    if status!=200:raise GateError('Prometheus alert rules unavailable')
    groups=json.loads(raw).get('data',{}).get('groups',[])
    names={r.get('name') for g in groups for r in g.get('rules',[])}
    if not {'OriginalAPIReplicaUnavailable','OriginalAPIDependencyReadinessDegraded','OriginalAPIReadinessTelemetryMissing'}<=names:
        raise GateError('Essential alert rules missing')
    result['original_alert_rules']='PASS'
    result['real_docker_distributed_quota']=proof_quota()
    if failover:
        stopped=False
        try:
            compose('stop','official_api_a',env=None);stopped=True
            wait(lambda:prom_query('up{job="coursesphere-original"}').get('official_api_a:8091')==0 and
                 prom_query('up{job="coursesphere-original"}').get('official_api_b:8091')==1,70)
            for _ in range(8):
                if http(PUBLIC+'/health')[0]!=200:raise GateError('Gateway lost availability during failover')
            result['real_docker_failover']='8/8 PASS'
        finally:
            if stopped:
                compose('start','official_api_a',env=None)
                wait(lambda:alive(A) and
                    all(v==1 for v in prom_query('up{job="coursesphere-original"}').values()),100)
                result['replica_recovered']='PASS'
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');parser.add_argument('--no-failover',action='store_true')
    args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report_dir=EVIDENCE/('R16_DOCKER_'+stamp);report_dir.mkdir(parents=True,mode=0o700,exist_ok=True)
    report={'version':'R16 Docker pilot (R15 Work derivative)','created_utc':stamp,'validated':False,
            'scope':'Docker two original Flask replicas, existing local demo Firebase Emulator, Nginx, Prometheus and Grafana',
            'checks':{},'errors':[],'old_docker_stacks_untouched':True}
    for path in ('compose.r16.existing-emulator.yaml','backend/firebase_configuration.py','scripts/deploy_r16_docker_pilot.py'):
        report.setdefault('source_sha256',{})[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    try:
        if not shutil.which('docker'):raise GateError('Docker CLI unavailable')
        if not (ROOT/'RELEASE_MANIFEST.json').is_file():raise GateError('Not an installed managed release')
        if not args.verify_only:
            net=check_emulator();preflight_ports();prepare_secrets(net)
            compose('config','--quiet',env=None)
            report['checks']['existing_emulator_preflight']='PASS'
            # Build only pilot-owned services. No `down`, `rm`, network connect or delete.
            compose('up','-d','--build',env=None)
            report['checks']['isolated_compose_up']='PASS'
        report['checks'].update(verify(failover=not args.no_failover))
        report['validated']=True
    except (GateError,KeyError,ValueError,OSError,subprocess.TimeoutExpired) as exc:
        report['errors'].append(type(exc).__name__+': '+str(exc)[:180])
    finally:
        report['pending']=['formal upstream 5 findings review','remaining npm dependency advisories','V19.15 full source reconciliation']
        (report_dir/'RESUMO.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        (report_dir/'SHA256SUMS.txt').write_text(hashlib.sha256((report_dir/'RESUMO.json').read_bytes()).hexdigest()+'  RESUMO.json\n')
        print(json.dumps({'validated':report['validated'],'checks':report['checks'],'errors':report['errors'],'evidence':str(report_dir)},ensure_ascii=False,indent=2))
    return 0 if report['validated'] else 1

if __name__=='__main__':sys.exit(main())
