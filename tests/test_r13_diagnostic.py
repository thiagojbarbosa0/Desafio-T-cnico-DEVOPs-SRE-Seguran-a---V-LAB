"""R13 one-download Fedora diagnostic contracts; all tests are offline."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diagnostico_total_r13 as diag


class DiagnosticTests(unittest.TestCase):
    def test_step_success_writes_private_log(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'success.log'
            result = diag.run_step('unit', ['python3', '-c', 'print(123)'], file)
            self.assertEqual(result['status'], 'PASS')
            self.assertIn('123', file.read_text())
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)

    def test_step_fail_is_not_silenced(self):
        with tempfile.TemporaryDirectory() as temp:
            result = diag.run_step('failed', ['python3', '-c', 'raise SystemExit(7)'], Path(temp)/'failed.log')
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['exit_code'], 7)

    def test_step_skip_not_claimed_as_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'skip.log'
            result = diag.run_step('skip', ['definitely-missing'], file, skip_reason='not requested')
            self.assertEqual(result['status'], 'SKIP')
            self.assertFalse(file.exists())

    def test_step_missing_executable_is_skip(self):
        with tempfile.TemporaryDirectory() as temp:
            result = diag.run_step('missing', ['missing-executable-r13-unique-name'], Path(temp)/'m.log')
            self.assertEqual(result['status'], 'SKIP')

    def test_step_timeout_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            result = diag.run_step('timeout', ['python3', '-c', 'import time; time.sleep(2)'], Path(temp)/'timeout.log', timeout=0.1)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['reason'], 'Timeout')

    def test_run_disallows_project_root_as_report_dir(self):
        with self.assertRaises(ValueError): diag.run(full=False, out_dir=diag.ROOT)

    def test_counts_preserve_failure_and_skip(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(diag,'run_step') as mock:
            statuses=['PASS','FAIL','SKIP','PASS','PASS','SKIP','PASS','PASS','SKIP','SKIP','SKIP','SKIP']
            mock.side_effect=[{'status':s,'reason':'not installed' if s=='SKIP' else None,
                                'name':str(i),'log':None} for i,s in enumerate(statuses)]
            result=diag.run(full=False,out_dir=Path(temp)/'reports',skip_native_nginx=True)
            self.assertEqual(result['counts'],{'PASS':5,'FAIL':1,'SKIP':6})
            self.assertFalse(result['ready_for_submission'])
            self.assertFalse(result['docker_firebase_acceptance_claim'])
            self.assertTrue((Path(temp)/'reports'/'RESUMO.json').exists())

    def test_full_docker_does_not_start_without_operator_permission(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(diag,'run_step') as mock, \
                patch.object(diag.shutil,'which',return_value=None):
            mock.side_effect=lambda name, cmd, output, **kw: {
                'name':name,'status':'SKIP','reason':kw.get('skip_reason') or 'not installed',
                'duration_seconds':0,'log':None}
            report=diag.run(full=True,out_dir=Path(temp)/'reports',skip_native_nginx=True)
            docker=next(s for s in report['steps'] if s['name']=='docker_official_stack')
            self.assertEqual(docker['status'],'SKIP')
            self.assertIn('Safety hold',docker['reason'])

    def test_report_output_location_is_private(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(diag,'run_step') as mock:
            mock.side_effect=lambda name, cmd, output, **kw: {
                'name':name,'status':'SKIP','reason':kw.get('skip_reason') or 'test',
                'duration_seconds':0,'log':None}
            folder=Path(temp)/'reports'
            report=diag.run(full=False,out_dir=folder,skip_native_nginx=True)
            self.assertEqual(folder.stat().st_mode & 0o777,0o700)
            self.assertEqual((folder/'RESUMO.json').stat().st_mode & 0o777,0o600)

    def test_wrapper_uses_own_directory_not_predefined_home(self):
        text=(diag.ROOT/'EXECUTAR_NO_FEDORA.sh').read_text()
        self.assertIn('BASH_SOURCE[0]',text)
        self.assertIn('exec python3 scripts/diagnostico_total_r13.py',text)


if __name__ == '__main__': unittest.main()
