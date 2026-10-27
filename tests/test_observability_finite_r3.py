"""Bounded timing samples never poison Prometheus output or HTTP responses."""
import unittest
from backend.observability import HTTPMetrics
class MetricFiniteTests(unittest.TestCase):
    def test_nonfinite_or_malformed_values_do_not_raise(self):
        metrics=HTTPMetrics()
        for value in (float('nan'),float('inf'),float('-inf'),None,'not-number',[],{},-1,10**1000):
            with self.subTest(value=str(value)[:20]):
                metrics.observe('GET','/health',200,value)
        result=metrics.render()
        self.assertNotIn(' nan',result.lower())
        self.assertNotIn(' inf',result.lower())
        self.assertIn('coursesphere_original_http_duration_seconds_count',result)
    def test_normal_latency_sample_preserved(self):
        metrics=HTTPMetrics()
        metrics.observe('GET','/health',200,0.25)
        self.assertIn('0.250000000',metrics.render())
    def test_routes_dont_include_user_paths_as_labels(self):
        metrics=HTTPMetrics()
        metrics.observe('GET','garbage',200,0.001)
        self.assertIn('route="unmatched"',metrics.render())
    def test_nonfinite_doesnt_change_request_count(self):
        metrics=HTTPMetrics()
        metrics.observe('GET','/health',200,float('nan'))
        self.assertIn('coursesphere_original_http_requests_total{route="/health",method="GET",status_class="2xx"} 1',metrics.render())
if __name__=='__main__':unittest.main()
