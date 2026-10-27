"""Fail-closed release ZIP boundary tests using only synthetic fixtures."""
import tempfile
import unittest
from pathlib import Path
import zipfile
from scripts.verify_release_archive_vlab import audit_archive

class ReleaseArchiveAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'delivery.zip'

    def make(self, contents):
        with zipfile.ZipFile(self.path,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for path,content in contents:
                z.writestr(path,content)
        return audit_archive(self.path)

    def test_safe_archive(self):
        r=self.make([('coursesphere/README.md','ok'),('coursesphere/.env.example','placeholder')])
        self.assertTrue(r['validated'],r)
    def test_traversal(self):self.assertFalse(self.make([('../secret','x')])['validated'])
    def test_absolute(self):self.assertFalse(self.make([('/tmp/secret','x')])['validated'])
    def test_windows_traversal(self):self.assertFalse(self.make([('..\\secret','x')])['validated'])
    def test_colon_drive(self):self.assertFalse(self.make([('C:/secret','x')])['validated'])
    def test_dot_component(self):self.assertFalse(self.make([('dir/./file','x')])['validated'])
    def test_private_local(self):self.assertFalse(self.make([('app/.local/log','x')])['validated'])
    def test_python_cache(self):self.assertFalse(self.make([('app/__pycache__/x.pyc','x')])['validated'])
    def test_env(self):self.assertFalse(self.make([('app/.env','TOKEN=x')])['validated'])
    def test_env_observability(self):self.assertFalse(self.make([('app/.env.official.observability','SECRET=x')])['validated'])
    def test_npmrc(self):self.assertFalse(self.make([('app/.npmrc','x')])['validated'])
    def test_duplicate_case_collision(self):
        self.assertFalse(self.make([('app/Readme','a'),('app/readme','b')])['validated'])
    def test_symlink(self):
        with zipfile.ZipFile(self.path,'w') as z:
            info=zipfile.ZipInfo('app/link')
            info.create_system=3
            info.external_attr=(0o120777<<16)
            z.writestr(info,'target')
        self.assertFalse(audit_archive(self.path)['validated'])
    def test_truncated_zip(self):
        self.path.write_bytes(b'not a zip')
        self.assertFalse(audit_archive(self.path)['validated'])
    def test_missing_zip(self):
        self.assertFalse(audit_archive(self.path)['validated'])
    def test_symlink_source(self):
        dest=Path(self.tmp.name)/'another.zip'
        with zipfile.ZipFile(dest,'w') as z:z.writestr('app/a','x')
        self.path.symlink_to(dest)
        self.assertFalse(audit_archive(self.path)['validated'])

if __name__=='__main__':unittest.main()
