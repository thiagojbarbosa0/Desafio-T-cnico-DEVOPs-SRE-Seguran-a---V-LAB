"""Regression tests for the ORIGINAL Flask/React Docker profile.

Static contracts are explicitly not a substitute for running Docker. They
prevent accidental fallback to the synthetic backend or exposed host ports.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding='utf-8')


class OriginalDockerContracts(unittest.TestCase):
    def test_original_flask_image_serves_endpoints_with_wsgi(self):
        value = read('backend/Dockerfile.official')
        self.assertIn('endpoints:app',value)
        self.assertIn('gunicorn',value)
        self.assertIn('USER coursesphere',value)
        self.assertNotIn('backend.local_server',value)
        self.assertIn('127.0.0.1:8091/health',value)
        self.assertNotIn('debug=True',value)

    def test_two_original_replicas_and_private_binding(self):
        value = read('compose.official.yaml')
        self.assertIn('official_api_a:',value)
        self.assertIn('official_api_b:',value)
        self.assertIn('backend/Dockerfile.official',value)
        self.assertIn('127.0.0.1:8081:8081',value)
        self.assertIn('service_healthy',value)
        self.assertIn('no-new-privileges:true',value)
        self.assertIn('cap_drop: [ALL]',value)
        self.assertNotIn('backend/Dockerfile\n',value)
        self.assertNotIn('0.0.0.0:8081:8081',value)
        self.assertNotIn('FIREBASE_CREDENTIALS_FILE:',value)
        self.assertNotIn('OPENAI_API_KEY:',value)

    def test_gateway_routing_official_contract(self):
        conf = read('ops/nginx/gateway.official.conf')
        self.assertIn('official_api_a:8091',conf)
        self.assertIn('official_api_b:8091',conf)
        self.assertIn('proxy_pass http://coursesphere_official_api;',conf)
        self.assertIn('location = /metrics { return 403; }',conf)
        self.assertIn('if ($args != "") { return 400; }',conf)
        self.assertIn('location / { proxy_pass http://official_frontend:8082; }',conf)
        self.assertNotIn('api_a:8091 max_fails', conf.replace('official_api_a:8091 max_fails', ''))
        nginx = read('ops/nginx/nginx.conf')
        self.assertIn('"path":"$uri"',nginx)
        self.assertNotIn('$request_uri', '\n'.join(line for line in nginx.splitlines() if not line.strip().startswith('#')))

    def test_frontend_spa_uses_unprivileged_port(self):
        docker = read('frontend/Dockerfile.official')
        self.assertIn('USER nginx', docker)
        self.assertIn('EXPOSE 8082', docker)
        self.assertIn('npm run build',docker)
        self.assertIn('VITE_USE_FIREBASE_EMULATORS',docker)
        self.assertIn('try_files $uri $uri/ /index.html;',read('ops/nginx/frontend.official.conf'))

    def test_never_embed_secrets_in_docker_context(self):
        ignore = read('.dockerignore')
        for excluded in ('.env', '**/reddit_key.json', '**/service-account*.json',
                         '**/*.pem', '**/node_modules', '.git'):
            self.assertIn(excluded,ignore)

    def test_smoke_proof_is_explicit_about_synthetic_upstreams(self):
        source = read('scripts/prove_official_nginx_contract_v19_7.py')
        module = ast.parse(source)
        self.assertTrue(module)
        self.assertIn('Upstream Flask and React mocked',source)
        self.assertIn('no_token_query_in_edge_logs',source)
        self.assertIn('survivor_after_backend_stop',source)

    def test_docker_runtime_proof_rejects_missing_replica(self):
        code = read('scripts/verify_official_docker_v19_7.py')
        self.assertIn('len(distribution) < 2',code)
        self.assertIn("'validated': False",code)
        self.assertIn('stopped_replica_restored',code)
        self.assertIn('source_sha256',code)
        self.assertIn('if result[\'validated\'] else 1',code)

    def test_original_app_is_not_rebranded_as_crud_demo(self):
        official = read('compose.official.yaml')
        self.assertIn('ORIGINAL Flask+React', official)
        self.assertNotIn('APP_MODE: demo',official)
        self.assertTrue((ROOT/'compose.yaml').exists())


if __name__ == '__main__':
    unittest.main()
