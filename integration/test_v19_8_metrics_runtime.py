"""Flask WSGI checks using real Flask, fake Firebase (never contacts upstream)."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
from unittest import mock
from integration.test_original_http_stubbed import HAS_FLASK, load_app, SOURCES

SECRET='SYNTHETIC_SECRET_FOR_WSGI_METRICS_'+'A'*48


@unittest.skipUnless(HAS_FLASK,'Flask missing; cannot claim WSGI metrics validation')
class FlaskMetricsAccessWSGI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=load_app(SOURCES['after'],'original_metrics_v19_8')

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token=Path(self.tmp.name)/'token'
        self.token.write_text(SECRET+'\n')
        self.env={'COURSESPHERE_METRICS_ENABLED':'1', 'COURSESPHERE_METRICS_TOKEN_FILE':str(self.token)}
        self.client=self.app.test_client()

    def get(self,remote,header=None, enabled=True,forwarded=None):
        env=self.env if enabled else {'COURSESPHERE_METRICS_ENABLED':'0'}
        h={}
        if header is not None: h['Authorization']=header
        if forwarded is not None: h['X-Forwarded-For']=forwarded
        with mock.patch.dict('os.environ',env,clear=False):
            return self.client.get('/metrics',headers=h,environ_overrides={'REMOTE_ADDR':remote})

    def test_disabled_even_loopback(self):
        self.assertEqual(self.get('127.0.0.1',enabled=False).status_code,404)

    def test_local_operator_enabled(self):
        res=self.get('127.0.0.1')
        self.assertEqual(res.status_code,200)
        self.assertIn('coursesphere_original_http_requests_total',res.get_data(as_text=True))

    def test_remote_without_authorization_denied(self):
        self.assertEqual(self.get('172.20.0.5').status_code,404)

    def test_remote_correct_secret_allowed(self):
        self.assertEqual(self.get('172.20.0.5','Bearer '+SECRET).status_code,200)

    def test_remote_wrong_secret_denied(self):
        self.assertEqual(self.get('172.20.0.5','Bearer '+SECRET[:-1]).status_code,404)

    def test_forwarded_header_cannot_bypass(self):
        self.assertEqual(self.get('172.20.0.5',forwarded='127.0.0.1').status_code,404)

    def test_missing_file_not_authorized(self):
        self.token.unlink()
        self.assertEqual(self.get('172.20.0.5','Bearer '+SECRET).status_code,404)

    def test_private_metrics_no_credentials_in_body(self):
        body=self.get('172.20.0.5','Bearer '+SECRET).get_data(as_text=True)
        self.assertNotIn(SECRET,body)
        self.assertNotIn('SYNTHETIC_TOKEN',body)

if __name__=='__main__': unittest.main()
