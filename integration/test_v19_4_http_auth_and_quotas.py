"""Flask WSGI integration (real Flask routing, fake Firebase service adapters).

No live service connection; Firebase Emulator remains a separate acceptance gate.
Run on Fedora or CI: python3 -m unittest integration.test_v19_4_http_auth_and_quotas -v
"""
from __future__ import annotations
import json
import unittest
from unittest import mock

from integration.test_original_http_stubbed import HAS_FLASK, SyntheticFirebase, SOURCES, load_app


@unittest.skipUnless(HAS_FLASK, 'Flask and Flask-Cors required for true Flask WSGI tests')
class FlaskAuthAndQuotasV194(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the same module identity imported by the real Flask endpoints.
        # backend.shared_quota would define different exception classes.
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
        from shared_quota import QuotaExceeded, QuotaUnavailable
        cls.QuotaExceeded = QuotaExceeded
        cls.QuotaUnavailable = QuotaUnavailable
        cls.app = load_app(SOURCES['after'], 'course_v19_4_auth_integration')

    def setUp(self):
        SyntheticFirebase.reset()
        self.client = self.app.test_client()
        self.header = {'Authorization': 'Bearer SYNTHETIC_TOKEN'}

    def test_verified_session_produces_auth_event_without_uid(self):
        import io, logging
        from unittest import mock
        stream=io.StringIO()
        logger=self.app.logger
        previous_level=logger.level
        handler=logging.StreamHandler(stream)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            res=self.client.get('/users/info',headers=self.header)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)
        self.assertEqual(res.status_code, 200)
        events=[]
        for line in stream.getvalue().splitlines():
            try: events.append(json.loads(line))
            except ValueError: continue
        self.assertTrue(any(e.get('event')=='authentication' and e.get('result')=='accepted' for e in events))
        for event in events:
            self.assertNotIn('SYNTHETIC_TOKEN',json.dumps(event))
            self.assertNotIn('alice',json.dumps(event))

    def test_unauthenticated_requests_logged_and_rejected(self):
        res=self.client.get('/users/info')
        self.assertEqual(res.status_code,401)
        self.assertNotIn('SYNTHETIC_INTERNAL',res.get_data(as_text=True))

    def test_profile_limit_rejects_without_data_change(self):
        with mock.patch.object(SyntheticFirebase,'enforce_quota',side_effect=self.QuotaExceeded('internal')):
            res=self.client.post('/users/info',headers=self.header,json={
                'majors':[], 'minors':[], 'courses':[],
                'year':'2026','college':'Synthetic','about':'Sample',
            })
        self.assertEqual(res.status_code,429)
        self.assertEqual(SyntheticFirebase.profiles,{})

    def test_profile_quota_storage_fault_no_mutation(self):
        with mock.patch.object(SyntheticFirebase,'enforce_quota',side_effect=self.QuotaUnavailable('SECRET_INTERNAL')):
            res=self.client.post('/users/info',headers=self.header,json={
                'majors':[], 'minors':[], 'courses':[],
                'year':'2026','college':'Synthetic','about':'Sample',
            })
        self.assertEqual(res.status_code,503)
        self.assertNotIn('SECRET_INTERNAL',res.get_data(as_text=True))
        self.assertEqual(SyntheticFirebase.profiles,{})

    def test_delete_quota_rejects_without_delete(self):
        SyntheticFirebase.chats[('alice','chat_a')]=[{'content':'safe'}]
        with mock.patch.object(SyntheticFirebase,'enforce_quota',side_effect=self.QuotaExceeded('internal')):
            res=self.client.delete('/chats/chat_a',headers=self.header)
        self.assertEqual(res.status_code,429)
        self.assertIn(('alice','chat_a'),SyntheticFirebase.chats)

    def test_deleted_chat_requires_authorization(self):
        SyntheticFirebase.chats[('alice','chat_a')]=[{'content':'safe'}]
        res=self.client.delete('/chats/chat_a')
        self.assertEqual(res.status_code,401)
        self.assertIn(('alice','chat_a'),SyntheticFirebase.chats)

    def test_auth_metrics_do_not_publish_identity(self):
        with mock.patch.dict('os.environ',{'COURSESPHERE_METRICS_ENABLED':'1'}):
            self.client.get('/users/info',headers=self.header)
            self.client.get('/users/info')
            metrics=self.client.get('/metrics')
        self.assertEqual(metrics.status_code,200)
        text=metrics.get_data(as_text=True)
        self.assertIn('coursesphere_original_auth_attempts_total',text)
        self.assertNotIn('SYNTHETIC_TOKEN',text)
        self.assertNotIn('alice',text)


if __name__=='__main__': unittest.main()
