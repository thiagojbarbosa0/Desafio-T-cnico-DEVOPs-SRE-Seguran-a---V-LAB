import ast
import json
import unittest
from pathlib import Path
from tests.origin_harness import ROOT, ORIGINAL, PATCHED, execute_handler


class OriginalCodeRegression(unittest.TestCase):
    """Original-vs-patched FUNCTION execution on synthetic data; no Flask/network."""

    def test_original_unprotected_admin_signup_now_gone(self):
        payload={'email':'synthetic@example.invalid','password':'SIMULATED_NOT_REAL'}
        old, old_calls=execute_handler(ORIGINAL,'create_user',payload=payload)
        new, new_calls=execute_handler(PATCHED,'create_user',payload=payload)
        self.assertEqual(old[1],200)
        self.assertIn('create_user',[x[0] for x in old_calls])
        self.assertEqual(new[1],410)
        self.assertEqual(new_calls,[])

    def test_original_token_in_query_now_header_only(self):
        old,_=execute_handler(ORIGINAL,'get_user_info',query_token='SYNTHETIC_TOKEN')
        new_no_header,_=execute_handler(PATCHED,'get_user_info',query_token='SYNTHETIC_TOKEN')
        new_with_header,_=execute_handler(PATCHED,'get_user_info',token='SYNTHETIC_TOKEN')
        self.assertEqual(old[1],200)
        self.assertEqual(new_no_header[1],401)
        self.assertEqual(new_with_header[1],200)

    def test_original_exception_details_leak_now_generic(self):
        old,_=execute_handler(ORIGINAL,'get_user_info',query_token='SYNTHETIC_TOKEN',
                              firebase_profile_error='SYNTHETIC_INTERNAL_TRACE_MARKER')
        new,_=execute_handler(PATCHED,'get_user_info',token='SYNTHETIC_TOKEN',
                              firebase_profile_error='SYNTHETIC_INTERNAL_TRACE_MARKER')
        self.assertIn('SYNTHETIC_INTERNAL_TRACE_MARKER',str(old[0]))
        self.assertNotIn('SYNTHETIC_INTERNAL_TRACE_MARKER',str(new[0]))
        self.assertEqual(new[1],500)

    def test_original_anonymous_query_now_rejected(self):
        payload={'query':'Safe synthetic search'}
        old,_=execute_handler(ORIGINAL,'get_user_query',payload=payload)
        new,_=execute_handler(PATCHED,'get_user_query',payload=payload)
        self.assertEqual(old[1],200)
        self.assertEqual(new[1],401)

    def test_original_oversized_chat_now_rejected(self):
        payload={'messages':[{'sender':'alice','content':'safe','messageID':'abc'}]*101}
        old, old_calls=execute_handler(ORIGINAL,'save_chat',payload=payload,token='SYNTHETIC_TOKEN')
        new, new_calls=execute_handler(PATCHED,'save_chat',payload=payload,token='SYNTHETIC_TOKEN')
        self.assertEqual(old[1],200)
        self.assertTrue(any(x[0]=='save_chat' for x in old_calls))
        self.assertEqual(new[1],400)
        self.assertFalse(any(x[0]=='save_chat' for x in new_calls))

    def test_original_profile_unbounded_now_rejected(self):
        payload={'about':'A'*2000}
        old,_=execute_handler(ORIGINAL,'set_user_info',payload={**payload,'id_token':'SYNTHETIC_TOKEN'})
        new,_=execute_handler(PATCHED,'set_user_info',payload=payload,token='SYNTHETIC_TOKEN')
        self.assertEqual(old[1],200)
        self.assertEqual(new[1],400)

    def test_original_security_configuration_audited(self):
        old=ORIGINAL.read_text()
        new=PATCHED.read_text()
        self.assertIn('CORS(app)',old)
        self.assertIn('CORS(app, origins=allowed_origins',new)
        self.assertIn('app.run(debug=True)',old)
        self.assertRegex(new, r'app\.run\(debug=False(?:,|\))')

    def test_sensitive_credential_removed_from_derivative(self):
        meta=json.loads((ROOT/'audit/baseline/credential_exposure_metadata.json').read_text())
        self.assertIn('client_secret',meta['fields_with_values'])
        self.assertFalse((ROOT/'backend/cornell-course-sphere-data/reddit-data/reddit_key.json').exists())
        self.assertIn('**/reddit_key.json',(ROOT/'.gitignore').read_text())

    def test_sql_injection_module_not_active(self):
        source=(ROOT/'audit/baseline/courses_original.txt').read_text()
        self.assertIn('f"SELECT * FROM courses WHERE semester =',source)
        self.assertNotIn('app.register_blueprint(courses_bp)',ORIGINAL.read_text().replace('#app.register_blueprint(courses_bp)',''))
        self.assertIn('WHERE semester = ?', (ROOT/'backend/blueprints/courses.py').read_text())

if __name__=='__main__': unittest.main()
