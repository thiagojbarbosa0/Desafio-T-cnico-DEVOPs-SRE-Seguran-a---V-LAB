"""SQLite utility for the optional course blueprint (disabled by default)."""
import os
from pathlib import Path
import sqlite3

DB_PATH = Path(os.environ.get("COURSESPHERE_COURSES_DB", Path(__file__).parent / "data" / "courses.sqlite3"))

def execute_query(query, parameters=()):
    """Return materialized rows, never a cursor referring to a closed connection."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor=conn.execute(query, tuple(parameters))
        return [dict(row) for row in cursor.fetchall()] if cursor.description else []
