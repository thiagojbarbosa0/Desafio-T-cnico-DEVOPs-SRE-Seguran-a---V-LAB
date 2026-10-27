"""Deterministic Firebase RTDB transaction regression suite, without the emulator.

These tests do not claim 20/21 HTTP acceptance or distributed clock synchronization.
"""
import math
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from backend.shared_quota import debit, LIMITS, QuotaUnavailable


class Store:
    def __init__(self):
        self.state = {}
        self.mutex = threading.Lock()
        self.calls = 0

    def reference(self, path):
        store = self
        class Ref:
            def transaction(self, callback):
                with store.mutex:
                    store.calls += 1
                    result = callback(store.state.get(path))
                    store.state[path] = result
                    return result
        return Ref()


class R3QuotaRegression(unittest.TestCase):
    def setUp(self):
        self.db = Store()

    def test_invalid_explicit_clocks_never_touch_storage(self):
        invalid = (True, False, None, '180', b'180', [], {},
                   float('nan'), float('inf'), float('-inf'), -0.1,
                   253402300800, 10**100)
        for t in invalid:
            # None means default trusted wall clock by API contract.
            if t is None:
                continue
            with self.subTest(clock=t), self.assertRaises(ValueError):
                debit(self.db.reference, 'alice', 'profile_write', now=t)
        self.assertEqual(self.db.calls, 0)

    def test_default_broken_wall_clock_returns_unavailable(self):
        for clock in (float('nan'), float('inf'), -1, True, 10**100):
            with self.subTest(clock=clock), patch('backend.shared_quota.time.time', return_value=clock):
                with self.assertRaises(QuotaUnavailable):
                    debit(self.db.reference, 'alice', 'profile_write')
        self.assertEqual(self.db.calls, 0)

    def test_corrupt_counter_stays_denied_after_next_window(self):
        self.assertTrue(debit(self.db.reference, 'alice', 'profile_write', now=60))
        key = next(iter(self.db.state))
        for corrupt in (-1, 21, '1', False, None, [], 1.5):
            with self.subTest(counter=corrupt):
                self.db.state[key] = {'window': 1, 'count': corrupt}
                self.assertFalse(debit(self.db.reference, 'alice', 'profile_write', now=120))
                self.assertEqual(self.db.state[key], {'window': 1, 'count': corrupt})

    def test_expected_reset_for_well_formed_prior_window(self):
        self.assertTrue(debit(self.db.reference, 'alice', 'profile_write', now=119))
        self.assertTrue(debit(self.db.reference, 'alice', 'profile_write', now=120))
        self.assertEqual(next(iter(self.db.state.values())), {'window': 2, 'count': 1})

    def test_20_accept_21_reject_under_concurrent_calls(self):
        with ThreadPoolExecutor(max_workers=20) as executor:
            decisions = list(executor.map(
                lambda _: debit(self.db.reference, 'alice', 'profile_write', now=240),
                range(100)))
        self.assertEqual(sum(decisions), LIMITS['profile_write'][0])
        self.assertEqual(next(iter(self.db.state.values()))['count'], 20)

    def test_transaction_raises_without_mutating_or_bypassing(self):
        def broken(_):
            raise RuntimeError('sensitive synthetic storage details')
        with self.assertRaises(QuotaUnavailable) as context:
            debit(broken, 'alice', 'profile_write', now=120)
        self.assertNotIn('sensitive', str(context.exception))
        self.assertEqual(self.db.state, {})

    def test_previous_future_window_does_not_roll_back(self):
        self.assertTrue(debit(self.db.reference, 'alice', 'profile_write', now=180))
        key = next(iter(self.db.state))
        self.assertFalse(debit(self.db.reference, 'alice', 'profile_write', now=119))
        self.assertEqual(self.db.state[key]['window'], 3)


if __name__ == '__main__':
    unittest.main()
