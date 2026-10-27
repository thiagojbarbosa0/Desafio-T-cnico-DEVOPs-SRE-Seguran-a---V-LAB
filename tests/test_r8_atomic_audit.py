"""R8: prove mutations and their events commit together in the synthetic lab.

No Flask/Firebase or production claims. Uses real SQLite with two Store instances.
"""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from backend.demo_store import DemoStore
from backend.security_core import Principal, SecurityError


class AtomicAuditR8(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = str(Path(tmp.name) / 'r8.sqlite3')
        self.first = DemoStore(path)
        self.second = DemoStore(path)
        self.alice = Principal('alice', 'instructor')
        self.bob = Principal('bob', 'instructor')
        self.admin = Principal('admin', 'admin')
        self.student = Principal('student', 'student')

    def events(self):
        return self.first.list_events(self.admin)

    def block_audit(self):
        with self.first.connect() as db:
            db.execute('''CREATE TRIGGER fail_audit_r8 BEFORE INSERT ON audit_events
                       BEGIN SELECT RAISE(ABORT, 'synthetic audit failure'); END''')

    def test_create_course_single_atomic_event(self):
        course = self.first.create_course(self.alice, {'title': 'R8 course'})
        matching = [x for x in self.events() if x['action'] == 'course.create']
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]['target'], str(course['id']))
        self.assertEqual(matching[0]['actor'], 'alice')

    def test_update_course_single_atomic_event(self):
        self.first.update_course(1, self.alice, {'title':'Changed'})
        self.assertEqual([x['action'] for x in self.events()], ['course.update'])

    def test_delete_course_single_atomic_event(self):
        self.first.delete_course(1, self.alice)
        self.assertEqual([x['action'] for x in self.events()], ['course.delete'])

    def test_create_lesson_single_atomic_event(self):
        item = self.second.create_lesson(1, self.alice, {'title': 'Atomic lesson'})
        self.assertEqual([x['action'] for x in self.events()], ['lesson.create'])
        self.assertEqual(item['course_id'], 1)

    def test_update_lesson_single_atomic_event(self):
        self.second.update_lesson(1, 1, self.alice, {'title': 'Safe title'})
        self.assertEqual([x['action'] for x in self.events()], ['lesson.update'])

    def test_delete_lesson_single_atomic_event(self):
        self.second.delete_lesson(1, 1, self.alice)
        self.assertEqual([x['action'] for x in self.events()], ['lesson.delete'])

    def test_course_create_rolls_back_when_audit_fails(self):
        before = self.first.list_courses()
        self.block_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.first.create_course(self.alice, {'title': 'Must roll back'})
        self.assertEqual(self.first.list_courses(), before)

    def test_course_update_rolls_back_when_audit_fails(self):
        before = self.first.list_courses()
        self.block_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.second.update_course(1, self.alice, {'title': 'Never persists'})
        self.assertEqual(self.first.list_courses(), before)

    def test_course_delete_rolls_back_when_audit_fails(self):
        before = self.first.list_courses()
        self.block_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.first.delete_course(1, self.alice)
        self.assertEqual(self.first.list_courses(), before)

    def test_lesson_create_rolls_back_when_audit_fails(self):
        before = self.first.list_lessons(1)
        self.block_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.second.create_lesson(1, self.alice, {'title': 'Not created'})
        self.assertEqual(self.first.list_lessons(1), before)

    def test_lesson_update_rolls_back_when_audit_fails(self):
        before = self.first.list_lessons(1)
        self.block_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.first.update_lesson(1, 1, self.alice, {'title': 'Not updated'})
        self.assertEqual(self.first.list_lessons(1), before)

    def test_lesson_delete_rolls_back_when_audit_fails(self):
        before = self.first.list_lessons(1)
        self.block_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.second.delete_lesson(1, 1, self.alice)
        self.assertEqual(self.first.list_lessons(1), before)

    def test_audit_log_cannot_be_modified_using_normal_sql(self):
        self.first.create_course(self.alice, {'title': 'Tracked'})
        for sql in ('DELETE FROM audit_events',
                    "UPDATE audit_events SET outcome='denied'"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                with self.second.connect() as db:
                    db.execute(sql)
        self.assertEqual(len(self.events()), 1)

    def test_reopening_store_keeps_append_only_triggers(self):
        reopened = DemoStore(self.first.path)
        self.first.create_course(self.alice, {'title':'Reopened'})
        with self.assertRaises(sqlite3.IntegrityError):
            with reopened.connect() as db:
                db.execute('DELETE FROM audit_events')

    def test_authorization_failure_creates_no_allowed_event(self):
        before = self.first.list_courses()
        with self.assertRaises(SecurityError):
            self.second.update_course(1, self.bob, {'title':'Forbidden'})
        self.assertEqual(self.first.list_courses(), before)
        self.assertEqual(self.events(), [])

    def test_invalid_content_creates_no_event(self):
        with self.assertRaises(SecurityError):
            self.first.create_course(self.alice, {'title':'x'})
        self.assertEqual(self.events(), [])

    def test_parallel_replica_writes_all_have_audit_entries(self):
        def create(i):
            store = self.first if i % 2 else self.second
            return store.create_course(self.alice, {'title': f'Course {i}'})['id']
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids=list(pool.map(create,range(18)))
        self.assertEqual(len(set(ids)),18)
        seen=[x for x in self.events() if x['action']=='course.create']
        self.assertEqual(len(seen),18)
        self.assertEqual({str(i) for i in ids},{x['target'] for x in seen})


if __name__ == '__main__':
    unittest.main()
