"""V19.5: credential disclosure provenance without copying/exposing the secret."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.prove_upstream_credential_f04 import TARGET, collect, main
from scripts.security_preflight_v14 import scan_tree


class F04SanitizedProofTests(unittest.TestCase):
    def make_source(self, directory, secret='SYNTHETIC_LOCAL_TEST_ONLY_12345', client_id='SYNTHETIC-CLIENT-123'):
        target = Path(directory) / 'upstream.zip'
        with ZipFile(target, 'w') as archive:
            archive.writestr('CourseSphere-main/' + TARGET,
                             json.dumps({'client_id': client_id, 'client_secret': secret}))
        return target

    def test_credential_metadata_and_no_value_or_value_hash(self):
        with tempfile.TemporaryDirectory() as d:
            archive = self.make_source(d)
            report = collect(archive)
            wire = json.dumps(report)
            self.assertEqual(report['finding_id'], 'F04')
            self.assertEqual(report['file_evidence']['credential_currently_valid'], 'NOT_TESTED')
            self.assertFalse(report['file_evidence']['external_service_contacted'])
            self.assertNotIn('SYNTHETIC_LOCAL_TEST_ONLY_12345', wire)
            self.assertNotIn('SYNTHETIC-CLIENT-123', wire)
            self.assertNotIn(hashlib.sha256(b'SYNTHETIC_LOCAL_TEST_ONLY_12345').hexdigest(), wire)
            self.assertEqual(report['source_snapshot_sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_placeholder_does_not_create_finding(self):
        with tempfile.TemporaryDirectory() as d:
            archive = self.make_source(d, secret='REPLACE_WITH_YOUR_CLIENT_SECRET')
            with self.assertRaisesRegex(ValueError, 'placeholder'):
                collect(archive)

    def test_missing_credential_file_cannot_validate(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'upstream.zip'
            with ZipFile(archive, 'w') as z:
                z.writestr('CourseSphere-main/README.md', 'safe')
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                collect(archive)
            evidence = Path(d) / 'evidence.json'
            self.assertEqual(main(['--source', str(archive), '--output', str(evidence)]), 2)
            self.assertFalse(evidence.exists())

    def test_duplicate_entry_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'upstream.zip'
            with ZipFile(archive, 'w') as z:
                z.writestr('CourseSphere-main/' + TARGET, '{"client_id":"x","client_secret":"x"}')
                z.writestr('AlternateCourseSphere/' + TARGET, '{"client_id":"x","client_secret":"x"}')
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                collect(archive)


class CredentialJSONPreflightTests(unittest.TestCase):
    def test_renamed_nested_oauth_secret_detected_without_printing_value(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'renamed.json').write_text(json.dumps({'api': {'client_secret': 'SYNTHETIC_NESTED_SECRET_1234'}}))
            count, findings = scan_tree(root)
            self.assertEqual(count, 1)
            self.assertIn({'file': 'renamed.json', 'rule': 'credential_shaped_json_value'}, findings)
            self.assertNotIn('SYNTHETIC_NESTED_SECRET_1234', json.dumps(findings))

    def test_placeholder_and_field_name_alone_are_not_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'template.json').write_text(json.dumps({'client_secret': 'REPLACE_WITH_YOUR_CLIENT_SECRET',
                                                          'notes': 'client_secret'}))
            self.assertEqual(scan_tree(root)[1], [])

    def test_json_list_nested_secret_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'settings.json').write_text(json.dumps({'settings': [
                {'refresh_token': 'SYNTHETIC_REFRESH_TOKEN_VALUE_1234'}]}))
            self.assertEqual([x['rule'] for x in scan_tree(root)[1]], ['credential_shaped_json_value'])


if __name__ == '__main__':
    unittest.main()
