#!/usr/bin/env python3
"""Verified local release installation. No sudo, container mutation or volume deletion."""
import argparse, hashlib, json, os, re, shutil, socket, stat, subprocess, sys, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
RELEASE='R16_DOCKER_PILOT'
ROOT_NAME='CourseSphere_R16_DOCKER_PILOT'

def inspect_archive(path):
    with zipfile.ZipFile(path) as z:
        infos=z.infolist(); names=[i.filename for i in infos]
        if len(names)!=len(set(names)) or len(names)>5000:raise ValueError('Duplicate or excessive ZIP entries')
        total=0
        for i in infos:
            n=PurePosixPath(i.filename); mode=i.external_attr>>16
            if (not n.parts or n.parts[0]!=ROOT_NAME or n.is_absolute() or '..' in n.parts
                or str(n)!=i.filename.rstrip('/') or '\\' in i.filename or ':' in i.filename or any(ord(c)<32 for c in i.filename)
                or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR))):
                raise ValueError('Unsafe archive member')
            total+=i.file_size
            if i.file_size>100_000_000 or total>300_000_000:raise ValueError('Archive size exceeded')
        info=json.loads(z.read(ROOT_NAME+'/RELEASE_MANIFEST.json'))
        if info.get('release')!=RELEASE or not isinstance(info.get('files'),dict):raise ValueError('Wrong release')
        expected={ROOT_NAME+'/'+n for n in info['files']}|{ROOT_NAME+'/RELEASE_MANIFEST.json'}
        if {i.filename for i in infos if not i.is_dir()}!=expected:raise ValueError('Unexpected or missing files')
        for name,digest in info['files'].items():
            if hashlib.sha256(z.read(ROOT_NAME+'/'+name)).hexdigest()!=digest:raise ValueError('Hash mismatch')
        if z.testzip() is not None:raise ValueError('ZIP CRC mismatch')
        return info

def activate(base,release):
    active=base/'CourseSphere_ATUAL';temporary=base/('.active-'+str(os.getpid()))
    if active.exists() and not active.is_symlink():raise ValueError('Active path is an unmanaged directory; preserved')
    temporary.symlink_to(release,target_is_directory=True)
    os.replace(temporary,active)

def install(archive,base,prepare=True):
    base=base.expanduser().resolve();base.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=base/'CourseSphere_EVIDENCIAS'/stamp;evidence.mkdir(parents=True)
    result={'release':RELEASE,'steps':{},'activated':False,'evidence':str(evidence),'pending':['Docker full stack','Grafana','AppSec final review']}
    lock=base/'.coursesphere-install.lock';stage=None
    try:
        import fcntl
        with lock.open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            info=inspect_archive(archive);result['steps']['archive']='PASS'
            result['zip_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
            active=base/'CourseSphere_ATUAL';previous=active.resolve() if active.is_symlink() else None
            if active.exists() and not active.is_symlink():raise ValueError('Unmanaged active directory preserved')
            releases=base/'releases';releases.mkdir(exist_ok=True)
            stage=Path(tempfile.mkdtemp(prefix='release-R16_DOCKER_PILOT-',dir=releases))
            with zipfile.ZipFile(archive) as z:
                for name in info['files']:
                    dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(z.read(ROOT_NAME+'/'+name));dest.chmod(0o644)
                (stage/'RELEASE_MANIFEST.json').write_bytes(z.read(ROOT_NAME+'/RELEASE_MANIFEST.json'))
            if previous:
                # Retain the entire old release; copy only declared local configuration.
                for name in ('.env.official.observability','.local/official_metrics_token'):
                    source=previous/name
                    if source.is_symlink() or any(p.is_symlink() for p in source.parents if p!=previous and previous in p.parents):raise ValueError('Symlink in local config')
                    if source.is_file():
                        if source.stat().st_size>65536:raise ValueError('Local config too large')
                        target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);target.chmod(0o600)
            def run(name,args,timeout=300,env=None):
                with (evidence/(name+'.log')).open('w') as log:
                    try:code=subprocess.run(args,cwd=stage,env=env,stdout=log,stderr=log,timeout=timeout).returncode
                    except (OSError,subprocess.TimeoutExpired):code=124
                result['steps'][name]='PASS' if code==0 else 'FAIL'
                return code==0
            py=sys.executable
            if not run('compile',[py,'-m','compileall','-q','backend','scripts','integration']):raise ValueError('Compile failed')
            if not run('offline',[py,'-m','unittest','discover','-s','tests'],300):raise ValueError('Regression failed; previous release remains active')
            if prepare:
                if not run('venv',[py,'-m','venv','.venv']):raise ValueError('Virtualenv unavailable')
                py=str(stage/'.venv/bin/python')
                if not run('pip',[py,'-m','pip','install','-r','backend/requirements.txt','gunicorn==23.0.0'],600):raise ValueError('Python dependencies failed')
                if not shutil.which('npm'):raise ValueError('Node/npm required before activation')
                if not run('react_build',['bash','scripts/verify_frontend_build_v14_2.sh'],600):raise ValueError('React build failed')
                if shutil.which('docker'):
                    run('docker_info',['docker','info','--format','{{.ServerVersion}}'],20)
                    run('compose_config',['docker','compose','-f','compose.official.yaml','config','--quiet'],20)
                else:result['steps']['docker']='SKIP'
                occupied=[]
                for port in (9000,9099,8081,9090,3000):
                    with socket.socket() as sock:
                        sock.settimeout(.15)
                        if sock.connect_ex(('127.0.0.1',port))==0:occupied.append(port)
                result['occupied_ports']=occupied
                env={**os.environ,'PATH':str(stage/'.venv/bin')+os.pathsep+os.environ.get('PATH','')}
                if not any(p in occupied for p in (9000,9099)) and shutil.which('java') and (shutil.which('firebase') or shutil.which('npx')):
                    if not run('firebase',['bash','scripts/verify_official_emulators.sh'],900,env):raise ValueError('Emulator validation failed')
                else:result['steps']['firebase']='SKIP'
                run('release_gate',[py,'-m','scripts.release_gate_r14'],40)
            else:result['steps']['dependencies']='SKIP'
            if previous:
                backups=base/'backups';backups.mkdir(exist_ok=True)
                (backups/(stamp+'.json')).write_text(json.dumps({'previous':str(previous),'next':str(stage)},indent=2))
            # Keep staging path stable: venv scripts contain absolute paths.
            # Rename would silently break pip/gunicorn executable shebangs.
            activate(base,stage);result['activated']=True
            result['active_path']=str(stage);result['previous']=str(previous) if previous else None
            result['rollback_command']=['python3',str(stage/'scripts/install_release_work.py'),'--base-dir',str(base),'--rollback',str(previous)] if previous else None
            if (stage/'evidence').exists():shutil.copytree(stage/'evidence',evidence/'project-evidence',dirs_exist_ok=True)
            (evidence/'RELEASE_MANIFEST.json').write_text(json.dumps(info,indent=2))
    except Exception as exc:
        result['steps']['installation']='FAIL';result['error']=type(exc).__name__+': '+str(exc)
        result['failed_stage']=str(stage) if stage else None
    finally:
        (evidence/'RESUMO.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(result,indent=2,ensure_ascii=False))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',type=Path);p.add_argument('--base-dir',type=Path,default=Path.home()/'V-Lab DevOps');p.add_argument('--skip-deps',action='store_true');p.add_argument('--rollback',type=Path);args=p.parse_args()
    if args.rollback:
        base=args.base_dir.expanduser().resolve();target=args.rollback.resolve()
        if target.parent!=base/'releases' or not (target/'RELEASE_MANIFEST.json').is_file():p.error('Rollback target must be an existing managed release')
        import fcntl
        with (base/'.coursesphere-install.lock').open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            activate(base,target)
            output=base/'CourseSphere_EVIDENCIAS'/('rollback-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
            output.mkdir(parents=True)
            (output/'RESUMO.json').write_text(json.dumps({'rollback':'PASS','active':str(target)},indent=2))
        print('Rollback completed:',target);return 0
    if not args.zip:p.error('--zip required')
    return 0 if install(args.zip.resolve(),args.base_dir,not args.skip_deps)['activated'] else 1
if __name__=='__main__':sys.exit(main())
