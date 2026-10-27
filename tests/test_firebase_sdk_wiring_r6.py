"""Execute the production Firebase adapter's actual _firebase initialization branch.

Synthetic SDK modules stand in for firebase_admin and google.auth; no network,
credential file, emulator, or real Firebase project is accessed.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import sys
import types
import unittest
from unittest.mock import patch

from backend.firebase import _firebase


class FakeSDK:
    def __init__(self, *, existing=None):
        self.existing = existing
        self.calls = []
        self.auth = types.ModuleType('firebase_admin.auth')
        self.db = types.ModuleType('firebase_admin.db')
        self.module = types.ModuleType('firebase_admin')
        self.module.auth = self.auth
        self.module.db = self.db
        creds = types.ModuleType('firebase_admin.credentials')
        creds.Base = type('Base', (), {})
        creds.Certificate = lambda path: ('cert', path)
        self.module.credentials = creds
        self.module.get_app = self.get_app
        self.module.initialize_app = self.initialize

    def get_app(self):
        if self.existing is None:
            raise ValueError('no default app')
        return self.existing

    def initialize(self, credential, options):
        self.calls.append((credential, options))
        self.existing = types.SimpleNamespace(options=options, credential=credential)


@contextmanager
def controlled_firebase(sdk, settings):
    class FakeGoogleCredentials:
        def __init__(self):
            self.token = None
    g = types.ModuleType('google')
    auth = types.ModuleType('google.auth')
    creds = types.ModuleType('google.auth.credentials')
    creds.Credentials = FakeGoogleCredentials
    auth.credentials = creds
    g.auth = auth
    modules = {'firebase_admin': sdk.module,
               'firebase_admin.credentials': sdk.module.credentials,
               'firebase_admin.auth': sdk.auth,
               'firebase_admin.db': sdk.db,
               'google': g, 'google.auth': auth, 'google.auth.credentials': creds}
    safe_env={'COURSESPHERE_USE_FIREBASE_EMULATORS': '0',
             'GCLOUD_PROJECT': '', 'FIREBASE_AUTH_EMULATOR_HOST': '',
             'FIREBASE_DATABASE_EMULATOR_HOST': '',
             'FIREBASE_CREDENTIALS_FILE': '', 'FIREBASE_DATABASE_URL': ''}
    safe_env.update(settings)
    with patch.dict(sys.modules, modules), patch.dict(os.environ, safe_env):
        yield


class FirebaseSDKWiringR6(unittest.TestCase):
    def emulator(self, **overrides):
        return dict({'COURSESPHERE_USE_FIREBASE_EMULATORS': '1',
                     'GCLOUD_PROJECT': 'demo-coursesphere-vlab',
                     'FIREBASE_AUTH_EMULATOR_HOST': '127.0.0.1:9099',
                     'FIREBASE_DATABASE_EMULATOR_HOST': '127.0.0.1:9000'}, **overrides)

    def live(self, **overrides):
        return dict({'FIREBASE_DATABASE_URL': 'https://project-default-rtdb.firebaseio.com',
                     'FIREBASE_CREDENTIALS_FILE': '/external/certificate.json'}, **overrides)

    def test_emulator_initialization_uses_only_fake_local_credential(self):
        sdk=FakeSDK()
        with controlled_firebase(sdk,self.emulator()):
            auth,db=_firebase.__wrapped__()
        self.assertIs(auth,sdk.auth)
        self.assertIs(db,sdk.db)
        self.assertEqual(len(sdk.calls),1)
        credential,options=sdk.calls[0]
        self.assertEqual(options['projectId'],'demo-coursesphere-vlab')
        self.assertTrue(options['databaseURL'].startswith('https://demo-'))
        self.assertEqual(credential.get_credential().token,'owner')
        self.assertNotIsInstance(credential,tuple)

    def test_disguised_remote_authority_fails_before_initialization(self):
        sdk=FakeSDK()
        with controlled_firebase(sdk,self.emulator(FIREBASE_AUTH_EMULATOR_HOST='remote@localhost:9099')):
            with self.assertRaises(RuntimeError):_firebase.__wrapped__()
        self.assertFalse(sdk.calls)

    def test_emulator_with_service_account_fails_before_initialization(self):
        sdk=FakeSDK()
        with controlled_firebase(sdk,self.emulator(FIREBASE_CREDENTIALS_FILE='/tmp/token.json')):
            with self.assertRaises(RuntimeError):_firebase.__wrapped__()
        self.assertFalse(sdk.calls)

    def test_emulator_rejects_preinitialized_production_default(self):
        existing=types.SimpleNamespace(options={
            'projectId':'demo-coursesphere-vlab',
            'databaseURL':'https://demo-coursesphere-vlab-default-rtdb.firebaseio.com'},
            credential=('cert','/tmp/prod.json'))
        sdk=FakeSDK(existing=existing)
        with controlled_firebase(sdk,self.emulator()):
            with self.assertRaises(RuntimeError):_firebase.__wrapped__()
        self.assertFalse(sdk.calls)

    def test_emulator_rejects_another_default_database(self):
        existing=types.SimpleNamespace(options={'projectId':'demo-coursesphere-vlab',
                          'databaseURL':'https://other.firebaseio.com'})
        sdk=FakeSDK(existing=existing)
        with controlled_firebase(sdk,self.emulator()):
            with self.assertRaises(RuntimeError):_firebase.__wrapped__()

    def test_explicit_live_config_uses_certificate(self):
        sdk=FakeSDK()
        with controlled_firebase(sdk,self.live()):
            _firebase.__wrapped__()
        self.assertEqual(len(sdk.calls),1)
        self.assertEqual(sdk.calls[0][0],('cert','/external/certificate.json'))
        self.assertEqual(sdk.calls[0][1]['databaseURL'],self.live()['FIREBASE_DATABASE_URL'])

    def test_live_suspicious_database_url_fails_before_certificate(self):
        sdk=FakeSDK()
        with controlled_firebase(sdk,self.live(FIREBASE_DATABASE_URL='https://attacker.invalid')):
            with self.assertRaises(RuntimeError):_firebase.__wrapped__()
        self.assertFalse(sdk.calls)

    def test_ambiguous_mode_never_downgrades_to_production(self):
        for mode in ('yes','true','False','2',' '):
            sdk=FakeSDK()
            with self.subTest(mode=mode), controlled_firebase(sdk,
                 self.live(COURSESPHERE_USE_FIREBASE_EMULATORS=mode)):
                with self.assertRaises(RuntimeError):_firebase.__wrapped__()
                self.assertFalse(sdk.calls)

    def test_live_rejects_different_existing_default_app(self):
        existing=types.SimpleNamespace(options={'databaseURL':'https://wrong.firebaseio.com'})
        sdk=FakeSDK(existing=existing)
        with controlled_firebase(sdk,self.live()):
            with self.assertRaises(RuntimeError):_firebase.__wrapped__()
        self.assertFalse(sdk.calls)

    def test_live_reuses_matching_existing_default_without_reinitialize(self):
        existing=types.SimpleNamespace(options={'databaseURL':self.live()['FIREBASE_DATABASE_URL']})
        sdk=FakeSDK(existing=existing)
        with controlled_firebase(sdk,self.live()):
            self.assertEqual(_firebase.__wrapped__(),(sdk.auth,sdk.db))
        self.assertFalse(sdk.calls)


if __name__ == '__main__':unittest.main()
