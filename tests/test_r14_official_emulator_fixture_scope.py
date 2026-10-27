"""R14 original Flask integration fixture cleanup tests (no live SDK)."""
import hashlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from integration import test_official_emulators as module


class FixtureScopeTests(unittest.TestCase):
    def setUp(self):
        self.vars={
          'COURSESPHERE_USE_FIREBASE_EMULATORS':'1',
          'GCLOUD_PROJECT':module.DEMO_PROJECT,
          'FIREBASE_AUTH_EMULATOR_HOST':'127.0.0.1:9099',
          'FIREBASE_DATABASE_EMULATOR_HOST':'127.0.0.1:9000',
        }

    def test_only_demo_loopback_configuration(self):
        with patch.dict(os.environ,self.vars,clear=True):
            module.require_emulator_environment()

    def test_guard_rejects_any_remote_or_live_credentials(self):
        changes=(
            ('GCLOUD_PROJECT','live-project'),
            ('FIREBASE_DATABASE_EMULATOR_HOST','mycompany.com:9000'),
            ('FIREBASE_AUTH_EMULATOR_HOST','localhost.attacker.com:9099'),
            ('COURSESPHERE_USE_FIREBASE_EMULATORS','0'),
            ('FIREBASE_CREDENTIALS_FILE','/unsafe/key.json'),
            ('FIREBASE_DATABASE_URL','https://real.firebaseio.com'),
            ('GOOGLE_APPLICATION_CREDENTIALS','/unsafe/key.json'),
        )
        for key,value in changes:
            with self.subTest(key=key), patch.dict(os.environ,{**self.vars,key:value},clear=True):
                with self.assertRaises(RuntimeError): module.require_emulator_environment()

    def test_cleanup_only_two_created_users_and_hashed_counters(self):
        fake=types.ModuleType('firebase')
        fake.db=MagicMock()
        fake.auth=MagicMock()
        group=module.OfficialFlaskFirebaseEmulatorIntegration
        with patch.dict(os.environ,self.vars,clear=True), patch.dict(sys.modules,{'firebase':fake}), \
             patch.object(group,'alice_uid','uid_a',create=True), \
             patch.object(group,'bob_uid','uid_b',create=True):
            group.cleanup_fixture_users()
        paths=[c.args[0] for c in fake.db.reference.call_args_list]
        self.assertEqual(paths,[
            'users/uid_a',
            'server_security/rate_limits/'+hashlib.sha256(b'uid_a').hexdigest(),
            'users/uid_b',
            'server_security/rate_limits/'+hashlib.sha256(b'uid_b').hexdigest(),
        ])
        self.assertEqual([c.args[0] for c in fake.auth.delete_user.call_args_list],['uid_a','uid_b'])
        self.assertNotIn('users',paths)

    def test_partial_signup_cleans_only_account_that_exists(self):
        fake=types.ModuleType('firebase');fake.db=MagicMock();fake.auth=MagicMock()
        group=module.OfficialFlaskFirebaseEmulatorIntegration
        with patch.dict(os.environ,self.vars,clear=True), patch.dict(sys.modules,{'firebase':fake}), \
             patch.object(group,'alice_uid','uid_a',create=True), \
             patch.object(group,'bob_uid',None,create=True):
            group.cleanup_fixture_users()
        self.assertEqual(fake.auth.delete_user.call_count,1)
        self.assertEqual(fake.auth.delete_user.call_args.args[0],'uid_a')

    def test_guard_fails_before_any_sdk_cleanup(self):
        fake=types.ModuleType('firebase');fake.db=MagicMock();fake.auth=MagicMock()
        group=module.OfficialFlaskFirebaseEmulatorIntegration
        with patch.dict(os.environ,{**self.vars,'GCLOUD_PROJECT':'real-project'},clear=True), \
             patch.dict(sys.modules,{'firebase':fake}), \
             patch.object(group,'alice_uid','uid_a',create=True), \
             patch.object(group,'bob_uid','uid_b',create=True):
            with self.assertRaises(RuntimeError):group.cleanup_fixture_users()
        fake.db.reference.assert_not_called()
        fake.auth.delete_user.assert_not_called()

if __name__=='__main__':unittest.main()
