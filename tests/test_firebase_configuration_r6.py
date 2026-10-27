"""R6 security checks: Firebase must never choose an ambiguous emulator host.

Tests are SDK-free and network-free, including process-global default-app reuse.
"""
from __future__ import annotations
import types
import unittest
from unittest.mock import patch
from backend.firebase_configuration import (
    emulator_host, validate_emulators, validate_live, validate_existing_default_app)


class FirebaseConfigurationR6(unittest.TestCase):
    def test_valid_emulator_hosts(self):
        for host in ('localhost:9099','127.0.0.1:9099','[::1]:9099',
                     'LOCALHOST:1','127.0.0.1:65535'):
            with self.subTest(host=host):
                self.assertEqual(emulator_host(host,'AUTH'),host)

    def test_reject_remote_or_ambiguous_emulator_authority(self):
        bad = ('', 'localhost', 'localhost:0', 'localhost:65536',
               'localhost:9099/', 'localhost:9099/evil', 'localhost:9099?q=1',
               'localhost:9099#f', 'foo@localhost:9099', 'a:pass@127.0.0.1:9099',
               'https://localhost:9099', '//localhost:9099', 'localhost:9099@remote.tld',
               'localhost:9099:1', 'localhost:9099\\n', 'localhost:9099 ',
               '127.0.0.2:9099', '192.168.0.1:9099', 'example.com:9099',
               '::1:9099', '[fe80::1]:9099', 'localhost:abc', None, 9099)
        for value in bad:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                emulator_host(value,'AUTH')

    def test_project_is_never_real_in_emulator_mode(self):
        for project in ('real-course', 'demo-', 'demo-a--b', 'demo-a-',
                        'DEMO-a', 'demo_a','demo-a/evil',' demo-a',None):
            with self.subTest(project=project),self.assertRaises(RuntimeError):
                validate_emulators(project,'localhost:9099','localhost:9000','')
        validate_emulators('demo-coursesphere-vlab','localhost:9099','localhost:9000','')

    def test_emulator_never_accepts_service_account_path(self):
        with self.assertRaises(RuntimeError):
            validate_emulators('demo-coursesphere-vlab','localhost:9099',
                               'localhost:9000','/tmp/creds.json')

    def test_reject_live_mixed_mode_and_unsafe_urls(self):
        invalid = ('', 'http://myproject.firebaseio.com',
                   'https://evil.example', 'https://firebaseio.com.evil.example',
                   'https://abc.firebaseio.com@evil.example',
                   'https://abc.firebaseio.com/secret',
                   'https://abc.firebaseio.com?dump=1',
                   'https://abc.firebaseio.com#frag',
                   'https://user:pw@abc.firebaseio.com',
                   'https://abc.firebaseio.com:444', 'https://abc.firebaseio.com:80',
                   'https://abc.firebaseio.com ', 'https://abc.firebaseio.com?',
                   'https://@abc.firebaseio.com', 'https://.firebaseio.com',
                   'https://-bad.firebaseio.com',
                   None, 'not-url')
        for url in invalid:
            with self.subTest(url=url),self.assertRaises(RuntimeError):
                validate_live('/tmp/user-owned.json', url,'','')
        for mixed in [('localhost:9099',''), ('','localhost:9000')]:
            with self.assertRaises(RuntimeError):
                validate_live('/tmp/creds.json','https://abc.firebaseio.com',*mixed)
        with self.assertRaises(RuntimeError):
            validate_live('','https://abc.firebaseio.com','','')

    def test_allow_only_known_firebase_rtdb_domains(self):
        for url in ('https://abc.firebaseio.com',
                    'https://abc-default-rtdb.firebaseio.com/',
                    'https://abc-default-rtdb.europe-west1.firebasedatabase.app',
                    'https://abc.firebasedatabase.app:443'):
            with self.subTest(url=url):
                validate_live('/separate/external.json',url,'','')

    def test_existing_default_app_never_crosses_project_or_database(self):
        credential = type('LocalCredential',(),{})
        app=types.SimpleNamespace(options={'projectId':'demo-coursesphere-vlab',
                    'databaseURL':'https://demo-coursesphere-vlab-default-rtdb.firebaseio.com'},
                    credential=credential())
        url=app.options['databaseURL']
        validate_existing_default_app(app,'demo-coursesphere-vlab',url,
                                       emulator=True,emulator_credential_type=credential)
        for project,db in [('demo-wrong',url),('demo-coursesphere-vlab','https://x.firebaseio.com')]:
            with self.subTest(project=project,db=db),self.assertRaises(RuntimeError):
                validate_existing_default_app(app,project,db,emulator=True,
                                              emulator_credential_type=credential)
        with self.assertRaises(RuntimeError):
            validate_existing_default_app(app,'demo-coursesphere-vlab',url,
                                          emulator=True,emulator_credential_type=str)
        with self.assertRaises(RuntimeError):
            validate_existing_default_app(types.SimpleNamespace(),'',url,emulator=False)

    def test_existing_live_app_rejects_database_confusion(self):
        app=types.SimpleNamespace(options={'databaseURL':'https://a.firebaseio.com'})
        validate_existing_default_app(app,'','https://a.firebaseio.com',emulator=False)
        with self.assertRaises(RuntimeError):
            validate_existing_default_app(app,'','https://b.firebaseio.com',emulator=False)

    def test_config_has_no_direct_network_imports(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'backend/firebase_configuration.py').read_text()
        self.assertNotIn('urlopen(',source)
        self.assertNotIn('requests.',source)


if __name__=='__main__': unittest.main()
