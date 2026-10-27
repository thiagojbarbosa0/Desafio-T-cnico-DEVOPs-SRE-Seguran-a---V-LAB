import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.demo_store import DemoStore
from backend.security_core import Principal, SecurityError

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=DemoStore(str(Path(self.tmp.name)/'data.db'))
        self.alice=Principal('alice','instructor')
        self.bob=Principal('bob','instructor')
        self.student=Principal('student','student')
        self.admin=Principal('admin','admin')
    def assertDenied(self,f,status=403):
        with self.assertRaises(SecurityError) as err: f()
        self.assertEqual(err.exception.status,status)

    def test_seed_data(self): self.assertGreaterEqual(len(self.store.list_courses()),2)
    def test_create_student_denied(self): self.assertDenied(lambda:self.store.create_course(self.student,{'title':'Test123'}))
    def test_create_instructor(self):
        row=self.store.create_course(self.alice,{'title':'Test123','description':'body'})
        self.assertEqual(row['owner_uid'],'alice')
    def test_bola_cross_account_update(self):
        self.assertDenied(lambda:self.store.update_course(2,self.alice,{'title':'Hacked','description':''}))
        self.assertEqual(self.store.list_courses()[1]['title'],'Fundamentos de SRE')
    def test_bola_cross_account_delete(self): self.assertDenied(lambda:self.store.delete_course(2,self.alice))
    def test_owner_update_success(self):
        self.store.update_course(1,self.alice,{'title':'Updated','description':'ok'})
        self.assertEqual(self.store.list_courses()[0]['title'],'Updated')
    def test_owner_delete_success(self):
        self.store.delete_course(1,self.alice)
        self.assertEqual(len(self.store.list_courses()),1)
    def test_admin_override(self):
        self.store.update_course(1,self.admin,{'title':'Reviewed','description':''})
        self.assertEqual(self.store.list_courses()[0]['title'],'Reviewed')
    def test_missing_course(self):
        self.assertDenied(lambda:self.store.delete_course(90000,self.alice),404)
    def test_lesson_cross_account(self):
        self.assertDenied(lambda:self.store.create_lesson(2,self.alice,{'title':'Injection','content':'hi'}))
    def test_lesson_course_isolation(self):
        self.assertDenied(lambda:self.store.update_lesson(2,1,self.bob,{'title':'Wrong link','content':'hi'}),404)
    def test_owner_lesson_crud(self):
        created=self.store.create_lesson(1,self.alice,{'title':'Another Lesson','content':'hi'})
        self.store.update_lesson(1,created['id'],self.alice,{'title':'Revised','content':'hi'})
        self.assertEqual(self.store.delete_lesson(1,created['id'],self.alice),{'deleted':True})
    def test_student_cannot_access_events(self): self.assertDenied(lambda:self.store.list_events(self.student))
    def test_admin_can_access_events(self): self.assertIsInstance(self.store.list_events(self.admin),list)
    def test_rate_limit(self):
        self.assertTrue(self.store.hit_rate_limit('key',100,2,60))
        self.assertTrue(self.store.hit_rate_limit('key',100,2,60))
        self.assertFalse(self.store.hit_rate_limit('key',100,2,60))
        self.assertTrue(self.store.hit_rate_limit('key',161,2,60))
    def test_concurrent_seed_only_once(self):
        fresh=Path(self.tmp.name)/'concurrent.db'
        with ThreadPoolExecutor(max_workers=2) as executor:
            stores=list(executor.map(lambda _: DemoStore(str(fresh)), range(2)))
        self.assertEqual(len(stores[0].list_courses()),2)

    def test_rate_limit_shared_between_store_instances(self):
        other=DemoStore(self.store.path)
        self.assertTrue(self.store.hit_rate_limit('x',100,1,60))
        self.assertFalse(other.hit_rate_limit('x',100,1,60))
    def test_sql_injection_treated_as_plain_string(self):
        injected="Course'); DROP TABLE courses; --"
        result=self.store.create_course(self.alice,{'title':injected,'description':''})
        self.assertEqual(result['title'],injected)
        self.assertGreater(len(self.store.list_courses()),1)
