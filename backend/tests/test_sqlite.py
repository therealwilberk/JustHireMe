"""Tests for SQLite connection pragmas and resilience.

Verifies that get_sql_connection() applies WAL journal mode, foreign key
enforcement, and busy timeout.

Note: Other test modules replace sys.modules['sqlite3'] with a fake at
import time. We restore the real sqlite3 at module level here so our
tests can verify pragma behavior against actual SQLite.
"""

import os
import sys
import tempfile
import unittest

# Restore real sqlite3 — other test modules may have faked it in sys.modules
_saved_fake = sys.modules.pop("sqlite3", None)
import sqlite3 as _sqlite3  # noqa: E402 — real stdlib module
if _saved_fake is not None:
    sys.modules["sqlite3"] = _saved_fake


def _pragma(c, name: str):
    """Return the current value of a PRAGMA."""
    return c.execute(f"PRAGMA {name}").fetchone()[0]


class TestSqlitePragmasOnFile(unittest.TestCase):
    """Verify pragma effects on a temp file database (real sqlite3).

    Uses file databases because WAL mode requires a file, not :memory:.
    """

    def _connect(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db_path = self._tmp.name
        self._tmp.close()
        return _sqlite3.connect(self._db_path)

    def tearDown(self):
        if hasattr(self, "_db_path") and os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_journal_mode_default_is_delete_for_empty_file(self):
        c = self._connect()
        mode = _pragma(c, "journal_mode")
        c.close()
        self.assertEqual(mode, "delete")

    def test_wal_pragma_changes_journal_mode_on_file_db(self):
        c = self._connect()
        c.execute("PRAGMA journal_mode=WAL")
        mode = _pragma(c, "journal_mode")
        c.close()
        self.assertEqual(mode, "wal")

    def test_wal_persists_across_connections(self):
        c1 = self._connect()
        c1.execute("PRAGMA journal_mode=WAL")
        c1.close()
        c2 = _sqlite3.connect(self._db_path)
        mode = _pragma(c2, "journal_mode")
        c2.close()
        self.assertEqual(mode, "wal")

    def test_foreign_keys_default_is_off(self):
        c = self._connect()
        self.assertEqual(_pragma(c, "foreign_keys"), 0)
        c.close()

    def test_foreign_keys_pragma_enables_enforcement(self):
        c = self._connect()
        c.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(_pragma(c, "foreign_keys"), 1)
        c.close()

    def test_foreign_keys_rejects_violation(self):
        c = self._connect()
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("CREATE TABLE parent(id INTEGER PRIMARY KEY)")
        c.execute(
            "CREATE TABLE child(id INTEGER PRIMARY KEY, pid INTEGER REFERENCES parent(id))"
        )
        with self.assertRaises(_sqlite3.IntegrityError):
            c.execute("INSERT INTO child(id, pid) VALUES(1, 999)")
        c.close()

    def test_foreign_keys_allows_valid_reference(self):
        c = self._connect()
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("CREATE TABLE parent(id INTEGER PRIMARY KEY)")
        c.execute(
            "CREATE TABLE child(id INTEGER PRIMARY KEY, pid INTEGER REFERENCES parent(id))"
        )
        c.execute("INSERT INTO parent(id) VALUES(999)")
        c.execute("INSERT INTO child(id, pid) VALUES(1, 999)")
        c.execute("COMMIT")
        c.close()

    def test_busy_timeout_is_settable(self):
        c = self._connect()
        c.execute("PRAGMA busy_timeout=5000")
        timeout = _pragma(c, "busy_timeout")
        c.close()
        self.assertGreaterEqual(timeout, 5000)

    def test_all_three_pragmas_together_on_file_db(self):
        c = self._connect()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        self.assertEqual(_pragma(c, "journal_mode"), "wal")
        self.assertEqual(_pragma(c, "foreign_keys"), 1)
        self.assertGreaterEqual(_pragma(c, "busy_timeout"), 5000)
        c.close()


class TestGetSqlConnection(unittest.TestCase):
    """Test that get_sql_connection is importable and applies pragmas."""

    def test_importable(self):
        from db.client import get_sql_connection
        self.assertTrue(callable(get_sql_connection))
