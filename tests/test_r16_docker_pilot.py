"""SDK-free R16 fail-closed deployment controls."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from backend.firebase_configuration import validate_emulators
from scripts import deploy_r16_docker_pilot as pilot

class R16DockerPilotTests(unittest.TestCase):
    def test_default_mode_rejects_remote_emulator_host(self):
        with patch.dict('os.environ',{'COURSESPHERE_DOCKER_EMULATOR_MODE':'0'}):
            with self.assertRaises(RuntimeError):validate_emulators('demo-coursesphere-vlab','official_firebase_emulators:9099','official_firebase_emulators:9000','')

    def test_docker_opt_in_allows_only_named_demo_services(self):
        with patch.dict('os.environ',{'COURSESPHERE_DOCKER_EMULATOR_MODE':'1'}):
            validate_emulators('demo-coursesphere-vlab','official_firebase_emulators:9099','official_firebase_emulators:9000','')
            for auth,db in [('evil:9099','official_firebase_emulators:9000'),('official_firebase_emulators:9099','evil:9000'),('127.0.0.1:9099','127.0.0.1:9000'),('official_firebase_emulators:9099/x','official_firebase_emulators:9000')]:
                with self.subTest(auth=auth,db=db),self.assertRaises(RuntimeError):validate_emulators('demo-coursesphere-vlab',auth,db,'')

    def test_docker_mode_must_be_strict_and_demo_only(self):
        for mode in ('true','yes','', '2'):
            with patch.dict('os.environ',{'COURSESPHERE_DOCKER_EMULATOR_MODE':mode}):
                with self.assertRaises(RuntimeError):validate_emulators('demo-coursesphere-vlab','official_firebase_emulators:9099','official_firebase_emulators:9000','')
        with patch.dict('os.environ',{'COURSESPHERE_DOCKER_EMULATOR_MODE':'1'}):
            with self.assertRaises(RuntimeError):validate_emulators('production','official_firebase_emulators:9099','official_firebase_emulators:9000','')
            with self.assertRaises(RuntimeError):validate_emulators('demo-coursesphere-vlab','official_firebase_emulators:9099','official_firebase_emulators:9000','/tmp/key.json')

    def test_check_emulator_refuses_unowned(self):
        record={'Config':{'Labels':{'com.docker.compose.project':'untrusted','com.docker.compose.service':'official_firebase_emulators'}},'State':{'Running':True,'Health':{'Status':'healthy'}}}
        with patch.object(pilot,'docker',return_value=json.dumps([record])):
            with self.assertRaises(pilot.GateError):pilot.check_emulator()

    def test_check_emulator_refuses_unhealthy(self):
        record={'Config':{'Labels':{'com.docker.compose.project':'coursesphere-official-local','com.docker.compose.service':'official_firebase_emulators'}},'State':{'Running':True,'Health':{'Status':'unhealthy'}}}
        with patch.object(pilot,'docker',return_value=json.dumps([record])):
            with self.assertRaises(pilot.GateError):pilot.check_emulator()

    def test_check_emulator_requires_docker_dns_alias(self):
        record={'Config':{'Labels':{'com.docker.compose.project':'coursesphere-official-local','com.docker.compose.service':'official_firebase_emulators'}},'State':{'Running':True,'Health':{'Status':'healthy'}},'NetworkSettings':{'Networks':{'network':{'Aliases':['wrong']}}}}
        with patch.object(pilot,'docker',return_value=json.dumps([record])):
            with self.assertRaises(pilot.GateError):pilot.check_emulator()

    def test_preflight_refuses_existing_pilot(self):
        with patch.object(pilot,'docker',return_value='existing-container-id'):
            with self.assertRaises(pilot.GateError):pilot.preflight_ports()

    def test_secrets_are_mode_600_without_values_in_reports(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(pilot,'ROOT',Path(tmp)):
            pilot.prepare_secrets('coursesphere-official-local_network')
            for item in (Path(tmp)/'.env.r16.local',Path(tmp)/'.local/official_metrics_token'):
                self.assertEqual(item.stat().st_mode & 0o777,0o600)
            self.assertIn('R16_FIREBASE_NETWORK=coursesphere-official-local_network',(Path(tmp)/'.env.r16.local').read_text())

    def test_docker_network_name_injection_refused(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(pilot,'ROOT',Path(tmp)):
            for bad in ('network\nOFFICIAL_GRAFANA_ADMIN_PASSWORD=evil','/tmp/path',' spaced ', ''):
                with self.subTest(bad=bad),self.assertRaises(pilot.GateError):pilot.prepare_secrets(bad)

    def test_symlink_secrets_refused(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(pilot,'ROOT',Path(tmp)):
            (Path(tmp)/'.local').symlink_to(Path(tmp)/'not-there')
            with self.assertRaises(pilot.GateError):pilot.prepare_secrets('network')

    def test_compose_project_is_unique_and_no_emulator_changes(self):
        text=(pilot.ROOT/pilot.COMPOSE).read_text()
        self.assertIn('name: coursesphere-r16-pilot',text)
        self.assertIn('firebase_existing:',text)
        self.assertIn('external: true',text)
        self.assertNotIn('docker-proxy',text)
        self.assertNotIn('docker.sock',text)
        self.assertNotIn('9000:9000',text)
        self.assertNotIn('9099:9099',text)
        self.assertIn('127.0.0.1:18081:8081',text)

if __name__=='__main__':unittest.main()
