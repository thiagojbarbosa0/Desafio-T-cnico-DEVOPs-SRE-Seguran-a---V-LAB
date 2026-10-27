"""Keep static upstream leak proof separate from live vulnerability acceptance."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import release_gate_v19_5 as gate

class F04ReleaseGateTests(unittest.TestCase):
    def proof(self):
        return {
            'finding_id':'F04',
            'finding':'Credential-shaped material included in original upstream source archive',
            'source_snapshot_sha256':'a'*64,
            'source_snapshot_size_bytes':200,
            'checked_at_utc':'2026-10-23T22:00:00+00:00',
            'file_evidence':{
                'relative_path':'backend/cornell-course-sphere-data/reddit-data/reddit_key.json',
                'fields_present':['client_id','client_secret'],
                'credential_like_non_placeholder':True,
                'credential_currently_valid':'NOT_TESTED',
                'external_service_contacted':False,
            },
            'scope':'Static only',
            'recommended_owner_action':'Rotate or revoke if valid',
        }

    def test_strict_sanitized_artifact_passes(self):
        self.assertTrue(gate.validate_f04(self.proof()))

    def test_claiming_valid_secret_rejected(self):
        x=self.proof(); x['file_evidence']['credential_currently_valid']='ACTIVE'
        self.assertFalse(gate.validate_f04(x))

    def test_secret_extra_field_rejected(self):
        x=self.proof();x['file_evidence']['client_secret']='SYNTHETIC_TEST_SECRET'
        self.assertFalse(gate.validate_f04(x))

    def test_no_external_contact_claim_rejected(self):
        x=self.proof();x['file_evidence']['external_service_contacted']=True
        self.assertFalse(gate.validate_f04(x))

    def test_bad_sha256_rejected(self):
        x=self.proof();x['source_snapshot_sha256']='unknown'
        self.assertFalse(gate.validate_f04(x))

    def test_no_extra_weighted_points(self):
        baseline={'weighted_acceptance_verified_percent':15, 'gates_passed':2, 'version':'V19.4'}
        with tempfile.TemporaryDirectory() as directory:
            temp=Path(directory)/'proof.json'; temp.write_text(json.dumps(self.proof()))
            with patch.object(gate,'previous',return_value=baseline),patch.object(gate,'EVIDENCE',temp):
                outcome=gate.evaluate()
        self.assertEqual(outcome['weighted_acceptance_verified_percent'],15)
        self.assertFalse(outcome['supplemental_upstream_credential_exposure_F04']['counts_in_weighted_acceptance'])
        self.assertFalse(outcome['ready_for_submission'])

if __name__=='__main__':unittest.main()
