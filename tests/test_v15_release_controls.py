"""V15 release and execution control contract (offline, not integrated proof)."""
from pathlib import Path
import unittest

R = Path(__file__).resolve().parents[1]

class ReleaseControlsV15(unittest.TestCase):
    def test_fedora_script_reuses_existing_virtual_environment(self):
        script = (R/'scripts/fedora_validation_v15.sh').read_text()
        self.assertIn('set -euo pipefail', script)
        self.assertIn('if [ -x .venv/bin/python ]; then', script)
        self.assertIn('bash scripts/fedora_validation_v13.sh "$@"',script)

    def test_offline_verification_does_not_claim_integrated_services(self):
        script = (R/'scripts/verify_v15.sh').read_text()
        self.assertIn('bash scripts/verify_v13.sh', script)
        self.assertNotIn('docker compose up', script)
        self.assertNotIn('firebase emulators:exec', script)

    def test_gate_never_imports_user_report_as_passed_ci_evidence(self):
        gate = (R/'scripts/release_gate_v15.py').read_text()
        self.assertIn('does not import that report', gate)
        self.assertIn('evaluate_v14()', gate)
        self.assertIn('ready_for_submission', gate)

    def test_principal_docs_explain_original_app_scope(self):
        doc = (R/'docs/HANDOFF_V15.md').read_text()
        self.assertIn('CourseSphere original',doc)
        self.assertIn('Firebase',doc)
        self.assertIn('Flask',doc)
        self.assertIn('laboratório',doc)

if __name__ == '__main__':
    unittest.main()
