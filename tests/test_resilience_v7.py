import unittest
from scripts.prove_resilience_local import run_experiment

class ResilienceLocalTest(unittest.TestCase):
    def test_two_replicas_and_survival(self):
        evidence=run_experiment()
        self.assertEqual(evidence['result'],'PASS')
        self.assertTrue(evidence['failure']['confirmed_unreachable'])
        self.assertEqual(evidence['shared_authentication']['status'],200)
