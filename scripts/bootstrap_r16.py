#!/usr/bin/env python3
"""Single ZIP Fedora installer + Docker pilot + permanent private evidence.

This small bootstrap is embedded inside the R16 archive, extracted only AFTER
external SHA256 verification. It invokes the archive's built-in strict installer.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess, sys, tempfile, zipfile

ROOT_NAME='CourseSphere_R16_DOCKER_PILOT'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--zip',type=Path,required=True)
    args=parser.parse_args()
    base=Path.home()/'V-Lab DevOps'
    evidence=base/'CourseSphere_EVIDENCIAS'/('R16_BOOTSTRAP_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    evidence.mkdir(parents=True,mode=0o700,exist_ok=True)
    result={'version':'R16_DOCKER_PILOT','steps':{},'zip':args.zip.name,'evidence':str(evidence),'docker_deployed':False}
    oldmask=os.umask(0o077)
    try:
        if not args.zip.is_file() or args.zip.is_symlink() or args.zip.parent.resolve()!=(Path.home()/'Downloads').resolve():
            raise RuntimeError('ZIP must be a regular non-symlink file in ~/Downloads')
        with zipfile.ZipFile(args.zip) as z:
            filename=ROOT_NAME+'/scripts/install_release_work.py'
            installer=z.read(filename)
        print('[OK] Arquivo localizado; iniciando instalacao verificada.',flush=True)
        with tempfile.TemporaryDirectory(prefix='coursesphere-r16-bootstrap-') as tmp:
            stage=Path(tmp)/'install_release.py';stage.write_bytes(installer)
            stage.chmod(0o600)
            cmd=[sys.executable,str(stage),'--zip',str(args.zip),'--base-dir',str(base)]
            with (evidence/'INSTALACAO.log').open('w') as out:
                code=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=2700).returncode
        result['steps']['installation']='PASS' if code==0 else 'FAIL'
        if code!=0:raise RuntimeError('Installation failed; previous active release remains intact')
        active=(base/'CourseSphere_ATUAL').resolve(strict=True)
        if active.parent!=(base/'releases').resolve() or not active.name.startswith('release-R16_DOCKER_PILOT-'):
            raise RuntimeError('Active release path is not a managed R16 release')
        result['active_release']=str(active)
        print('[PASS] R16 instalada. R15 anterior preservada.',flush=True)
        print('[INFO] Tentando Docker isolado usando o Firebase Emulator ja existente...',flush=True)
        py=active/'.venv/bin/python'
        if not py.is_file():py=Path(sys.executable)
        with (evidence/'DOCKER_PILOTO.log').open('w') as out:
            code=subprocess.run([str(py),str(active/'scripts/deploy_r16_docker_pilot.py')],cwd=active,
                                stdout=out,stderr=subprocess.STDOUT,timeout=2700).returncode
        result['steps']['docker_pilot']='PASS' if code==0 else 'FAIL'
        result['docker_deployed']=code==0
        if code!=0:
            print('[PENDENTE] Docker piloto: consultar DOCKER_PILOTO.log e R16_DOCKER_*/RESUMO.json.',flush=True)
        else:print('[PASS] Docker: Flask A/B + Firebase + Nginx + Prometheus + Grafana + quota + failover.',flush=True)
    except Exception as exc:
        result.setdefault('error',type(exc).__name__+': '+str(exc)[:160])
        if 'installation' not in result['steps']:result['steps']['installation']='FAIL'
        print('[ATENCAO]',result['error'],flush=True)
    finally:
        (evidence/'RESUMO.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        (evidence/'SHA256SUMS.txt').write_text(hashlib.sha256((evidence/'RESUMO.json').read_bytes()).hexdigest()+'  RESUMO.json\n')
        os.umask(oldmask)
        print('EVIDENCIAS:',evidence)
        print('RESUMO:',evidence/'RESUMO.json')
    return 0 if result.get('docker_deployed') else 1

if __name__=='__main__':sys.exit(main())
