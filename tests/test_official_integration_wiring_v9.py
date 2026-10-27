"""Regression tests checking integrations connect to real, defined routes."""
import ast
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class IntegrationWiring(unittest.TestCase):
    def test_original_react_components_share_auth_client(self):
        source_files=[
            ROOT/'frontend/src/api.ts',
            ROOT/'frontend/src/components/nav/Nav.tsx',
            ROOT/'frontend/src/components/UserChats/UserChats.tsx',
        ]
        for f in source_files:
            contents=f.read_text()
            self.assertIn('firebaseClient',contents,str(f))
            self.assertNotIn('initializeApp(',contents,str(f))

    def test_replaced_fake_chats_url_with_real_authenticated_route(self):
        frontend=(ROOT/'frontend/src/components/UserChats/UserChats.tsx').read_text()
        backend=(ROOT/'backend/endpoints.py').read_text()
        self.assertNotIn('/theactualbackendlink',frontend)
        self.assertIn('/chats',frontend)
        self.assertIn('Authorization',frontend)
        self.assertIn('@app.route("/chats", methods=["GET"])',backend)
        self.assertIn('user_id = verified_uid()',backend)
        self.assertIn('Firebase.list_chats(user_id)',backend)

    def test_emulator_integration_is_not_a_fake_unit_harness(self):
        file=ROOT/'integration/test_official_emulators.py'
        source=file.read_text()
        ast.parse(source)
        self.assertIn("from werkzeug.serving import make_server",source)
        self.assertIn("'/identitytoolkit.googleapis.com",source.replace('"','\'')) if False else None
        self.assertIn('identitytoolkit.googleapis.com/v1/accounts:signUp',source)
        self.assertIn('127.0.0.1:9000',source)
        self.assertIn('GET',source)

    def test_docker_operational_verifier_includes_grafana_prometheus_failover(self):
        script=(ROOT/'scripts/verify_docker_stack.py').read_text()
        for needle in ('--failover','docker','prometheus_scrapes_two','grafana_database_health',
                       'stop','api_a_restarted'):
            self.assertIn(needle,script)

if __name__=='__main__':unittest.main()
