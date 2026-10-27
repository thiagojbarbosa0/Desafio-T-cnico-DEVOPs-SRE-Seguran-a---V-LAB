import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from backend.local_server import make_server

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.server=make_server('127.0.0.1',0,str(Path(cls.tmp.name)/'data.db'),secret='S'*50,instance='integration-A')
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2);cls.tmp.cleanup()
    def call(self,path,method='GET',body=None,token=None,headers=None):
        hdr=dict(headers or {})
        if token: hdr['Authorization']='Bearer '+token
        data=None
        if body is not None:
            data=json.dumps(body).encode()
            hdr['Content-Type']='application/json'
        req=Request(self.base+path,method=method,data=data,headers=hdr)
        try: response=urlopen(req,timeout=3)
        except HTTPError as e: response=e
        content=response.read().decode()
        return response.status,(json.loads(content) if 'application/json' in response.headers.get('Content-Type','') else content),dict(response.headers)
    def login(self,uid): return self.call('/api/demo/session','POST',{'uid':uid})[1]['access_token']

    def test_healthy(self):
        code,obj,headers=self.call('/api/health')
        self.assertEqual(code,200);self.assertEqual(obj['instance'],'integration-A')
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
    def test_readiness(self): self.assertEqual(self.call('/api/ready')[0],200)
    def test_metrics(self):
        code,data,_=self.call('/metrics')
        self.assertEqual(code,200)
        self.assertIn('coursesphere_http_duration_seconds_bucket',data)
    def test_no_cors_wildcard(self):
        code,body,headers=self.call('/api/health',headers={'Origin':'https://attacker.example'})
        self.assertNotIn('Access-Control-Allow-Origin',headers)
    def test_query_string_not_accepted_for_auth(self):
        code,obj,_=self.call('/api/courses?access_token=stolen')
        self.assertEqual(code,401)
    def test_auth_missing(self): self.assertEqual(self.call('/api/courses')[0],401)
    def test_auth_tamper(self):
        token=self.login('alice')
        self.assertEqual(self.call('/api/courses',token=token+'x')[0],401)
    def test_get_courses(self):
        token=self.login('student')
        code,obj,_=self.call('/api/courses',token=token)
        self.assertEqual(code,200);self.assertTrue(obj['courses'])
    def test_student_forbidden(self):
        token=self.login('student')
        self.assertEqual(self.call('/api/courses','POST',{'title':'Test'},token)[0],403)
    def test_bola_update(self):
        token=self.login('alice')
        self.assertEqual(self.call('/api/courses/2','PUT',{'title':'Interferência','description':''},token)[0],403)
    def test_bola_delete(self):
        token=self.login('alice')
        self.assertEqual(self.call('/api/courses/2','DELETE',token=token)[0],403)
    def test_admin_audit(self):
        token=self.login('admin')
        self.assertEqual(self.call('/api/events',token=token)[0],200)
    def test_student_audit_forbidden(self):
        token=self.login('student')
        self.assertEqual(self.call('/api/events',token=token)[0],403)
    def test_crud_lesson(self):
        token=self.login('alice')
        code,created,_=self.call('/api/courses/1/lessons','POST',{'title':'Secure Lesson','content':'ok'},token)
        self.assertEqual(code,201)
        self.assertEqual(self.call('/api/courses/1/lessons/'+str(created['id']),'PUT',{'title':'Changed','content':'ok'},token)[0],200)
        self.assertEqual(self.call('/api/courses/1/lessons/'+str(created['id']),'DELETE',token=token)[0],200)
    def test_too_long_body(self):
        token=self.login('alice')
        self.assertEqual(self.call('/api/courses','POST',{'title':'x'*40000},token)[0],413)
    def test_logs_do_not_expose_tokens(self):
        token=self.login('alice')
        code,obj,headers=self.call('/api/courses?secret='+token,token=token)
        self.assertEqual(code,200)
        self.assertNotIn(token,str(obj))
    def test_demo_unknown_user(self):
        self.assertEqual(self.call('/api/demo/session','POST',{'uid':'root'})[0],400)
