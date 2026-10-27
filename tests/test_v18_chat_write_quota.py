"""V18: chat-write abuse protection on the real Flask source, with offline fakes.

No Firebase services, credentials or live routes are contacted. Full RTDB
transactions remain a separate emulator acceptance criterion.
"""
from __future__ import annotations

import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from backend.shared_quota import LIMITS, QuotaExceeded, QuotaUnavailable, debit
from tests.origin_harness import FakeFirebase, PATCHED, execute_handler


class SharedStore:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()
        self.unavailable = False

    def reference(self, path):
        store = self
        class Ref:
            def transaction(self, callback):
                if store.unavailable:
                    raise ConnectionError('SYNTHETIC storage error not for the client')
                with store.lock:
                    updated = callback(store.data.get(path))
                    store.data[path] = updated
                    return updated
        return Ref()


def message_payload():
    return {'messages': [{'sender': 'user', 'content': 'local test only',
                          'messageID': 'synthetic_msg_1',
                          'timestamp': '2026-10-23T10:00:00Z'}]}


class ChatWriteQuotaRegressions(unittest.TestCase):
    def setUp(self):
        self.store = SharedStore()

    def test_chat_limit_is_explicitly_bounded(self):
        self.assertEqual(LIMITS['chat_write'], (60, 60))

    def test_chat_write_transaction_allows_sixty_then_denies(self):
        decisions = [debit(self.store.reference, 'alice', 'chat_write', now=120) for _ in range(64)]
        self.assertEqual(decisions.count(True), 60)
        self.assertEqual(decisions.count(False), 4)

    def test_different_users_have_independent_write_quota(self):
        for _ in range(60):
            debit(self.store.reference, 'alice', 'chat_write', now=120)
        self.assertFalse(debit(self.store.reference, 'alice', 'chat_write', now=120))
        self.assertTrue(debit(self.store.reference, 'bob', 'chat_write', now=120))

    def test_recommendation_quota_is_separate_from_chat_write(self):
        for _ in range(60):
            debit(self.store.reference, 'alice', 'chat_write', now=120)
        self.assertTrue(debit(self.store.reference, 'alice', 'recommendation', now=120))

    def test_next_window_restores_chat_writes(self):
        for _ in range(60):
            debit(self.store.reference, 'alice', 'chat_write', now=120)
        self.assertTrue(debit(self.store.reference, 'alice', 'chat_write', now=180))
        self.assertEqual(len(self.store.data), 1)

    def test_concurrent_writes_do_not_exceed_quota(self):
        with ThreadPoolExecutor(max_workers=16) as pool:
            decisions=list(pool.map(lambda _: debit(self.store.reference, 'alice', 'chat_write', now=120), range(120)))
        self.assertEqual(decisions.count(True), 60)

    def test_storage_failure_is_not_permitted(self):
        self.store.unavailable = True
        with self.assertRaises(QuotaUnavailable):
            debit(self.store.reference, 'alice', 'chat_write', now=120)

    def test_valid_authenticated_chat_checks_quota_before_writing(self):
        result, calls = execute_handler(PATCHED, 'save_chat', token='SYNTHETIC_TOKEN', payload=message_payload())
        self.assertEqual(result[1], 200)
        names = [entry[0] for entry in calls]
        self.assertLess(names.index('enforce_quota'), names.index('save_chat'))
        self.assertIn(('enforce_quota', 'alice', 'chat_write'), calls)

    def test_invalid_chat_does_not_debit_or_write(self):
        payload = message_payload()
        payload['messages'][0]['messageID'] = '../unsafe'
        result, calls = execute_handler(PATCHED, 'save_chat', token='SYNTHETIC_TOKEN', payload=payload)
        self.assertEqual(result[1], 400)
        self.assertNotIn('enforce_quota', [c[0] for c in calls])
        self.assertNotIn('save_chat', [c[0] for c in calls])

    def test_anonymous_chat_never_uses_the_database(self):
        result, calls = execute_handler(PATCHED, 'save_chat', payload=message_payload())
        self.assertEqual(result[1], 401)
        self.assertFalse(any(c[0] in {'save_chat', 'enforce_quota'} for c in calls))

    def test_exceeded_quota_returns_429_without_writing(self):
        with mock.patch.object(FakeFirebase, 'enforce_quota', side_effect=QuotaExceeded('synthetic only')):
            result, calls = execute_handler(PATCHED, 'save_chat', token='SYNTHETIC_TOKEN', payload=message_payload())
        self.assertEqual(result[1], 429)
        self.assertEqual(result[0]['error'], 'Too many requests')
        self.assertNotIn('save_chat', [c[0] for c in calls])

    def test_unavailable_quota_returns_503_without_writing_or_leak(self):
        with mock.patch.object(FakeFirebase, 'enforce_quota', side_effect=QuotaUnavailable('SYNTHETIC_INTERNAL_ERROR')):
            result, calls = execute_handler(PATCHED, 'save_chat', token='SYNTHETIC_TOKEN', payload=message_payload())
        self.assertEqual(result[1], 503)
        self.assertEqual(result[0]['error'], 'Quota service unavailable')
        self.assertNotIn('SYNTHETIC_INTERNAL_ERROR', repr(result))
        self.assertNotIn('save_chat', [c[0] for c in calls])


if __name__ == '__main__':
    unittest.main()
