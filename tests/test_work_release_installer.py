import contextlib,hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from scripts.install_release_work import inspect_archive,install,activate,ROOT_NAME,RELEASE

def archive(path,files=None,extra=None):
    files=files or {'backend/app.py':'pass\n','scripts/app.py':'pass\n','integration/app.py':'pass\n','tests/test_ok.py':'import unittest\nclass Test(unittest.TestCase):\n def test_ok(self):self.assertTrue(True)\n'}
    manifest={'release':RELEASE,'files':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in files.items()}}
    with zipfile.ZipFile(path,'w') as z:
        for n,s in files.items():z.writestr(ROOT_NAME+'/'+n,s)
        z.writestr(ROOT_NAME+'/RELEASE_MANIFEST.json',json.dumps(manifest))
        if extra:extra(z)
    return path

class ReleaseInstallerTests(unittest.TestCase):
    def test_rejects_traversal_symlink_duplicate_and_unexpected_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.zip'
            for name in ('../escape','/absolute',ROOT_NAME+'/a/../escape',ROOT_NAME+'/a//alias',ROOT_NAME+'/unexpected'):
                archive(p,extra=lambda z:z.writestr(name,'bad'))
                with self.assertRaises(ValueError):inspect_archive(p)
            def symlink(z):
                i=zipfile.ZipInfo(ROOT_NAME+'/link');i.create_system=3;i.external_attr=0o120777<<16;z.writestr(i,'/tmp')
            archive(p,extra=symlink)
            with self.assertRaises(ValueError):inspect_archive(p)
    def test_rejects_wrong_hash_or_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.zip'
            for value in ({'release':'wrong','files':{}},{'release':RELEASE,'files':{'file':'0'*64}}):
                with zipfile.ZipFile(p,'w') as z:
                    z.writestr(ROOT_NAME+'/RELEASE_MANIFEST.json',json.dumps(value));z.writestr(ROOT_NAME+'/file','actual')
                with self.assertRaises(ValueError):inspect_archive(p)
    def test_install_update_preserves_config_and_old_release_then_rollback(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp)/'project';p=archive(Path(tmp)/'release.zip')
            first=install(p,base,prepare=False);self.assertTrue(first['activated'])
            old=Path(first['active_path']);(old/'.env.official.observability').write_text('TEST_ONLY=value\n')
            second=install(p,base,prepare=False);self.assertTrue(second['activated']);new=Path(second['active_path'])
            self.assertNotEqual(old,new);self.assertTrue(old.is_dir())
            self.assertEqual((new/'.env.official.observability').read_text(),'TEST_ONLY=value\n')
            self.assertEqual((new/'.env.official.observability').stat().st_mode&0o777,0o600)
            self.assertTrue((Path(second['evidence'])/'RESUMO.json').is_file())
            activate(base,old);self.assertEqual((base/'CourseSphere_ATUAL').resolve(),old)
    def test_failed_validation_keeps_active_release(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp)/'project';p=archive(Path(tmp)/'release.zip');first=install(p,base,prepare=False)
            archive(p,{'backend/app.py':'invalid python syntax!','scripts/a.py':'pass','integration/a.py':'pass'})
            second=install(p,base,prepare=False);self.assertFalse(second['activated'])
            self.assertEqual((base/'CourseSphere_ATUAL').resolve(),Path(first['active_path']))
            self.assertEqual(second['steps']['compile'],'FAIL')
