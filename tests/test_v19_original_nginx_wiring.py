"""Offline source guards for V19 original Flask/Nginx proof.

Only CI/Fedora with Flask installed can claim an actual successful HTTP run.
"""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class OriginalFlaskReplicationWiring(unittest.TestCase):
    def test_harness_is_real_flask_with_synthetic_firebase_only(self):
        p=ROOT/'scripts/flask_replica_stub_worker.py'
        src=p.read_text()
        ast.parse(src)
        self.assertIn('load_app(SOURCES[\'after\']', src)
        self.assertIn("host='127.0.0.1'",src)
        self.assertIn('make_server(host, port, app, threaded=True,',src)

    def test_nginx_proof_checks_original_auth_and_failover(self):
        p=ROOT/'scripts/prove_original_flask_nginx.py'
        src=p.read_text()
        ast.parse(src)
        for requirement in (
            'X-CourseSphere-Test-Instance',
            "'/api/users/info'",
            'SYNTHETIC_TOKEN',
            'survivor_after_flask_a_crash',
            "result['validated']=True",
            "'backend/endpoints.py'",
            "'ops/nginx/gateway.conf'",
            "'integration/test_original_http_stubbed.py'",
        ):
            self.assertIn(requirement,src)

    def test_evidence_never_calls_real_firebase(self):
        src=(ROOT/'scripts/flask_replica_stub_worker.py').read_text()
        self.assertNotIn('FirebaseCredentials',src)
        self.assertNotIn('firebase_admin.initialize_app',src)
        proof=(ROOT/'scripts/prove_original_flask_nginx.py').read_text()
        self.assertIn("'COURSESPHERE_USE_FIREBASE_EMULATORS':'0'",proof)
        self.assertIn("env.pop('FIREBASE_CREDENTIALS_FILE', None)",proof)

    def test_ci_requires_real_flask_and_nginx(self):
        ci=(ROOT/'.github/workflows/ci.yml').read_text()
        self.assertIn('original-flask-nginx-replication',ci)
        self.assertIn('python3 scripts/prove_original_flask_nginx.py',ci)
        self.assertIn('sudo apt-get install -y nginx',ci)
        self.assertIn('Flask-Cors',ci)


if __name__=='__main__':
    unittest.main()
