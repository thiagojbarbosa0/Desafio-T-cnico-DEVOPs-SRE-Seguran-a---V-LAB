"""Offline contract tests: shared quotas, transaction failures and provenance."""
import importlib.util
import pathlib
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shared_quota import LIMITS, QuotaUnavailable, debit


class TransactionalDB:
    def __init__(self):
        self.records = {}
        self.paths = []
        self.lock = threading.Lock()
        self.broken = False

    def reference(self, path):
        self.paths.append(path)
        database = self

        class Reference:
            def transaction(self, update):
                if database.broken:
                    raise ConnectionError('synthetic unreachable Firebase')
                with database.lock:
                    state = database.records.get(path)
                    final = update(state)
                    database.records[path] = final
                    return final

        return Reference()


class TestDistributedQuota(unittest.TestCase):
    def setUp(self):
        self.db = TransactionalDB()

    def test_permits_first_call(self):
        self.assertTrue(debit(self.db.reference, 'alice', 'recommendation', now=60))

    def test_exact_limit_and_rejection(self):
        limit, _ = LIMITS['recommendation']
        for _ in range(limit):
            self.assertTrue(debit(self.db.reference, 'alice', 'recommendation', now=120))
        for _ in range(3):
            self.assertFalse(debit(self.db.reference, 'alice', 'recommendation', now=120))
        path = self.db.paths[-1]
        self.assertEqual(self.db.records[path]['count'], limit)

    def test_new_window_resets_bounded_single_record(self):
        self.assertTrue(debit(self.db.reference, 'alice', 'recommendation', now=119))
        self.assertTrue(debit(self.db.reference, 'alice', 'recommendation', now=120))
        self.assertEqual(len(self.db.records), 1)
        self.assertEqual(list(self.db.records.values())[0], {'window': 2, 'count': 1})

    def test_separate_users_and_actions(self):
        for uid, action in [('alice', 'recommendation'), ('bob', 'recommendation'), ('alice', 'message_id')]:
            self.assertTrue(debit(self.db.reference, uid, action, now=120))
        self.assertEqual(len(self.db.records), 3)

    def test_hash_avoids_raw_uid_in_path(self):
        debit(self.db.reference, 'real-uid.example', 'message_id', now=120)
        self.assertTrue(self.db.paths[-1].startswith('server_security/rate_limits/'))
        self.assertNotIn('real-uid.example', self.db.paths[-1])

    def test_unknown_actions_and_ids_rejected_before_database(self):
        for uid, action in [('alice', 'arbitrary'), ('', 'recommendation'), ('X' * 513, 'message_id')]:
            with self.assertRaises(ValueError):
                debit(self.db.reference, uid, action, now=120)
        self.assertEqual(self.db.paths, [])

    def test_corrupted_counter_does_not_reset_quota(self):
        debit(self.db.reference, 'alice', 'recommendation', now=120)
        path = self.db.paths[-1]
        self.db.records[path] = {'window': 2, 'count': 'bad value'}
        self.assertFalse(debit(self.db.reference, 'alice', 'recommendation', now=120))

    def test_clock_skew_never_rolls_window_back(self):
        # Replica A has advanced to window 3; a slower B must not reopen 2.
        for _ in range(20):
            self.assertTrue(debit(self.db.reference, 'alice', 'profile_write', now=180))
        self.assertFalse(debit(self.db.reference, 'alice', 'profile_write', now=179))
        self.assertFalse(debit(self.db.reference, 'alice', 'profile_write', now=180))
        record = next(iter(self.db.records.values()))
        self.assertEqual(record, {'window':3,'count':20})
    def test_corrupted_window_never_reopens_counter(self):
        debit(self.db.reference, 'alice', 'profile_write', now=180)
        path=self.db.paths[-1]
        for bad in ('3', True, -1, None, 1.5):
            self.db.records[path] = {'window':bad,'count':1}
            with self.subTest(bad=bad):
                self.assertFalse(debit(self.db.reference, 'alice', 'profile_write', now=180))
                self.assertEqual(self.db.records[path]['window'],bad)
    def test_invalid_counter_type_denied(self):
        debit(self.db.reference, 'alice', 'profile_write', now=180)
        path=self.db.paths[-1]
        self.db.records[path]={'window':3,'count':True}
        self.assertFalse(debit(self.db.reference,'alice','profile_write',now=180))
    def test_invalid_quota_clock(self):
        with self.assertRaises(ValueError):
            debit(self.db.reference,'alice','profile_write',now=-2)
    def test_storage_error_fails_closed(self):
        self.db.broken = True
        with self.assertRaises(QuotaUnavailable) as ctx:
            debit(self.db.reference, 'alice', 'recommendation', now=120)
        self.assertNotIn('synthetic unreachable Firebase', str(ctx.exception))

    def test_parallel_requests_share_one_counter(self):
        limit, _ = LIMITS['recommendation']
        with ThreadPoolExecutor(max_workers=12) as pool:
            result = list(pool.map(lambda _: debit(self.db.reference, 'alice', 'recommendation', now=120), range(80)))
        self.assertEqual(sum(result), limit)
        self.assertEqual(len(self.db.records), 1)

    def test_default_clock_is_second_based(self):
        with mock.patch('shared_quota.time.time', return_value=180.5):
            self.assertTrue(debit(self.db.reference, 'alice', 'recommendation'))
        self.assertEqual(next(iter(self.db.records.values()))['window'], 3)

    def test_production_flask_routes_use_shared_quota(self):
        text = (ROOT / 'backend/endpoints.py').read_text(encoding='utf8')
        self.assertIn('Firebase.enforce_quota(uid, "recommendation")', text)
        self.assertIn('Firebase.enforce_quota(uid, "message_id")', text)
        self.assertIn('return error_response("Too many requests", 429)', text)
        self.assertIn('return error_response("Quota service unavailable", 503)', text)

    def test_http_evidence_requires_quota_digest(self):
        from scripts.release_gate_v12 import validate_http_evidence, sha256, ROOT
        record = {
            'validated': True, 'tests_run': 15,
            'failures': 0, 'errors': 0, 'skipped': 0,
            'cases': {str(i): 200 for i in range(15)},
            'source_sha256': {name: sha256(ROOT / location) for name, location in {
                'original': 'audit/baseline/endpoints_original.txt',
                'corrected': 'backend/endpoints.py',
                'test_harness': 'integration/test_original_http_stubbed.py',
                'security_core': 'backend/security_core.py',
                'observability': 'backend/observability.py',
            }.items()},
        }
        self.assertFalse(validate_http_evidence(record))
        record['source_sha256']['shared_quota'] = sha256(ROOT / 'backend/shared_quota.py')
        self.assertFalse(validate_http_evidence(record))
        record['source_sha256']['cors_policy'] = sha256(ROOT / 'backend/cors_policy.py')
        self.assertTrue(validate_http_evidence(record))

    def test_emulator_evidence_requires_quota_digest(self):
        from scripts.release_gate_v12 import validate_emulator_evidence, sha256, ROOT
        record = {
            'validated': True, 'tests_run': 23,
            'project': 'demo-coursesphere-vlab',
            'failures': 0, 'errors': 0, 'skipped': 0,
            'cases': {str(i): 200 for i in range(23)},
            'source_sha256': {name: sha256(ROOT / location) for name, location in {
                'endpoints': 'backend/endpoints.py',
                'firebase': 'backend/firebase.py',
                'firebase_configuration': 'backend/firebase_configuration.py',
                'security_core': 'backend/security_core.py',
                'rules': 'ops/firebase/database.rules.json',
                'emulator_harness': 'integration/test_official_emulators.py',
                'emulator_runner': 'integration/run_official_emulator_tests.py',
            }.items()},
        }
        self.assertFalse(validate_emulator_evidence(record))
        record['source_sha256']['shared_quota'] = sha256(ROOT / 'backend/shared_quota.py')
        self.assertFalse(validate_emulator_evidence(record))
        record['source_sha256']['cors_policy'] = sha256(ROOT / 'backend/cors_policy.py')
        self.assertTrue(validate_emulator_evidence(record))

    def test_client_rules_do_not_expose_server_counters(self):
        import json
        rules = json.loads((ROOT / 'ops/firebase/database.rules.json').read_text())['rules']
        self.assertIs(rules['.read'], False)
        self.assertIs(rules['.write'], False)
        self.assertNotIn('server_security', rules)


if __name__ == '__main__':
    unittest.main()
