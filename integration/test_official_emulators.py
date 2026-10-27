"""Real CourseSphere Flask HTTP + Firebase Auth/Database Emulator integration tests.

Only run under firebase emulators:exec. The test uses synthetic users and a demo-
project; no remote Firebase, service-account key, or paid API is contacted.
Evidence includes statuses only, never ID tokens or user data.
"""
import json
import hashlib
import secrets
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib import request, error

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
DEMO_PROJECT='demo-coursesphere-vlab'


def require_emulator_environment():
    required = {
        'COURSESPHERE_USE_FIREBASE_EMULATORS': '1',
        'GCLOUD_PROJECT': DEMO_PROJECT,
        'FIREBASE_AUTH_EMULATOR_HOST': '127.0.0.1:9099',
        'FIREBASE_DATABASE_EMULATOR_HOST': '127.0.0.1:9000',
    }
    if any(os.getenv(key) != value for key, value in required.items()):
        raise RuntimeError('Only isolated loopback demo emulators are allowed')
    if any(os.getenv(key) for key in ('FIREBASE_CREDENTIALS_FILE',
                                      'FIREBASE_DATABASE_URL',
                                      'GOOGLE_APPLICATION_CREDENTIALS')):
        raise RuntimeError('Production credential configuration is forbidden in emulator tests')


def call(url, method='GET', payload=None, token=None, timeout=5):
    body=json.dumps(payload).encode() if payload is not None else None
    headers={'Content-Type':'application/json'} if payload is not None else {}
    if token: headers['Authorization']='Bearer '+token
    req=request.Request(url,data=body,headers=headers,method=method)
    try:
        with request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read().decode()
            return resp.status,json.loads(raw) if raw else None
    except error.HTTPError as exc:
        raw=exc.read().decode()
        try: response=json.loads(raw)
        except ValueError: response={'error':'non-JSON response'}
        return exc.code,response


def signup(email):
    code,obj=call('http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=demo-key',
                  'POST',{'email':email,'password':'OnlyLocalTesting_Password_12345','returnSecureToken':True})
    if code!=200:
        raise RuntimeError('Auth emulator synthetic signup failed with HTTP '+str(code))
    return obj['localId'],obj['idToken']


class OfficialFlaskFirebaseEmulatorIntegration(unittest.TestCase):
    """Live Flask HTTP server connecting to real Firebase Emulator Suite services."""
    @classmethod
    def setUpClass(cls):
        require_emulator_environment()
        from werkzeug.serving import make_server
        from endpoints import app
        # Bind directly to port 0; avoids the bind/release race of probing a port first.
        cls.httpd=make_server('127.0.0.1',0,app,threaded=True,
                             request_handler=app.config.get('SAFE_REQUEST_HANDLER'))
        cls.base=f'http://127.0.0.1:{cls.httpd.server_port}'
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True)
        cls.thread.start()
        cls.alice_uid = cls.bob_uid = None
        try:
            cls.alice_uid,cls.alice_token=signup('alice-'+secrets.token_hex(8)+'@synthetic.example.invalid')
            cls.bob_uid,cls.bob_token=signup('bob-'+secrets.token_hex(8)+'@synthetic.example.invalid')
        except Exception:
            # setUpClass failures do not call tearDownClass in unittest.
            try:
                cls.cleanup_fixture_users()
            finally:
                cls.httpd.shutdown()
                cls.thread.join(timeout=4)
            raise
        cls.results={}
        # Every test seeds the fixtures it needs; no dependence on test order.

    @classmethod
    def seed_fixture(cls):
        from firebase import db
        db.reference(f'users/{cls.alice_uid}/chats/chat_synthetic_integration/messages/fixture001').set({
            'sender':'user', 'content':'Seed message in local emulator',
            'messageID':'fixture001', 'timestamp':'2026-10-22T00:00:00Z',
        })

    @classmethod
    def cleanup_fixture_users(cls):
        # The guard is mandatory even for administrative cleanup.
        require_emulator_environment()
        from firebase import db, auth
        # Delete ONLY fixtures created by this test run; never wipe users/.
        for uid in (cls.alice_uid, cls.bob_uid):
            if uid is None:
                continue
            db.reference(f'users/{uid}').delete()
            key = hashlib.sha256(uid.encode('utf-8')).hexdigest()
            db.reference(f'server_security/rate_limits/{key}').delete()
            auth.delete_user(uid)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.cleanup_fixture_users()
        finally:
            cls.httpd.shutdown()
            cls.thread.join(timeout=4)
            # The integration result is written by the authoritative runner.

    def record(self,name,code):
        self.__class__.results[name]=code

    def test_01_live_health(self):
        code,payload=call(self.base+'/health')
        self.assertEqual(code,200)
        self.assertEqual(payload['status'],'ok')
        self.record('live_health',code)

    def test_02_prohibit_privileged_anonymous_registration(self):
        code,_=call(self.base+'/users/create','POST',{'email':'not-real@example.invalid','password':'abc'})
        self.assertEqual(code,410)
        self.record('privileged_registration_disabled',code)

    def test_03_unauthenticated_profile_denied(self):
        code,_=call(self.base+'/users/info')
        self.assertEqual(code,401)
        self.record('no_auth_denied',code)

    def test_04_token_in_url_denied(self):
        # Never place a real token in a URL. This uses a deliberate invalid marker.
        code,_=call(self.base+'/users/info?id_token=NON_SECRET_MARKER')
        self.assertEqual(code,401)
        self.record('querystring_token_denied',code)

    def test_05_alice_can_save_read_own_profile(self):
        data={'majors':['Mathematics'],'minors':[],'courses':[],'year':'2026',
              'college':'Synthetic Test University','about':'Private synthetic user',
              'uid':self.bob_uid, 'id_token':'FORGED_BODY_MARKER'}
        code,payload=call(self.base+'/users/info','POST',data,self.alice_token)
        self.assertEqual(code,200)
        self.assertEqual(payload['uid'],self.alice_uid)
        code,payload=call(self.base+'/users/info',token=self.alice_token)
        self.assertEqual(code,200)
        self.assertEqual(payload['majors'],['Mathematics'])
        self.record('alice_self_profile_write_read',code)

    def test_06_bob_is_isolated_from_alice_profile(self):
        code,payload=call(self.base+'/users/info',token=self.bob_token)
        self.assertEqual(code,200)
        self.assertTrue(payload is None or payload.get('majors')!=['Mathematics'])
        self.record('bob_profile_isolation',code)

    def test_07_database_rules_deny_anonymous_read(self):
        # The emulator enforces the checked-in RTDB rules for client requests.
        database='http://127.0.0.1:9000/users/anyone/info.json?ns='+DEMO_PROJECT+'-default-rtdb'
        code,_=call(database)
        self.assertEqual(code,401)
        self.record('database_anonymous_access_denied',code)

    def test_08_malformed_user_info_rejected(self):
        code,_=call(self.base+'/users/info','POST',{'about':'A'*1201},self.alice_token)
        self.assertEqual(code,400)
        self.record('oversized_profile_rejected',code)

    def test_09_invalid_token_rejected(self):
        code,_=call(self.base+'/users/info',token='SYNTHETIC_INVALID_TOKEN')
        self.assertEqual(code,401)
        self.record('invalid_token_rejected',code)

    def test_10_chat_data_saved_only_for_authenticated_uid(self):
        self.seed_fixture()
        chat_id='chat_synthetic_integration'
        message={'sender':'user','content':'A safe local message','messageID':'integration01','timestamp':'2026-10-22'}
        code,_=call(self.base+f'/chats/{chat_id}/messages','POST',{'messages':[message]},self.alice_token)
        self.assertEqual(code,200)
        from firebase import db
        alice=db.reference(f'users/{self.alice_uid}/chats/{chat_id}/messages').get()
        bob=db.reference(f'users/{self.bob_uid}/chats/{chat_id}/messages').get()
        # setUpClass deliberately seeded fixture001 in this same chat.
        # A second message must be added without overwriting the fixture.
        self.assertEqual(set(alice), {'fixture001', 'integration01'})
        self.assertIsNone(bob)
        self.record('chat_uid_isolation',code)

    def test_11_chats_list_only_self(self):
        self.seed_fixture()
        code,alice=call(self.base+'/chats',token=self.alice_token)
        self.assertEqual(code,200)
        self.assertTrue(any(item['title']=='chat_synthetic_integration' for item in alice['chats']))
        code,bob=call(self.base+'/chats',token=self.bob_token)
        self.assertEqual(code,200)
        self.assertFalse(any(item['title']=='chat_synthetic_integration' for item in bob['chats']))
        self.record('chats_list_by_verified_uid',code)

    def test_12_cross_user_delete_does_not_touch_other_users_chat(self):
        self.seed_fixture()
        chat_id='chat_synthetic_integration'
        code,_=call(self.base+f'/chats/{chat_id}','DELETE',token=self.bob_token)
        self.assertEqual(code,200)
        from firebase import db
        self.assertTrue(db.reference(f'users/{self.alice_uid}/chats/{chat_id}/messages').get())
        self.record('cross_user_delete_isolated',code)

    def test_13_chat_retry_does_not_duplicate_messages(self):
        chat_id='chat_retry_proof'
        message={'sender':'user','content':'Retry-safe payload','messageID':'retrymessage01',
                 'timestamp':'2026-10-22T00:00:00Z'}
        statuses=[]
        for _ in range(3):
            code,_=call(self.base+f'/chats/{chat_id}/messages','POST',{'messages':[message]},self.alice_token)
            self.assertEqual(code,200)
            statuses.append(code)
        from firebase import db
        result=db.reference(f'users/{self.alice_uid}/chats/{chat_id}/messages').get()
        self.assertEqual(len(result),1)
        self.assertIn('retrymessage01',result)
        self.record('chat_retry_idempotent', statuses)

    def test_14_object_message_content_rejected_over_http(self):
        bad={'messages':[{'sender':'bot','content':{'response':'unsupported'},
                          'messageID':'badmsg001','timestamp':'2026-10-22T00:00:00Z'}]}
        code,_=call(self.base+'/chats/chat_validation/messages','POST',bad,self.alice_token)
        self.assertEqual(code,400)
        self.record('message_schema_rejects_object_content',code)

    def test_15_malformed_auth_does_not_leak_internal_trace(self):
        code,data=call(self.base+'/users/info',token='LOCAL_MALFORMED_TOKEN')
        self.assertEqual(code,401)
        self.assertNotIn('Traceback',json.dumps(data))
        self.assertNotIn('firebase_admin',json.dumps(data))
        self.record('auth_error_generic',code)
    def test_16_reject_query_token_even_with_valid_bearer(self):
        # A valid header must not cause an unsafe token-bearing URL to be accepted.
        # Query strings could be leaked by access logs/history; fail closed.
        code, payload = call(self.base+'/users/info?id_token=NON_SECRET_MARKER', token=self.alice_token)
        self.assertEqual(code, 401)
        self.assertEqual(payload.get('error'), 'Use Authorization header')
        self.record('token_in_url_rejected_even_with_bearer', code)

    def test_17_chats_list_requires_authentication(self):
        code, _ = call(self.base+'/chats')
        self.assertEqual(code, 401)
        self.record('chat_index_requires_auth', code)

    def test_18_security_headers_present(self):
        from urllib.request import urlopen
        with urlopen(self.base+'/health', timeout=5) as response:
            self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
            self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
            self.assertEqual(response.headers.get('Cache-Control'), 'no-store')
        self.record('http_security_headers', 200)

    def test_19_untrusted_cors_origin_not_allowed(self):
        req=request.Request(self.base+'/health', headers={'Origin':'https://untrusted.example.invalid'})
        with request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIsNone(resp.headers.get('Access-Control-Allow-Origin'))
        self.record('untrusted_origin_cors_denied', 200)


    def test_20_rate_limit_shared_via_firebase_admin_transaction(self):
        """Exhaust the real shared quota and prove HTTP 429, then recover.

        The server is Flask real and the counter lives in the RTDB emulator,
        not an in-process Python dict. No requests are sent to a real project.
        """
        import hashlib
        from firebase import db
        # Avoid intermittency if this test starts at the end of the fixed window.
        seconds = int(time.time()) % 60
        if seconds >= 48:
            time.sleep(60 - seconds + 1)
        key = hashlib.sha256(self.alice_uid.encode('utf-8')).hexdigest()
        path = f'server_security/rate_limits/{key}/recommendation'
        ref = db.reference(path)
        try:
            ref.set({'window': int(time.time()) // 60, 'count': 30})
            code, body = call(self.base + '/users/query', 'POST',
                              {'query': 'Synthetic quota check'}, self.alice_token)
            self.assertEqual(code, 429)
            self.assertEqual(body.get('error'), 'Too many requests')
            ref.set({'window': int(time.time()) // 60, 'count': 0})
            code, body = call(self.base + '/users/query', 'POST',
                              {'query': 'Synthetic quota check'}, self.alice_token)
            self.assertEqual(code, 200)
            self.assertIn('botResponse', body)
            # Separately verify that chat writes use the same shared RTDB
            # enforcement, instead of an independent counter per replica.
            chat_path = f'server_security/rate_limits/{key}/chat_write'
            chat_ref = db.reference(chat_path)
            try:
                chat_ref.set({'window': int(time.time()) // 60, 'count': 60})
                message = {'sender': 'user', 'content': 'Local quota test',
                           'messageID': 'quota_synthetic_01',
                           'timestamp': '2026-10-23T10:00:00Z'}
                code, body = call(self.base + '/chats/quota_synthetic/messages',
                                  'POST', {'messages': [message]}, self.alice_token)
                self.assertEqual(code, 429)
                self.assertEqual(body.get('error'), 'Too many requests')
                self.assertIsNone(db.reference(f'users/{self.alice_uid}/chats/quota_synthetic').get())
                chat_ref.set({'window': int(time.time()) // 60, 'count': 0})
                code, body = call(self.base + '/chats/quota_synthetic/messages',
                                  'POST', {'messages': [message]}, self.alice_token)
                self.assertEqual(code, 200)
                self.assertIn('quota_synthetic_01', db.reference(
                    f'users/{self.alice_uid}/chats/quota_synthetic/messages').get())
            finally:
                chat_ref.delete()
                db.reference(f'users/{self.alice_uid}/chats/quota_synthetic').delete()
            # V19.4 extends the same RTDB-backed contract to profile updates
            # and deletions, which could previously bypass the distributed limit.
            profile_ref = db.reference(f'server_security/rate_limits/{key}/profile_write')
            delete_ref = db.reference(f'server_security/rate_limits/{key}/chat_delete')
            marker_path = f'users/{self.alice_uid}/chats/quota_delete_synthetic'
            marker = db.reference(marker_path)
            profile_payload = {'majors': [], 'minors': [], 'courses': [],
                               'year': '2026', 'college': 'Synthetic University',
                               'about': 'Profile quota synthetic test'}
            try:
                profile_ref.set({'window': int(time.time()) // 60, 'count': 20})
                code, body = call(self.base+'/users/info', 'POST', profile_payload, self.alice_token)
                self.assertEqual(code, 429)
                self.assertEqual(body.get('error'), 'Too many requests')
                profile_ref.set({'window': int(time.time()) // 60, 'count': 0})
                code, _ = call(self.base+'/users/info', 'POST', profile_payload, self.alice_token)
                self.assertEqual(code, 200)
                marker.set({'messages': {'fixture': {'sender':'user','content':'Synthetic marker'}}})
                delete_ref.set({'window': int(time.time()) // 60, 'count': 30})
                code, body = call(self.base+'/chats/quota_delete_synthetic',
                                  'DELETE', token=self.alice_token)
                self.assertEqual(code, 429)
                self.assertEqual(body.get('error'), 'Too many requests')
                self.assertIsNotNone(marker.get())
                delete_ref.set({'window': int(time.time()) // 60, 'count': 0})
                code, _ = call(self.base+'/chats/quota_delete_synthetic',
                               'DELETE', token=self.alice_token)
                self.assertEqual(code, 200)
                self.assertIsNone(marker.get())
            finally:
                profile_ref.delete()
                delete_ref.delete()
                marker.delete()
            self.record('shared_firebase_rate_limit_429_then_200',
                        {'recommendations': [429, 200], 'chat_writes': [429, 200],
                         'profile_writes': [429, 200], 'chat_deletes': [429, 200]})
        finally:
            ref.delete()

    def test_21_rtdb_client_cannot_bypass_flask_validation_and_quota(self):
        """Prove REAL emulator rules with a synthetic authenticated ID token.

        RTDB REST requires an ``auth=`` query for *Firebase ID tokens* (not an
        OAuth2 Bearer header). Only loopback and demo accounts are used; token
        values are never printed, persisted or included in evidence output.
        """
        from urllib.parse import quote
        database='http://127.0.0.1:9000'
        namespace=DEMO_PROJECT+'-default-rtdb'
        uid=quote(self.alice_uid, safe='')
        bob_token=quote(self.bob_token, safe='')
        alice_token=quote(self.alice_token, safe='')
        path=f'/users/{uid}/info.json?ns={namespace}'
        # First, prove the token genuinely authenticates a permitted read;
        # otherwise 401 on a write could be an auth harness failure.
        code, data=call(self.base+'/users/info', 'POST', {
            'majors':[], 'minors':[], 'courses':[],
            'about':'Validated via Flask', 'year':'2026',
            'college':'Synthetic Test University',
        }, self.alice_token)
        self.assertEqual(code, 200)
        code, own=call(database+path+'&auth='+alice_token)
        self.assertEqual(code, 200)
        self.assertEqual(own.get('about'), 'Validated via Flask')
        code, _=call(database+path+'&auth='+bob_token)
        self.assertIn(code, (401, 403))
        for kind, target, payload in (
            ('profile', path, {'about':'INVALID_DIRECT_WRITE'}),
            ('chat', f'/users/{uid}/chats/bypass/messages/danger.json?ns={namespace}',
             {'content':'unvalidated', 'sender':'admin'}),
        ):
            code, _=call(database+target+'&auth='+alice_token, 'PUT', payload)
            self.assertIn(code, (401, 403),
                          f'Authenticated client {kind} write bypassed Flask: {code}')
        # Server-side Firebase Admin must retain valid write access.
        from firebase import db
        self.assertEqual(db.reference(f'users/{self.alice_uid}/info').get()['about'],
                         'Validated via Flask')
        self.assertIsNone(db.reference(f'users/{self.alice_uid}/chats/bypass').get())
        self.record('rtdb_client_write_bypass_closed_reads_preserved',
                    {'own_read':200, 'other_read':'denied', 'direct_writes':'denied',
                     'flask_validated_write':200})

    def test_22_replicas_share_the_same_emulator_quota(self):
        """Two REAL Flask HTTP listeners debit one RTDB emulator counter.

        This is NOT two Docker containers: the listeners share a Python process,
        but every debit is a Firebase RTDB transaction, never a Python counter.
        """
        import hashlib
        from werkzeug.serving import make_server
        from endpoints import app
        from firebase import db
        # Keep calls in a single one-minute window to avoid time-boundary flakes.
        seconds = int(time.time()) % 60
        if seconds >= 48:
            time.sleep(60 - seconds + 1)
        second = make_server('127.0.0.1', 0, app, threaded=True)
        worker = threading.Thread(target=second.serve_forever, daemon=True)
        worker.start()
        port = second.server_port
        ref = db.reference('server_security/rate_limits/' +
            hashlib.sha256(self.alice_uid.encode('utf-8')).hexdigest() + '/recommendation')
        try:
            ref.set({'window': int(time.time()) // 60, 'count': 29})
            first, _ = call(self.base+'/users/query', 'POST', {'query':'Synthetic sample 1'}, self.alice_token)
            second_status, payload = call(f'http://127.0.0.1:{port}/users/query', 'POST',
                                           {'query':'Synthetic sample 2'}, self.alice_token)
            self.assertEqual(first, 200)
            self.assertEqual(second_status, 429)
            self.assertEqual(payload.get('error'), 'Too many requests')
            counter = ref.get()
            self.assertEqual(counter['count'], 30)
            self.record('two_flask_listeners_share_emulator_quota',
                        {'first_listener':200, 'second_listener':429, 'committed_count':30})
        finally:
            ref.delete()
            second.shutdown()
            worker.join(timeout=5)
            second.server_close()

    def test_23_private_rate_limit_counters_are_inaccessible_to_clients(self):
        """Authenticated clients cannot inspect or change server-owned quota state."""
        from urllib.parse import quote
        from firebase import db
        namespace = DEMO_PROJECT + '-default-rtdb'
        path = '/server_security/rate_limits/proof_placeholder.json?ns=' + namespace
        # Ensure fixture exists through a trusted server-side adapter first.
        ref = db.reference('server_security/rate_limits/proof_placeholder')
        ref.set({'count': 1, 'window': 1})
        try:
            token = quote(self.alice_token, safe='')
            code, _ = call('http://127.0.0.1:9000'+path+'&auth='+token)
            self.assertIn(code, (401,403))
            code_write, _ = call('http://127.0.0.1:9000'+path+'&auth='+token,
                                 'PUT', {'count': 0, 'window': 1})
            self.assertIn(code_write, (401,403))
            self.assertEqual(ref.get()['count'], 1)
            self.record('quota_counters_private_to_admin', {'read':'denied','write':'denied'})
        finally:
            ref.delete()


if __name__=='__main__':
    unittest.main(verbosity=2)
