"""Secret preflight pattern regression checks with deliberately synthetic tokens."""
import tempfile
import unittest
from pathlib import Path
from scripts.security_preflight_v14 import scan_tree


class SecretPreflightTests(unittest.TestCase):
    def test_private_key_marker_is_flagged_without_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config.txt').write_text('-----BEGIN ' + 'PRIVATE KEY-----\nNOT_A_REAL_KEY\n')
            _,findings=scan_tree(root)
            self.assertEqual(findings,[{'file':'config.txt','rule':'private_key'}])
            self.assertNotIn('NOT_A_REAL_KEY',str(findings))

    def test_sensitive_filename_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'credentials.json').write_text('{}')
            _,findings=scan_tree(root)
            self.assertTrue(any(item['rule']=='sensitive_filename' for item in findings))

    def test_dummy_sample_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'example.env').write_text('TOKEN=replace_me\n')
            _,findings=scan_tree(root)
            self.assertFalse(findings)

    def test_ignores_build_and_cache_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sub=root/'node_modules'
            sub.mkdir()
            (sub/'credentials.json').write_text('{}')
            _,findings=scan_tree(root)
            self.assertEqual(findings,[])


if __name__=='__main__':
    unittest.main()
