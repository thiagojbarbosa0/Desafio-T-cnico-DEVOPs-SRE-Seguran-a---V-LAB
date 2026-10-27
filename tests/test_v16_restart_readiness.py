import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class RealRecoveryContract(unittest.TestCase):
    def test_docker_recovery_verifies_health_not_just_start_command(self):
        source=(ROOT/'scripts/verify_docker_stack.py').read_text()
        fragment=source.split("compose('start','api_a')",1)[1].split("result['tests']['api_a_restarted']='pass'",1)[0]
        self.assertIn("response[2].get('instance') == 'api-a'", fragment)
        self.assertIn('wait(lambda:',fragment)
        self.assertIn('get(',fragment)

    def test_firebase_runner_prefers_local_venv(self):
        source=(ROOT/'scripts/verify_official_emulators.sh').read_text()
        self.assertIn('if [ -x .venv/bin/python ]; then',source)
        self.assertIn('demo-coursesphere-vlab',source)

if __name__=='__main__':unittest.main()
