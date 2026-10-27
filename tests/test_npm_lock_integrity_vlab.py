import copy
import base64
import unittest
from scripts.npm_lock_integrity_vlab import scan

class NpmLockIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.lock={'lockfileVersion':3,'packages':{
            '':{'name':'frontend','version':'1.0.0'},
            'node_modules/real':{'version':'1.2.3',
                'resolved':'https://registry.npmjs.org/real/-/real-1.2.3.tgz',
                'integrity':'sha512-'+base64.b64encode(b'Z'*64).decode()}}}
    def test_valid(self):self.assertTrue(scan(self.lock)['validated'])
    def test_real_lock_and_manifest_match(self):
        from pathlib import Path
        import json
        root=Path(__file__).resolve().parents[1]
        lock=json.loads((root/'frontend/package-lock.json').read_text())
        manifest=json.loads((root/'frontend/package.json').read_text())
        self.assertTrue(scan(lock,manifest)['validated'])
    def test_drift_from_manifest_rejected(self):
        manifest={'name':'frontend','version':'1.0.0','dependencies':{'real':'^1.0.0'}}
        self.assertFalse(scan(self.lock,manifest)['validated'])
    def test_manifest_parity_positive(self):
        self.lock['packages']['']['dependencies']={'real':'^1.0.0'}
        manifest={'name':'frontend','version':'1.0.0','dependencies':{'real':'^1.0.0'}}
        self.assertTrue(scan(self.lock,manifest)['validated'])
    def test_incomplete_base64_hash_rejected(self):
        self.lock['packages']['node_modules/real']['integrity']='sha512-AAAA'
        self.assertFalse(scan(self.lock)['validated'])
    def test_corrupt_base64_hash_rejected(self):
        self.lock['packages']['node_modules/real']['integrity']='sha512-AAAAAAAAAAAAAA=='
        self.assertFalse(scan(self.lock)['validated'])
    def test_count(self):self.assertEqual(scan(self.lock)['package_count'],1)
    def test_no_root(self):
        del self.lock['packages']['']
        self.assertFalse(scan(self.lock)['validated'])
    def test_http_rejected(self):
        self.lock['packages']['node_modules/real']['resolved']='http://registry.npmjs.org/r'
        self.assertFalse(scan(self.lock)['validated'])
    def test_git_url_rejected(self):
        self.lock['packages']['node_modules/real']['resolved']='git+https://github.com/a/b'
        self.assertFalse(scan(self.lock)['validated'])
    def test_credentials_in_url_rejected(self):
        self.lock['packages']['node_modules/real']['resolved']='https://u:pass@registry.npmjs.org/r'
        self.assertFalse(scan(self.lock)['validated'])
    def test_invalid_port_is_fail_closed(self):
        self.lock['packages']['node_modules/real']['resolved']='https://registry.npmjs.org:invalid/x'
        self.assertFalse(scan(self.lock)['validated'])
    def test_missing_integrity(self):
        del self.lock['packages']['node_modules/real']['integrity']
        self.assertFalse(scan(self.lock)['validated'])
    def test_weak_integrity(self):
        self.lock['packages']['node_modules/real']['integrity']='sha1-xxx'
        self.assertFalse(scan(self.lock)['validated'])
    def test_unpinned_version(self):
        self.lock['packages']['node_modules/real']['version']='^1.2.0'
        self.assertFalse(scan(self.lock)['validated'])
    def test_install_scripts_are_review_queue(self):
        self.lock['packages']['node_modules/real']['hasInstallScript']=True
        x=scan(self.lock)
        self.assertTrue(x['validated']);self.assertEqual(x['install_script_packages'],1)
    def test_missing_packages(self):
        self.assertFalse(scan({'lockfileVersion':3})['validated'])
    def test_v2_requires_review(self):
        self.lock['lockfileVersion']=2
        self.assertFalse(scan(self.lock)['validated'])

if __name__=='__main__':unittest.main()
