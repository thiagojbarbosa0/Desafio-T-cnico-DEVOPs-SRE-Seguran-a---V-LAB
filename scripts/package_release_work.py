"""Build the single R16 Docker Pilot release with a strict member/hash manifest."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from work_checkpoint import eligible
from scripts.install_release_work import inspect_archive,ROOT_NAME,RELEASE

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('Output must be outside source')
    out.parent.mkdir(parents=True,exist_ok=True)
    files={}
    for f in sorted(ROOT.rglob('*')):
        if eligible(f,ROOT) and f.name!='RELEASE_MANIFEST.json':files[f.relative_to(ROOT).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
    manifest={'release':RELEASE,'base':'R15 Work (not integrated V19.15)','files':files}
    (ROOT/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name in [*files,'RELEASE_MANIFEST.json']:z.write(ROOT/name,ROOT_NAME+'/'+name)
    inspect_archive(out)
    digest=hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix('.zip.sha256').write_text(digest+'  '+out.name+'\n')
    print(json.dumps({'path':str(out),'sha256':digest,'files':len(files),'integrity':'PASS'}))
if __name__=='__main__':main()
