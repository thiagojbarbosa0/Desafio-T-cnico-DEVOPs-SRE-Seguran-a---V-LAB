import threading
import unittest
from backend.shared_quota import LIMITS, QuotaUnavailable, debit

class TransactionalDB:
    def __init__(self):
        self.store={}
        self.lock=threading.Lock()
    def reference(self,path):
        database=self
        class Ref:
            def transaction(self,fn):
                with database.lock:
                    state=fn(database.store.get(path))
                    database.store[path]=state
                    return state
        return Ref()

class QuotaTests(unittest.TestCase):
    def setUp(self):self.db=TransactionalDB()
    def test_limit(self):
        limit,_=LIMITS['recommendation']
        results=[debit(self.db.reference,'user','recommendation',now=120) for _ in range(limit+3)]
        self.assertEqual(results.count(True),limit)
        self.assertEqual(results.count(False),3)
    def test_per_user(self):
        self.assertTrue(debit(self.db.reference,'alice','recommendation',now=120))
        self.assertTrue(debit(self.db.reference,'bob','recommendation',now=120))
        self.assertEqual(len(self.db.store),2)
    def test_window_reset(self):
        self.assertTrue(debit(self.db.reference,'alice','recommendation',now=119))
        self.assertTrue(debit(self.db.reference,'alice','recommendation',now=120))
        self.assertEqual(len(self.db.store),1)
        self.assertEqual(next(iter(self.db.store.values())),{'window':2,'count':1})
    def test_bad_reference_fails_closed(self):
        def broken(path):raise ConnectionError('test failure')
        with self.assertRaises(QuotaUnavailable):
            debit(broken,'alice','recommendation',now=120)
