"""Pure-Python regression for per-process metrics on the ORIGINAL Flask endpoints."""
import threading
import unittest
from backend.observability import HTTPMetrics, BUCKETS

class OriginalMetricsV13Tests(unittest.TestCase):
    def test_histogram_is_cumulative_and_has_inf(self):
        m = HTTPMetrics()
        m.observe('POST', '/users/query', 200, 0.008)
        m.observe('POST', '/users/query', 500, 0.06)
        s = m.render()
        self.assertIn('coursesphere_original_http_requests_total{route="/users/query",method="POST",status_class="2xx"} 1', s)
        self.assertIn('status_class="5xx"} 1',s)
        self.assertIn('status_class="2xx",le="0.005"} 0',s)
        self.assertIn('status_class="2xx",le="0.01"} 1',s)
        self.assertIn('status_class="2xx",le="+Inf"} 1',s)
        self.assertIn('_count{route="/users/query",method="POST",status_class="2xx"} 1',s)

    def test_never_use_untrusted_raw_url_as_label(self):
        m=HTTPMetrics()
        m.observe('GET', 'https://host/users/secret?token=PRIVATE', 200,0.01)
        self.assertNotIn('PRIVATE',m.render())
        self.assertIn('route="unmatched"',m.render())

    def test_concurrent_observations_are_not_lost(self):
        m=HTTPMetrics()
        def runner():
            for _ in range(500):
                m.observe('GET','/health',200,.02)
        th=[threading.Thread(target=runner) for _ in range(8)]
        for t in th: t.start()
        for t in th: t.join()
        self.assertIn('status_class="2xx"} 4000',m.render())
        self.assertIn('status_class="2xx",le="+Inf"} 4000',m.render())

    def test_escape_label_newline_and_quote(self):
        m=HTTPMetrics()
        m.observe('GET','/strange"\npath',404,.001)
        s=m.render()
        self.assertIn('strange\\"\\npath',s)
        self.assertEqual(tuple(sorted(BUCKETS)), BUCKETS)

if __name__=='__main__': unittest.main()
