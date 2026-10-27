import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts.check_release_archive_v19_5 import scan_release, scan_large_jsonl
from io import BytesIO

class ReleaseArchiveTests(unittest.TestCase):
    def mkzip(self,dir,items):
        path=Path(dir)/'release.zip'
        with ZipFile(path,'w') as z:
            for name,content in items:
                z.writestr(name,content)
        return path

    def test_safe_release_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.mkzip(d,[('CourseSphere/README.md','Safe'),('CourseSphere/config.example.json','{"client_secret":"REPLACE_WITH_SECRET"}')])
            self.assertEqual(scan_release(p)['status'],'PASS')

    def test_renamed_secret_json_fails_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.mkzip(d,[('CourseSphere/settings.json','{"client_secret":"SYNTHETIC_SECRET_NOT_REAL_1234"}')])
            result=scan_release(p)
            self.assertEqual(result['status'],'FAIL')
            self.assertEqual(result['findings'][0]['issue'],'credential_shaped_json_value')
            self.assertNotIn('SYNTHETIC_SECRET_NOT_REAL_1234',str(result))

    def test_nested_archives_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.mkzip(d,[('CourseSphere/original.zip','x')])
            self.assertEqual(scan_release(p)['findings'][0]['issue'],'nested_archive_not_reviewed')

    def test_dotenv_and_runtime_dirs_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.mkzip(d,[('CourseSphere/.env','x'),('CourseSphere/.venv/bin/python','x')])
            self.assertEqual(len(scan_release(p)['findings']),2)

    def test_large_jsonl_streaming_scans_without_echoing_values(self):
        payload=BytesIO((b'{"title":"course"}\n' * 300))
        self.assertIsNone(scan_large_jsonl(payload))
        value=BytesIO(b'{"client_secret":"SYNTHETIC_LOCAL_ONLY_123456789"}\n')
        self.assertEqual(scan_large_jsonl(value),'oauth_json_assignment')

    def test_traversal_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.mkzip(d,[('CourseSphere/../../outside.txt','x')])
            self.assertEqual(scan_release(p)['findings'][0]['issue'],'unsafe_archive_path')

if __name__=='__main__':unittest.main()
