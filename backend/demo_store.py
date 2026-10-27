"""SQLite sandbox for synthetic data only. Per-request connections; WAL for dual replicas."""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from .security_core import SecurityError, Principal, validate_course, validate_lesson, safe_identifier

class DemoStore:
    def __init__(self, path: str):
        self.path=str(Path(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        conn=sqlite3.connect(self.path, timeout=10)
        conn.row_factory=sqlite3.Row
        conn.execute('PRAGMA busy_timeout=10000')
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        # Two replicas can open a brand new volume simultaneously. WAL mode
        # changes may return SQLITE_BUSY immediately despite busy_timeout.
        for attempt in range(20):
            try:
                self._initialize_once()
                return
            except sqlite3.OperationalError as error:
                if 'locked' not in str(error).lower() or attempt == 19:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _initialize_once(self):
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
              CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_uid TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT ''
              );
              CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT ''
              );
              CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                target TEXT NOT NULL,
                outcome TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
              );
              CREATE TRIGGER IF NOT EXISTS audit_events_no_update
              BEFORE UPDATE ON audit_events BEGIN
                SELECT RAISE(ABORT, 'append-only audit');
              END;
              CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
              BEFORE DELETE ON audit_events BEGIN
                SELECT RAISE(ABORT, 'append-only audit');
              END;
              CREATE TABLE IF NOT EXISTS rate_limits (
                bucket TEXT PRIMARY KEY,
                hits INTEGER NOT NULL,
                window_started INTEGER NOT NULL
              );
            ''')
            db.execute('BEGIN IMMEDIATE')  # serialize seed checks across startup replicas
            count=db.execute('SELECT COUNT(*) FROM courses').fetchone()[0]
            if count == 0:
                db.execute("INSERT INTO courses(owner_uid,title,description) VALUES(?,?,?)",('alice','Segurança de Aplicações','Exemplos sintéticos para o laboratório'))
                db.execute("INSERT INTO courses(owner_uid,title,description) VALUES(?,?,?)",('bob','Fundamentos de SRE','Simulações de confiabilidade e observabilidade'))
                db.execute("INSERT INTO lessons(course_id,title,content) VALUES(1,?,?)",('Autorização por recurso','Validar identidade e titularidade em cada escrita'))

    @staticmethod
    def _audit_in_transaction(db, action, principal, target, outcome='allowed'):
        """Commit business mutations and their audit evidence in one transaction.

        A failure to record the event must roll back the mutation. Never perform
        a second independent commit after returning a successful response.
        """
        db.execute("INSERT INTO audit_events(action,actor,target,outcome) VALUES(?,?,?,?)",
                   (action, principal.uid, str(target), outcome))

    def log_event(self, action, principal, target, outcome):
        with self.connect() as db:
            db.execute("INSERT INTO audit_events(action,actor,target,outcome) VALUES(?,?,?,?)",
                       (action, principal.uid, str(target), outcome))

    def list_events(self, principal):
        if principal.role != 'admin':
            raise SecurityError('Forbidden',403)
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,action,actor,target,outcome,created_at FROM audit_events ORDER BY id DESC LIMIT 40')]

    def _owned(self, db, course_id, principal):
        course=db.execute('SELECT * FROM courses WHERE id=?',(course_id,)).fetchone()
        if not course:
            raise SecurityError('Course not found', 404)
        if principal.role != 'admin' and course['owner_uid'] != principal.uid:
            raise SecurityError('Forbidden', 403)
        return course

    def list_courses(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,owner_uid,title,description FROM courses ORDER BY id')]

    def create_course(self, principal: Principal, value):
        if principal.role not in {'instructor','admin'}:
            raise SecurityError('Forbidden',403)
        data=validate_course(value)
        with self.connect() as db:
            cursor=db.execute('INSERT INTO courses(owner_uid,title,description) VALUES(?,?,?)',
                              (principal.uid, data['title'], data['description']))
            self._audit_in_transaction(db, 'course.create', principal, cursor.lastrowid)
            return {'id':cursor.lastrowid, 'owner_uid':principal.uid, **data}

    def update_course(self, course_id, principal, value):
        data=validate_course(value)
        with self.connect() as db:
            self._owned(db,course_id,principal)
            db.execute('UPDATE courses SET title=?, description=? WHERE id=?',
                       (data['title'],data['description'],course_id))
            self._audit_in_transaction(db, 'course.update', principal, course_id)
        return {'id':course_id, **data}

    def delete_course(self, course_id, principal):
        with self.connect() as db:
            self._owned(db,course_id,principal)
            db.execute('DELETE FROM courses WHERE id=?',(course_id,))
            self._audit_in_transaction(db, 'course.delete', principal, course_id)
        return {'deleted':True}

    def list_lessons(self,course_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,course_id,title,content FROM lessons WHERE course_id=? ORDER BY id',(course_id,))]

    def create_lesson(self,course_id,principal,value):
        data=validate_lesson(value)
        with self.connect() as db:
            self._owned(db,course_id,principal)
            cursor=db.execute('INSERT INTO lessons(course_id,title,content) VALUES(?,?,?)',(course_id,data['title'],data['content']))
            self._audit_in_transaction(db, 'lesson.create', principal, course_id)
            return {'id':cursor.lastrowid,'course_id':course_id,**data}

    def update_lesson(self,course_id,lesson_id,principal,value):
        data=validate_lesson(value)
        with self.connect() as db:
            self._owned(db,course_id,principal)
            row=db.execute('SELECT id FROM lessons WHERE id=? AND course_id=?',(lesson_id,course_id)).fetchone()
            if row is None:
                raise SecurityError('Lesson not found',404)
            db.execute('UPDATE lessons SET title=?,content=? WHERE id=?',(data['title'],data['content'],lesson_id))
            self._audit_in_transaction(db, 'lesson.update', principal, lesson_id)
        return {'id':lesson_id,'course_id':course_id,**data}

    def delete_lesson(self,course_id,lesson_id,principal):
        with self.connect() as db:
            self._owned(db,course_id,principal)
            cursor=db.execute('DELETE FROM lessons WHERE id=? AND course_id=?',(lesson_id,course_id))
            if cursor.rowcount == 0:
                raise SecurityError('Lesson not found',404)
            self._audit_in_transaction(db, 'lesson.delete', principal, lesson_id)
        return {'deleted':True}

    def hit_rate_limit(self, bucket: str, now: int, limit: int = 6, window_seconds: int = 60) -> bool:
        """Fail-closed, bounded SQLite limiter shared across local replicas.

        Rejected attempts never increase the stored hit count. Clock rollback,
        corrupted records and invalid configuration must not reset a quota.
        BEGIN IMMEDIATE serializes readers/writers between both processes.
        This protects the *synthetic* demo; original Flask uses Firebase RTDB.
        """
        if (not isinstance(bucket, str) or not bucket or len(bucket) > 256
                or any(ord(ch) < 32 for ch in bucket)):
            raise ValueError('Invalid rate-limit bucket')
        if (type(now) is not int or not 0 <= now <= 253402300799
                or type(limit) is not int or not 1 <= limit <= 10000
                or type(window_seconds) is not int or not 1 <= window_seconds <= 86400):
            raise ValueError('Invalid rate-limit configuration or clock')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT hits,window_started FROM rate_limits WHERE bucket=?', (bucket,)).fetchone()
            if row:
                hits, started = row['hits'], row['window_started']
                if (type(hits) is not int or type(started) is not int
                        or not 0 <= started <= now or not 0 <= hits <= limit):
                    return False
                if now - started < window_seconds:
                    if hits >= limit:
                        return False
                    db.execute('UPDATE rate_limits SET hits=hits+1 WHERE bucket=?', (bucket,))
                    return True
            db.execute('INSERT INTO rate_limits(bucket,hits,window_started) VALUES(?,?,?) '
                       'ON CONFLICT(bucket) DO UPDATE SET hits=excluded.hits, '
                       'window_started=excluded.window_started', (bucket, 1, now))
            return True
