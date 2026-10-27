"""V19: ensure the client cannot bypass Flask validation and rate limits.

These are source/configuration regression guards, NOT a substitute for running
Firebase's actual security-rule evaluator. The latter runs in emulator test 21.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FirebaseWriteBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads((ROOT / 'ops/firebase/database.rules.json').read_text())['rules']

    def test_root_remains_default_deny(self):
        self.assertIs(self.rules['.write'], False)
        self.assertIs(self.rules['.read'], False)

    def test_client_writes_to_own_uid_subtree_denied(self):
        self.assertIs(self.rules['users']['$uid']['.write'], False)
        self.assertEqual(self.rules['users']['$uid']['.read'],
                         'auth != null && auth.uid === $uid')

    def test_no_overriding_nested_write_grants(self):
        def walk(value, path='rules'):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == '.write':
                        self.assertIs(item, False, f'Client bypass grant in {path}')
                    walk(item, path + '/' + key)
        walk(self.rules)

    def test_no_untrusted_storage_namespace_grants(self):
        self.assertNotIn('server_security', self.rules)
        self.assertNotIn('.validate', self.rules)

    def test_rtdb_client_frontend_has_no_direct_write_contract(self):
        # The frontend only authenticates via the Firebase client SDK; sensitive
        # mutations must pass through Flask, where schema and quotas are checked.
        for path in (ROOT / 'frontend/src').rglob('*'):
            if path.suffix not in ('.ts', '.tsx'):
                continue
            source = path.read_text(encoding='utf-8')
            self.assertNotRegex(source, r"from\s*['\"]firebase/database['\"][^;]*\bset\s*\(")
        src = (ROOT / 'backend/endpoints.py').read_text()
        self.assertIn('Firebase.enforce_quota(user_id, "chat_write")', src)
        self.assertIn('Firebase.save_chat(user_id, chat_id, messages)', src)
        self.assertLess(src.index('Firebase.enforce_quota(user_id, "chat_write")'),
                        src.index('Firebase.save_chat(user_id, chat_id, messages)'))

    def test_live_emulator_check_is_mandatory_for_passing(self):
        src = (ROOT / 'integration/test_official_emulators.py').read_text()
        runner = (ROOT / 'integration/run_official_emulator_tests.py').read_text()
        self.assertIn('def test_21_rtdb_client_cannot_bypass_flask_validation_and_quota', src)
        self.assertIn('own_read', src)
        self.assertIn('direct_writes', src)
        self.assertIn('result.testsRun == 23', runner)
        self.assertIn('len(cases) == 23', runner)

    def test_existing_profile_and_auth_is_preserved(self):
        src = (ROOT / 'backend/endpoints.py').read_text()
        self.assertIn('Firebase.get_user_info(uid)', src)
        self.assertIn('Firebase.set_user_info(uid, user_info)', src)
        self.assertIn('uid = verified_uid()', src)
        self.assertIn('user_info = validate_profile(data)', src)


if __name__ == '__main__':
    unittest.main()
