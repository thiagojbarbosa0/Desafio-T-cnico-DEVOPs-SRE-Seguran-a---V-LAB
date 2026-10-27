"""Portable regression: a lagging Flask replica cannot reopen an old RTDB window.

Runs with a deterministic fake RTDB transaction, not a live Firebase emulator.
Does not overwrite preexisting shared-quota test modules when copied into V19.15.
"""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from backend.shared_quota import LIMITS, debit, QuotaUnavailable

class MemoryRTDB:
    def __init__(self):
        self.state = {}
        self.lock = threading.Lock()
    def reference(self, path):
        db=self
        class Ref:
            def transaction(self, callback):
                with db.lock:
                    final=callback(db.state.get(path))
                    db.state[path]=final
                    return final
        return Ref()

class ClockSkewQuotaTests(unittest.TestCase):
    def setUp(self):
        self.store=MemoryRTDB()
    def test_lagging_replica_does_not_reset_window(self):
        limit, window=LIMITS['profile_write']
        now=window*100
        for _ in range(limit):
            self.assertTrue(debit(self.store.reference,'alice','profile_write',now=now))
        self.assertFalse(debit(self.store.reference,'alice','profile_write',now=now-1))
        self.assertFalse(debit(self.store.reference,'alice','profile_write',now=now))
        self.assertEqual(next(iter(self.store.state.values())),{'window':100,'count':limit})
    def test_skewed_concurrent_replicas_never_exceed_quota(self):
        limit, period=LIMITS['profile_write']
        # Simulate clocks on opposite sides of one 60s boundary.
        stamps=[period*100 if i%2==0 else period*100-1 for i in range(100)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            result=list(pool.map(lambda t:debit(self.store.reference,'alice','profile_write',now=t),stamps))
        self.assertLessEqual(sum(result),limit)
        self.assertEqual(len(self.store.state),1)
    def test_corrupted_future_window_denied(self):
        debit(self.store.reference,'alice','profile_write',now=180)
        key=next(iter(self.store.state))
        self.store.state[key]={'window':'unexpected','count':0}
        self.assertFalse(debit(self.store.reference,'alice','profile_write',now=180))
    def test_corrupt_counter_denied(self):
        debit(self.store.reference,'alice','profile_write',now=180)
        key=next(iter(self.store.state))
        self.store.state[key]={'window':3,'count':False}
        self.assertFalse(debit(self.store.reference,'alice','profile_write',now=180))

if __name__=='__main__':unittest.main()
