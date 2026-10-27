"""V19.4: real handler functions with synthetic Firebase + bounded shared quotas.

The Firebase transaction itself is simulated atomically here; this is NOT a
Firebase Emulator test. Source audits do not substitute for network execution.
"""
from __future__ import annotations

import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from backend.observability import HTTPMetrics
from backend.shared_quota import LIMITS, debit, QuotaExceeded, QuotaUnavailable
from tests.origin_harness import PATCHED, FakeFirebase, execute_handler

ROOT = Path(__file__).resolve().parents[1]


class AtomicRTDB:
    def __init__(self):
        self.entries = {}
        self.lock = threading.Lock()
        self.fail = False

    def reference(self, path):
        store = self
        class Ref:
            def transaction(self, callback):
                if store.fail:
                    raise ConnectionError('synthetic secret internal error')
                with store.lock:
                    value = callback(store.entries.get(path))
                    store.entries[path] = value
                    return value
        return Ref()


def profile():
    return {'majors':['Computing'], 'minors':[], 'courses':[],
            'year':'2026', 'college':'Synthetic University', 'about':'Lab only'}


class ReplicatedWriteLimits(unittest.TestCase):
    def setUp(self):
        self.db = AtomicRTDB()

    def test_profile_write_quota(self):
        self.assertEqual(LIMITS['profile_write'], (20,60))
        results = [debit(self.db.reference, 'alice', 'profile_write', now=120) for _ in range(23)]
        self.assertEqual(results, [True]*20 + [False]*3)

    def test_delete_quota(self):
        self.assertEqual(LIMITS['chat_delete'], (30,60))
        results = [debit(self.db.reference, 'alice', 'chat_delete', now=120) for _ in range(35)]
        self.assertEqual(sum(results), 30)

    def test_parallel_limits_are_transactional(self):
        for action, count in (('profile_write', 80), ('chat_delete', 100)):
            with ThreadPoolExecutor(max_workers=14) as pool:
                outcomes = list(pool.map(lambda _: debit(self.db.reference, 'alice', action, now=120), range(count)))
            self.assertEqual(sum(outcomes), LIMITS[action][0])

    def test_user_action_and_window_independent(self):
        for action in ('profile_write','chat_delete'):
            for _ in range(LIMITS[action][0]):
                self.assertTrue(debit(self.db.reference, 'alice', action, now=120))
            self.assertFalse(debit(self.db.reference, 'alice', action, now=120))
            self.assertTrue(debit(self.db.reference, 'bob', action, now=120))
            self.assertTrue(debit(self.db.reference, 'alice', action, now=180))

    def test_broken_storage_fails_closed(self):
        self.db.fail = True
        for action in ('profile_write','chat_delete'):
            with self.subTest(action=action), self.assertRaises(QuotaUnavailable) as context:
                debit(self.db.reference, 'alice', action, now=120)
            self.assertNotIn('secret',str(context.exception))

    def test_profile_checks_quota_before_write(self):
        result, calls = execute_handler(PATCHED,'set_user_info',token='SYNTHETIC_TOKEN',payload=profile())
        self.assertEqual(result[1],200)
        names=[x[0] for x in calls]
        self.assertLess(names.index('enforce_quota'),names.index('set_user_info'))
        self.assertIn(('enforce_quota','alice','profile_write'),calls)

    def test_invalid_profile_never_debits_quota(self):
        data=profile();data['majors']=['x'*101]
        result,calls=execute_handler(PATCHED,'set_user_info',token='SYNTHETIC_TOKEN',payload=data)
        self.assertEqual(result[1],400)
        self.assertNotIn('enforce_quota',[x[0] for x in calls])

    def test_delete_checks_quota_before_deletion(self):
        result,calls=execute_handler(PATCHED,'delete_chat',token='SYNTHETIC_TOKEN',path_id='safe_chat')
        self.assertEqual(result[1],200)
        names=[x[0] for x in calls]
        self.assertLess(names.index('enforce_quota'),names.index('delete_chat'))
        self.assertIn(('enforce_quota','alice','chat_delete'),calls)

    def test_invalid_chat_id_never_debits(self):
        result,calls=execute_handler(PATCHED,'delete_chat',token='SYNTHETIC_TOKEN',path_id='../unsafe')
        self.assertEqual(result[1],400)
        self.assertNotIn('enforce_quota',[x[0] for x in calls])

    def test_unauthenticated_writes_never_use_quota(self):
        for handler,kwargs in (('set_user_info',{'payload':profile()}),('delete_chat',{'path_id':'safe_chat'})):
            result,calls=execute_handler(PATCHED,handler,**kwargs)
            self.assertEqual(result[1],401)
            self.assertNotIn('enforce_quota',[x[0] for x in calls])

    def test_quota_failure_returns_503_without_mutation(self):
        for handler,kwargs,forbidden in (
            ('set_user_info',{'payload':profile()},'set_user_info'),
            ('delete_chat',{'path_id':'safe_chat'},'delete_chat'),
        ):
            with mock.patch.object(FakeFirebase,'enforce_quota',side_effect=QuotaUnavailable('INTERNAL_PRIVATE')):
                result,calls=execute_handler(PATCHED,handler,token='SYNTHETIC_TOKEN',**kwargs)
            self.assertEqual(result[1],503)
            self.assertEqual(result[0]['error'],'Quota service unavailable')
            self.assertNotIn('PRIVATE',str(result))
            self.assertNotIn(forbidden,[x[0] for x in calls])

    def test_quota_exhaustion_returns_429_without_mutation(self):
        for handler,kwargs,forbidden in (
            ('set_user_info',{'payload':profile()},'set_user_info'),
            ('delete_chat',{'path_id':'safe_chat'},'delete_chat'),
        ):
            with mock.patch.object(FakeFirebase,'enforce_quota',side_effect=QuotaExceeded('local')):
                result,calls=execute_handler(PATCHED,handler,token='SYNTHETIC_TOKEN',**kwargs)
            self.assertEqual(result[1],429)
            self.assertNotIn(forbidden,[x[0] for x in calls])


class AuthenticationEventObservability(unittest.TestCase):
    def test_only_whitelisted_auth_labels(self):
        m=HTTPMetrics()
        m.observe_auth('accepted','/users/info')
        m.observe_auth('denied','/users/info')
        text=m.render()
        self.assertIn('coursesphere_original_auth_attempts_total{result="accepted",route="/users/info"} 1',text)
        self.assertIn('coursesphere_original_auth_attempts_total{result="denied",route="/users/info"} 1',text)
        with self.assertRaises(ValueError):
            m.observe_auth('Bearer SECRET','/users/info')

    def test_auth_never_accepts_querystrings_as_route_labels(self):
        m=HTTPMetrics()
        m.observe_auth('denied','/users/info?token=synthetic_secret')
        self.assertNotIn('synthetic_secret',m.render())
        self.assertIn('route="unmatched"',m.render())

    def test_auth_counter_concurrency(self):
        m=HTTPMetrics()
        def run():
            for _ in range(100):m.observe_auth('denied','/users/info')
        threads=[threading.Thread(target=run) for _ in range(8)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertIn('result="denied",route="/users/info"} 800',m.render())

    def test_auth_event_log_does_not_contain_user_identity(self):
        text=(ROOT/'backend/endpoints.py').read_text()
        section=text[text.index('def audit_auth('):text.index('def verified_uid(')]
        emitted=section[section.index('app.logger.info('):]
        self.assertNotIn('token',emitted)
        self.assertNotIn('uid',emitted)
        self.assertIn('"event": "authentication"',section)


class CIChecks(unittest.TestCase):
    def test_original_flask_nginx_proof_executes_two_separate_commands(self):
        text=(ROOT/'.github/workflows/ci.yml').read_text()
        self.assertIn('''      - name: Exercise original patched Flask behind two native Nginx backends
        run: |
          python3 scripts/check_nginx_main_config_v19_3.py
          python3 scripts/prove_original_flask_nginx.py''',text)
        self.assertNotIn('run: python3 scripts/check_nginx_main_config_v19_3.py\n          python3',text)


if __name__=='__main__': unittest.main()
