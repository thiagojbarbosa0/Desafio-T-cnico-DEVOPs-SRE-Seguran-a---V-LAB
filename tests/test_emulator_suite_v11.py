"""Pre-flight checks for the Firebase Emulator test suite without Firebase installed."""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EmulatorSuitePreflight(unittest.TestCase):
    def setUp(self):
        self.source=(ROOT/'integration/test_official_emulators.py').read_text()

    def test_fixtures_and_expected_messages_do_not_conflict(self):
        self.assertIn("'fixture001'",self.source)
        self.assertIn("'integration01'",self.source)
        self.assertIn("self.assertEqual(set(alice), {'fixture001', 'integration01'})",self.source)

    def test_port_binding_avoids_probe_race(self):
        self.assertIn("make_server('127.0.0.1',0,app,threaded=True,",self.source)
        self.assertIn('cls.httpd.server_port',self.source)

    def test_test_suite_rejects_non_demo_projects(self):
        from integration.test_official_emulators import require_emulator_environment, DEMO_PROJECT
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {
                'COURSESPHERE_USE_FIREBASE_EMULATORS': '1',
                'GCLOUD_PROJECT': DEMO_PROJECT,
                'FIREBASE_AUTH_EMULATOR_HOST': '127.0.0.1:9099',
                'FIREBASE_DATABASE_EMULATOR_HOST': '127.0.0.1:9000'}, clear=True):
            require_emulator_environment()
        with patch.dict(os.environ, {'GCLOUD_PROJECT':'production'}, clear=True):
            with self.assertRaises(RuntimeError):require_emulator_environment()

    def test_suite_is_actually_parseable(self):
        ast.parse(self.source)

if __name__=='__main__':unittest.main()
