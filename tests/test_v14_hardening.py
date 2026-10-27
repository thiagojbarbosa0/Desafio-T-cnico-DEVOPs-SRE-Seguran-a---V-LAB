"""V14 regressions: actual input validation and honest operational exit statuses.

These unit tests do NOT substitute for running Flask, Docker or Firebase.
"""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend.security_core import SecurityError, validate_messages

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_docker_stack as verifier


class MessageIntegrity(unittest.TestCase):
    @staticmethod
    def msg(mid="id1", sender="user"):
        return {"sender": sender, "messageID": mid, "content": "safe synthetic text", "timestamp": "2026-10-23T10:00:00Z"}

    def test_valid_pair(self):
        messages = validate_messages({"messages": [self.msg("id1"), self.msg("id2", "bot")]})
        self.assertEqual([m["messageID"] for m in messages], ["id1", "id2"])

    def test_reject_duplicate_ids_before_firebase_write(self):
        with self.assertRaisesRegex(SecurityError, "Duplicate messageID"):
            validate_messages({"messages": [self.msg("id1"), self.msg("id1", "bot")]})

    def test_reject_unknown_sender(self):
        with self.assertRaisesRegex(SecurityError, "Unknown message sender"):
            validate_messages({"messages": [self.msg(sender="admin")]})

    def test_legacy_human_sender_remains_supported(self):
        self.assertEqual(validate_messages({"messages": [self.msg(sender="human")]})[0]["sender"], "human")

    def test_reject_malformed_ids(self):
        with self.assertRaises(SecurityError):
            validate_messages({"messages": [self.msg(mid="../cross-user")]})


class DockerVerifierReleaseSafety(unittest.TestCase):
    """Fake HTTP/compose dependencies; test verifier logic, not the Docker runtime."""
    def run_case(self, restart_fails=False, provisioned=True, unhealthy_after_restart=False):
        state = {"stopped": False, "turn": 0, "restarted": False}
        calls = []

        def fake_compose(*args):
            calls.append(args)
            if args[:2] == ("stop", "api_a"):
                state["stopped"] = True
            if args[:2] == ("start", "api_a"):
                if restart_fails:
                    raise RuntimeError("synthetic restart failure")
                state["stopped"] = False
                state["restarted"] = True

        def fake_get(url, headers=None):
            if "/api/ready" in url:
                if state["stopped"] or (state["restarted"] and unhealthy_after_restart):
                    return 200, {"X-CourseSphere-Instance": "api-b"}, {"status": "ok", "instance": "api-b"}
                state["turn"] += 1
                host = "api-a" if state["turn"] % 2 else "api-b"
                return 200, {"X-CourseSphere-Instance": host}, {"status": "ok", "instance": host}
            if url.endswith("/lab/"):
                return 200, {}, {}
            if url.endswith("/metrics"):
                return 403, {}, {}
            if "9090/api/v1/query" in url:
                return 200, {}, {"status": "success", "data": {"result": [{"value": [0, "1"]}, {"value": [0, "1"]}]}}
            if "3000/api/health" in url:
                return 200, {}, {"database": "ok"}
            if "3000/api/search" in url:
                return 200, {}, ([{"title": "CourseSphere Local"}] if provisioned else [])
            raise AssertionError(url)

        def fake_wait(fn, **kwargs):
            for _ in range(5):
                value = fn()
                if value:
                    return value
            raise RuntimeError('service missing')

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "docker.json"
            with mock.patch.object(verifier, "EVIDENCE", target), \
                 mock.patch.object(verifier, "compose", side_effect=fake_compose), \
                 mock.patch.object(verifier, "get", side_effect=fake_get), \
                 mock.patch.object(verifier, "wait", side_effect=fake_wait), \
                 mock.patch.object(verifier, "creds", return_value={"Authorization": "Basic SYNTHETIC"}), \
                 mock.patch.object(verifier, "docker_fingerprint", return_value="synthetic"), \
                 mock.patch.object(sys, "argv", ["verify_docker_stack.py", "--failover"]):
                result = verifier.main()
            evidence = json.loads(target.read_text())
        return result, evidence, calls

    def test_full_proof_exits_zero_only_when_recovered(self):
        status, evidence, calls = self.run_case()
        self.assertEqual(status, 0)
        self.assertTrue(evidence["validated"])
        self.assertEqual(evidence["tests"]["api_a_restarted"], "pass")
        self.assertIn(("start", "api_a"), calls)

    def test_failed_restart_must_exit_nonzero(self):
        status, evidence, _ = self.run_case(restart_fails=True)
        self.assertEqual(status, 1)
        self.assertFalse(evidence["validated"])
        self.assertEqual(evidence["tests"]["api_a_restarted"], "FAILED_RESTART_MANUALLY")

    def test_restart_success_without_http_readiness_must_fail(self):
        status, evidence, _ = self.run_case(unhealthy_after_restart=True)
        self.assertEqual(status, 1)
        self.assertFalse(evidence["validated"])
        self.assertEqual(evidence["tests"]["api_a_restarted"], "FAILED_RESTART_MANUALLY")

    def test_missing_grafana_dashboard_must_fail(self):
        status, evidence, calls = self.run_case(provisioned=False)
        self.assertEqual(status, 1)
        self.assertFalse(evidence["validated"])
        self.assertNotIn(("stop", "api_a"), calls)


if __name__ == "__main__":
    unittest.main()
