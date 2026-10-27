import unittest
from pathlib import Path
from backend.observability import HTTPMetrics
from work_checkpoint import eligible

class WorkRegression(unittest.TestCase):
    def test_arbitrary_http_verbs_share_one_metric_series(self):
        metrics = HTTPMetrics()
        for i in range(100):
            metrics.observe('X' + chr(65 + i//26) + chr(65 + i%26), '/health', 405, .01)
        counters = [line for line in metrics.render().splitlines() if line.startswith('coursesphere_original_http_requests_total{')]
        self.assertEqual(len(counters), 1)
        self.assertIn('method="OTHER"', counters[0])
        self.assertTrue(counters[0].endswith(' 100'))

    def test_checkpoint_excludes_local_secret_directory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = root / '.local' / 'metrics_token'
            secret.parent.mkdir(); secret.write_text('synthetic-test-secret')
            source = root / 'app.py'; source.write_text('pass')
            self.assertFalse(eligible(secret, root))
            self.assertTrue(eligible(source, root))
