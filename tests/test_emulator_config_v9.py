"""Static protections; not a substitute for live Firebase Emulator integration."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class FirebaseEmulatorSafetyTests(unittest.TestCase):
    def test_demo_project_and_loopback_ports(self):
        config=json.loads((ROOT/'firebase.json').read_text())
        self.assertEqual(config['emulators']['auth']['host'],'127.0.0.1')
        self.assertEqual(config['emulators']['database']['host'],'127.0.0.1')
        self.assertEqual(config['emulators']['auth']['port'],9099)
        self.assertEqual(config['emulators']['database']['port'],9000)

    def test_firebase_rtdb_rules_limit_access_to_own_uid(self):
        rules=json.loads((ROOT/'ops/firebase/database.rules.json').read_text())['rules']
        self.assertIs(rules['.read'],False)
        self.assertIs(rules['.write'],False)
        self.assertEqual(rules['users']['$uid']['.read'],'auth != null && auth.uid === $uid')
        self.assertIs(rules['users']['$uid']['.write'], False)  # All writes go through validated Flask endpoints

    def test_rtdb_namespace_is_consistent_across_admin_web_and_integration(self):
        backend=(ROOT/'backend/firebase.py').read_text()
        frontend=(ROOT/'frontend/src/firebaseConfig.ts').read_text()
        tests=(ROOT/'integration/test_official_emulators.py').read_text()
        self.assertIn('project_id}-default-rtdb.firebaseio.com', backend)
        self.assertIn('"-default-rtdb"', frontend)
        self.assertIn("DEMO_PROJECT+'-default-rtdb'", tests)

    def test_firebase_frontend_does_not_use_original_project(self):
        cfg=(ROOT/'frontend/src/firebaseConfig.ts').read_text()
        self.assertIn('demo-coursesphere-vlab',cfg)
        self.assertNotIn('coursesphere-8bd9a',cfg)
        self.assertIn('VITE_USE_FIREBASE_EMULATORS',cfg)
        client=(ROOT/'frontend/src/firebaseClient.ts').read_text()
        self.assertIn('connectAuthEmulator',client)
        self.assertIn('connectDatabaseEmulator',client)
        self.assertIn('127.0.0.1',client)

    def test_flask_auth_emulator_never_loads_service_account(self):
        source=(ROOT/'backend/firebase.py').read_text()
        self.assertIn('COURSESPHERE_USE_FIREBASE_EMULATORS',source)
        self.assertIn('EmulatorOwnerCredentials',source)
        self.assertIn('validate_emulators(project_id, auth_host, db_host,',source)
        from backend.firebase_configuration import validate_emulators
        with self.assertRaises(RuntimeError):
            validate_emulators('demo-coursesphere-vlab', 'localhost:9099',
                               'localhost:9000', '/tmp/real-service-account.json')
        with self.assertRaises(RuntimeError):
            validate_emulators('real-course', 'localhost:9099', 'localhost:9000', '')

    def test_official_integration_is_explicit_not_fake(self):
        source=(ROOT/'integration/test_official_emulators.py').read_text()
        self.assertIn('from werkzeug.serving import make_server',source)
        self.assertIn('firebase',source)
        self.assertIn('signup(',source)
        self.assertIn('auth',source)
        self.assertIn('database_anonymous_access_denied',source)

if __name__=='__main__': unittest.main()
