"""R7 regression: bounded demo tokens and atomic fail-closed SQLite quotas.

All identities and databases in this suite are synthetic; no external services.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.demo_store import DemoStore
from backend.security_core import DemoTokens, SecurityError


class TokenHardeningR7(unittest.TestCase):
    def setUp(self):
        self.key='K'*40
        self.tokens=DemoTokens(self.key)

    def denied(self, token):
        with self.assertRaises(SecurityError) as ctx:
            self.tokens.verify(token)
        self.assertEqual(ctx.exception.status, 401)

    def signed(self, body):
        raw=body if isinstance(body, bytes) else json.dumps(body, separators=(',', ':')).encode()
        payload=base64.urlsafe_b64encode(raw).rstrip(b'=').decode()
        mac=hmac.new(self.key.encode(), payload.encode(), hashlib.sha256).digest()
        return payload + '.' + base64.urlsafe_b64encode(mac).rstrip(b'=').decode()

    def valid_claims(self):
        return {'uid':'alice','role':'instructor','exp':2000000000,'nonce':'0123456789abcdef'}

    def test_roundtrip(self):
        self.assertEqual(self.tokens.verify(self.tokens.issue('alice','instructor')).uid,'alice')
    def test_no_long_token(self): self.denied('x'*200000 + '.sig')
    def test_no_nonstr_token(self): self.denied(None)
    def test_no_extra_segment(self): self.denied(self.tokens.issue('alice','admin')+'.more')
    def test_no_empty_segment(self): self.denied('.'+'A'*43)
    def test_no_noncanonical_base64(self):
        real=self.tokens.issue('alice','admin')
        self.denied(real+'=')
    def test_duplicate_claim_denied_even_if_correctly_signed(self):
        self.denied(self.signed(b'{"uid":"alice","uid":"bob","role":"admin","exp":2000000000,"nonce":"0123456789abcdef"}'))
    def test_missing_claim_denied(self):
        claims=self.valid_claims(); claims.pop('nonce')
        self.denied(self.signed(claims))
    def test_extra_claim_denied(self):
        claims=self.valid_claims(); claims['admin']=True
        self.denied(self.signed(claims))
    def test_bool_exp_denied(self):
        claims=self.valid_claims(); claims['exp']=True
        self.denied(self.signed(claims))
    def test_bad_nonce_denied(self):
        claims=self.valid_claims(); claims['nonce']='anything'
        self.denied(self.signed(claims))
    def test_future_expiry_denied(self):
        claims=self.valid_claims(); claims['exp']=9999999999
        self.denied(self.signed(claims))
    def test_future_expiry_valid_with_frozen_time(self):
        with patch('backend.security_core.time.time',return_value=1999999000):
            self.assertEqual(self.tokens.verify(self.signed(self.valid_claims())).uid,'alice')
    def test_ttl_is_bounded(self):
        for value in [True, None, 1.5, 90000]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.tokens.issue('alice','admin',value)
    def test_non_string_secret(self):
        with self.assertRaises(ValueError): DemoTokens(None)


class DistributedSqliteQuotaR7(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.db=DemoStore(str(Path(tmp.name)/'shared.db'))
        self.other=DemoStore(str(Path(tmp.name)/'shared.db'))

    def state(self, bucket='login'):
        with self.db.connect() as conn:
            row=conn.execute('SELECT hits,window_started FROM rate_limits WHERE bucket=?',(bucket,)).fetchone()
            return None if row is None else (row['hits'],row['window_started'])

    def test_denied_attempts_do_not_increment(self):
        self.assertTrue(self.db.hit_rate_limit('login',100,2,60))
        self.assertTrue(self.db.hit_rate_limit('login',100,2,60))
        for _ in range(30): self.assertFalse(self.other.hit_rate_limit('login',101,2,60))
        self.assertEqual(self.state(),(2,100))
    def test_window_expiry_resets(self):
        self.db.hit_rate_limit('login',100,1,60)
        self.assertTrue(self.other.hit_rate_limit('login',160,1,60))
        self.assertEqual(self.state(),(1,160))
    def test_rollback_denied_after_clock_advances(self):
        self.db.hit_rate_limit('login',160,2,60)
        self.assertFalse(self.other.hit_rate_limit('login',100,2,60))
        self.assertEqual(self.state(),(1,160))
    def test_corrupt_hit_count_denied(self):
        self.db.hit_rate_limit('login',100,2,60)
        with self.db.connect() as conn:
            conn.execute('UPDATE rate_limits SET hits=-1 WHERE bucket=?',('login',))
        self.assertFalse(self.other.hit_rate_limit('login',200,2,60))
        self.assertEqual(self.state(),(-1,100))
    def test_corrupt_future_window_denied(self):
        self.db.hit_rate_limit('login',100,2,60)
        with self.db.connect() as conn:
            conn.execute('UPDATE rate_limits SET window_started=9999 WHERE bucket=?',('login',))
        self.assertFalse(self.other.hit_rate_limit('login',200,2,60))
        self.assertEqual(self.state(),(1,9999))
    def test_bad_configuration_denied_without_write(self):
        for bucket,now,limit,period in [('login',True,1,60),('login',-1,1,60),
                                        ('login',100,True,60),('login',100,1,0),
                                        ('bad\nkey',100,1,60),('',100,1,60),
                                        ('login',float('nan'),1,60),('login',100,0,60)]:
            with self.subTest(value=(bucket,now,limit,period)), self.assertRaises(ValueError):
                self.db.hit_rate_limit(bucket,now,limit,period)
        self.assertEqual(self.state(), None)
    def test_concurrent_cross_replica_exactly_limit(self):
        stores=[self.db,self.other]
        def request(i): return stores[i%2].hit_rate_limit('login',100,10,60)
        with ThreadPoolExecutor(max_workers=12) as executor:
            results=list(executor.map(request,range(40)))
        self.assertEqual(sum(results),10)
        self.assertEqual(self.state(),(10,100))
    def test_isolated_buckets(self):
        self.db.hit_rate_limit('login',100,1,60)
        self.assertTrue(self.other.hit_rate_limit('profile',100,1,60))
        self.assertFalse(self.other.hit_rate_limit('login',100,1,60))

class StrictJsonR7(unittest.TestCase):
    def test_duplicate_uid_denied(self):
        from backend.security_core import strict_json_loads
        with self.assertRaises(SecurityError):
            strict_json_loads(b'{"uid":"student","uid":"admin"}')
    def test_nested_duplicate_denied(self):
        from backend.security_core import strict_json_loads
        with self.assertRaises(SecurityError):
            strict_json_loads(b'{"user":{"role":"student","role":"admin"}}')
    def test_non_json_constants_denied(self):
        from backend.security_core import strict_json_loads
        for value in [b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}']:
            with self.subTest(value=value), self.assertRaises(SecurityError):
                strict_json_loads(value)
    def test_normal_json(self):
        from backend.security_core import strict_json_loads
        self.assertEqual(strict_json_loads(b'{"uid":"alice","value":[1,true,null]}'),
                         {'uid':'alice','value':[1,True,None]})
    def test_unpaired_surrogate_refused_by_text_validator(self):
        from backend.security_core import bounded_text
        with self.assertRaises(SecurityError):
            bounded_text('x\ud800y','name')
        self.assertEqual(bounded_text('português','name'),'português')
