"""V11 guards against overclaiming security verification and accidental regressions."""
import json
import tempfile
import unittest
from pathlib import Path
from backend.security_core import SecurityError, validate_messages
import integration.test_original_http_stubbed as http_tests
SOURCES = http_tests.SOURCES
from scripts.release_gate_v11 import ROOT, evaluate

class EvidenceTruthfulness(unittest.TestCase):
    def test_baseline_is_archived_separately(self):
        self.assertTrue(SOURCES['before'].exists())
        self.assertTrue(SOURCES['after'].exists())
        self.assertNotEqual(SOURCES['before'].read_bytes(),SOURCES['after'].read_bytes())

    def test_no_http_evidence_is_not_a_pass(self):
        # The gate must not claim HTTP success merely because test files exist.
        result=evaluate()
        artifact=ROOT/'evidence/generated/ORIGINAL_FLASK_HTTP_BEFORE_AFTER_V12.json'
        if not artifact.exists():
            self.assertFalse(result['gates']['original_flask_http_with_stubbed_firebase']['passed'])

    def test_synthetic_http_never_counts_as_completed_upstream_pentest(self):
        gates=evaluate()['gates']
        self.assertFalse(gates['five_upstream_findings_two_categories_three_root_cause_fixes']['passed'])

    def test_human_clearance_not_automatically_approved(self):
        self.assertFalse(evaluate()['gates']['upstream_redistribution_rights_and_secret_rotation']['passed'])

    def test_http_cases_are_named_and_unique(self):
        methods=[name for name in dir(http_tests.OriginalHTTPBeforeAfter) if name.startswith('test_')]
        self.assertEqual(len(methods),15)
        self.assertEqual(len(set(methods)),len(methods))

    def test_original_cors_and_debug_are_never_reintroduced(self):
        old=SOURCES['before'].read_text()
        new=SOURCES['after'].read_text()
        self.assertIn('CORS(app)',old)
        self.assertIn('app.run(debug=True)',old)
        self.assertNotIn('CORS(app)\n',new)
        self.assertNotIn('app.run(debug=True)',new)

    def test_ci_runs_real_http_not_only_ast_harness(self):
        workflow=(ROOT/'.github/workflows/ci.yml').read_text()
        self.assertIn('python3 -m integration.run_original_http_stubbed',workflow)
        self.assertIn('Flask-Cors',workflow)

    def test_non_mock_flask_runs_never_marked_from_skip(self):
        code=(ROOT/'integration/run_original_http_stubbed.py').read_text()
        self.assertIn('not result.skipped',code)
        self.assertIn('result.testsRun == 15',code)

    def test_original_cors_test_uses_nonexistent_synthetic_origin(self):
        code=(ROOT/'integration/test_original_http_stubbed.py').read_text()
        self.assertIn('https://malicious.example.invalid',code)
        self.assertNotIn('http://localhost:5000',code)

    def test_sensitive_credential_file_not_reintroduced(self):
        self.assertFalse((ROOT/'backend/cornell-course-sphere-data/reddit-data/reddit_key.json').exists())

class FrontendContractV11(unittest.TestCase):
    def setUp(self): self.client=(ROOT/'frontend/src/api.ts').read_text()
    def test_sign_in_uses_typed_string_inputs_without_jquery(self):
        # Login/signup forms provide strings without the jQuery typing dependency.
        self.assertIn('const inputValue = (id: string): string',self.client)
        self.assertIn("inputValue('login-email-input')",self.client)
        self.assertIn("inputValue('login-password-input')",self.client)
        self.assertIn("inputValue('signup-email-input')",self.client)
        self.assertIn("inputValue('signup-password-input')",self.client)
        self.assertNotIn("from 'jquery'",self.client)
    def test_authenticated_query_never_sends_bearer_undefined(self):
        snippet=self.client.split('async function fetchCourseSphereResponse',1)[1].split('function ensureUserLoggedIn',1)[0]
        self.assertIn('if (!user || user.uid !== expectedUid)',snippet)
        self.assertIn('if (!sameUser(user.uid))',snippet)
        self.assertIn('await user.getIdToken()',snippet)
        self.assertNotIn('user?.getIdToken()',snippet)
    def test_profile_fields_are_typed_and_sent_from_react_state(self):
        self.assertRegex(self.client, r'year: string,\s*college: string,\s*about: string')
        self.assertIn('body: JSON.stringify({ majors, minors, year, college, courses, about })',self.client)
        dashboard=(ROOT/'frontend/src/pages/dashboard/Dashboard.tsx').read_text()
        self.assertIn('value={props.about}',dashboard)
        self.assertIn('onChange={(event) => props.setAbout(event.target.value)}',dashboard)

if __name__=='__main__':unittest.main()
