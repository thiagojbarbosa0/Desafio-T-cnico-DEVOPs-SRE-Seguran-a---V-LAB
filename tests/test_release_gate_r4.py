"""Release report must never claim historic Firebase proof is current."""
import unittest
from scripts.release_gate_work_v19_9 import annotate

class ReleaseGateR4Tests(unittest.TestCase):
    def sample(self,passed=()):
        return {'gates':{name:{'passed':name in passed} for name in (
            'original_flask_http_before_after','firebase_auth_database_emulators','docker_observability_failover')},
            'weighted_acceptance_verified_percent':22,'ready_for_submission':True}

    def test_all_stale_firebase_proof_is_marked_historical(self):
        doc=annotate(self.sample())
        self.assertIn('HISTORICAL_ONLY',doc['new_security_boundary']['client_rtdb_write'])
        self.assertFalse(doc['ready_for_submission'])
        self.assertEqual(doc['r4_new_instrumentation']['additional_acceptance_points'],0)
        self.assertEqual(len(doc['current_source_change_notice']['invalidated_gates']),3)

    def test_only_actual_firebase_gate_pass_can_claim_current(self):
        doc=annotate(self.sample(passed=('firebase_auth_database_emulators',)))
        self.assertEqual(doc['new_security_boundary']['client_rtdb_write'],'CURRENT_EMULATOR_PROOF_PRESENT')
        self.assertNotIn('firebase_auth_database_emulators',doc['current_source_change_notice']['invalidated_gates'])
        self.assertFalse(doc['ready_for_submission'])

    def test_r5_scrape_telemetry_never_awards_unrun_docker_points(self):
        doc=annotate(self.sample())
        self.assertFalse(doc['r5_private_readiness_scrape']['runtime_verified_in_this_iteration'])
        self.assertEqual(doc['r5_private_readiness_scrape']['additional_acceptance_points'],0)
        self.assertFalse(doc['ready_for_submission'])

    def test_no_promoted_implementation_percentage(self):
        doc=annotate(self.sample())
        self.assertIn('historical',doc['implementation_readiness_note'])
        self.assertEqual(doc['weighted_acceptance_verified_percent'],22)
        self.assertNotIn('V19.15 passed',str(doc))

if __name__=='__main__':unittest.main()
