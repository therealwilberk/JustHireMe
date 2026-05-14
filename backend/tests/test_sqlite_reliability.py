"""Tests for SQLite operational configuration and concurrency resilience.

Verifies that get_sql_connection() provides a known-good state (WAL,
foreign_keys=ON, busy_timeout=5000) and that the database layer handles
contention predictably — overlapping readers/writers, transaction
isolation, and lock timeout behavior.

Important: These tests use the real sqlite3 module, not the test fake,
because pragma effects and contention semantics cannot be verified
against a mock.  Threaded tests create connections inside each thread
(cf. Python's check_same_thread restriction).
"""

import os
import sys
import tempfile
import threading
import time
import unittest

_saved_fake = sys.modules.pop("sqlite3", None)
import sqlite3 as _sqlite3
if _saved_fake is not None:
    sys.modules["sqlite3"] = _saved_fake


def _pragma_val(c, name: str):
    return c.execute(f"PRAGMA {name}").fetchone()[0]


class TestGetSqlConnectionPragmas(unittest.TestCase):
    """Verify that get_sql_connection() applies standard pragmas.

    Patches db.client._sq and db.client.sql so that get_sql_connection()
    opens a real SQLite connection on a temp file.
    """

    def setUp(self):
        import db.client as _dc
        self._dc = _dc
        self._saved_sq = _dc._sq
        self._saved_sql = _dc.sql
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db_path = self._tmp.name
        self._tmp.close()
        _dc._sq = _sqlite3
        _dc.sql = self._db_path

    def tearDown(self):
        self._dc._sq = self._saved_sq
        self._dc.sql = self._saved_sql
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def _assert_pragmas(self, c):
        self.assertEqual(_pragma_val(c, "journal_mode"), "wal")
        self.assertEqual(_pragma_val(c, "foreign_keys"), 1)
        self.assertGreaterEqual(_pragma_val(c, "busy_timeout"), 5000)

    def test_applies_wal(self):
        c = self._dc.get_sql_connection()
        try:
            self.assertEqual(_pragma_val(c, "journal_mode"), "wal")
        finally:
            c.close()

    def test_applies_foreign_keys(self):
        c = self._dc.get_sql_connection()
        try:
            self.assertEqual(_pragma_val(c, "foreign_keys"), 1)
        finally:
            c.close()

    def test_applies_busy_timeout(self):
        c = self._dc.get_sql_connection()
        try:
            self.assertGreaterEqual(_pragma_val(c, "busy_timeout"), 5000)
        finally:
            c.close()

    def test_all_pragmas_applied_together(self):
        c = self._dc.get_sql_connection()
        try:
            self._assert_pragmas(c)
        finally:
            c.close()

    def test_every_call_returns_configured_connection(self):
        c1 = self._dc.get_sql_connection()
        c2 = self._dc.get_sql_connection()
        try:
            self._assert_pragmas(c1)
            self._assert_pragmas(c2)
        finally:
            c1.close()
            c2.close()


class TestSqliteContentionBase(unittest.TestCase):
    """Base for contention tests — temp file db with standard pragmas."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db_path = self._tmp.name
        self._tmp.close()

    def tearDown(self):
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def _make_conn(self, busy_timeout: int = 100):
        c = _sqlite3.connect(self._db_path)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute(f"PRAGMA busy_timeout={busy_timeout}")
        return c

    def _prepare_table(self, c, name: str = "ctest"):
        c.execute(f"CREATE TABLE IF NOT EXISTS {name} (k INTEGER PRIMARY KEY, v TEXT)")
        c.execute(f"DELETE FROM {name}")
        c.commit()


class TestWALSnapshotIsolation(TestSqliteContentionBase):
    """WAL mode guarantees snapshot isolation for readers."""

    def test_reader_does_not_see_uncommitted_writes(self):
        cw = self._make_conn()
        cr = self._make_conn()
        try:
            self._prepare_table(cw)
            cw.execute("BEGIN")
            cw.execute("INSERT INTO ctest (k, v) VALUES (1, 'uncommitted')")

            rows = cr.execute("SELECT * FROM ctest").fetchall()
            self.assertEqual(len(rows), 0,
                             "WAL snapshot isolation: reader must not see uncommitted write")

            cw.execute("COMMIT")
        finally:
            cw.close()
            cr.close()

    def test_reader_sees_committed_data_after_commit(self):
        cw = self._make_conn()
        cr = self._make_conn()
        try:
            self._prepare_table(cw)
            cw.execute("INSERT INTO ctest (k, v) VALUES (1, 'persistent')")
            cw.commit()

            rows = cr.execute("SELECT * FROM ctest").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1], "persistent")
        finally:
            cw.close()
            cr.close()

    def test_reader_reads_snapshot_from_moment_of_first_read(self):
        cw = self._make_conn()
        cr = self._make_conn()
        try:
            self._prepare_table(cw)
            cw.execute("INSERT INTO ctest (k, v) VALUES (1, 'initial')")
            cw.commit()

            rows_before = cr.execute("SELECT * FROM ctest").fetchall()
            self.assertEqual(len(rows_before), 1)

            cw.execute("INSERT INTO ctest (k, v) VALUES (2, 'late')")
            cw.commit()

            rows_after = cr.execute("SELECT * FROM ctest").fetchall()
            self.assertEqual(len(rows_after), 2,
                             "New reader sees committed data after writer commits")
        finally:
            cw.close()
            cr.close()

    def test_concurrent_readers_are_not_blocked_by_other_readers(self):
        cw = self._make_conn()
        try:
            self._prepare_table(cw)
            for i in range(10):
                cw.execute("INSERT INTO ctest (k, v) VALUES (?, 'x')", (i,))
            cw.commit()

            results = []
            lock = threading.Lock()

            def read_all():
                c = _sqlite3.connect(self._db_path)
                c.execute("PRAGMA journal_mode=WAL")
                rows = c.execute("SELECT count(*) FROM ctest").fetchone()[0]
                with lock:
                    results.append(rows)
                c.close()

            threads = [threading.Thread(target=read_all) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(len(results), 5)
            self.assertTrue(all(r == 10 for r in results),
                            "All concurrent readers must see same data")
        finally:
            cw.close()

    def test_reader_not_blocked_by_concurrent_writer(self):
        cw = self._make_conn(2000)
        try:
            self._prepare_table(cw)
            cw.execute("INSERT INTO ctest (k, v) VALUES (1, 'before')")
            cw.commit()

            reader_done = threading.Event()
            reader_rows = []

            def read():
                c = _sqlite3.connect(self._db_path)
                c.execute("PRAGMA journal_mode=WAL")
                rows = c.execute("SELECT * FROM ctest").fetchall()
                reader_rows.extend(rows)
                reader_done.set()
                c.close()

            t_reader = threading.Thread(target=read)
            cw.execute("BEGIN IMMEDIATE")
            cw.execute("INSERT INTO ctest (k, v) VALUES (2, 'during')")
            t_reader.start()

            ok = reader_done.wait(timeout=3)
            self.assertTrue(ok, "Reader must not be blocked by concurrent writer in WAL mode")

            self.assertEqual(len(reader_rows), 1,
                             "WAL: reader sees snapshot from before writer's transaction")

            cw.execute("COMMIT")
        finally:
            cw.close()


class TestWriterContention(TestSqliteContentionBase):
    """Writer lock contention and busy_timeout behavior."""

    def test_busy_timeout_zero_raises_immediate_busy(self):
        c1 = _sqlite3.connect(self._db_path)
        c1.execute("PRAGMA busy_timeout=0")
        c2 = _sqlite3.connect(self._db_path)
        c2.execute("PRAGMA busy_timeout=0")
        try:
            c1.execute("CREATE TABLE IF NOT EXISTS nobusy (k INTEGER PRIMARY KEY)")
            c1.execute("DELETE FROM nobusy")
            c1.commit()

            c1.execute("BEGIN IMMEDIATE")
            c1.execute("INSERT INTO nobusy (k) VALUES (1)")

            start = time.time()
            with self.assertRaises(_sqlite3.OperationalError) as ctx:
                c2.execute("INSERT INTO nobusy (k) VALUES (2)")
            elapsed = time.time() - start

            self.assertLess(elapsed, 0.2,
                            "With busy_timeout=0, writer must fail immediately, not wait")
            self.assertIn("locked", str(ctx.exception).lower())
        finally:
            c1.execute("ROLLBACK")
            c1.close()
            c2.close()

    def test_python_default_busy_timeout_is_5000(self):
        c = _sqlite3.connect(self._db_path)
        try:
            self.assertEqual(_pragma_val(c, "busy_timeout"), 5000,
                             "Python sqlite3 defaults to busy_timeout=5000")
        finally:
            c.close()

    def test_writer_with_busy_timeout_waits_then_succeeds(self):
        cw_lock = threading.Lock()
        cw_lock.acquire()

        writer1_result = []
        writer2_result = []

        def writer1():
            c = _sqlite3.connect(self._db_path)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=3000")
            c.execute("CREATE TABLE IF NOT EXISTS wt (k INTEGER PRIMARY KEY, v TEXT)")
            c.execute("DELETE FROM wt")
            c.commit()

            c.execute("BEGIN IMMEDIATE")
            c.execute("INSERT INTO wt (k, v) VALUES (1, 'first')")
            cw_lock.release()
            time.sleep(0.3)
            c.execute("COMMIT")
            c.close()
            writer1_result.append("ok")

        def writer2():
            cw_lock.acquire()
            cw_lock.release()
            c = _sqlite3.connect(self._db_path)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=3000")

            start = time.time()
            try:
                c.execute("INSERT INTO wt (k, v) VALUES (2, 'second')")
                c.commit()
                elapsed = time.time() - start
                writer2_result.append(("ok", elapsed))
            except Exception as e:
                writer2_result.append(("error", str(e)))
            c.close()

        t1 = threading.Thread(target=writer1)
        t2 = threading.Thread(target=writer2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(writer1_result[0], "ok")
        _, elapsed = writer2_result[0]
        self.assertEqual(writer2_result[0][0], "ok",
                         f"Writer with busy_timeout should succeed: {writer2_result[0]}")
        self.assertGreaterEqual(elapsed, 0.1,
                                "Writer2 should have waited for the lock")

    def test_short_busy_timeout_expires_and_writer_fails(self):
        cw_lock = threading.Lock()
        cw_lock.acquire()

        writer1_result = []
        writer2_result = []

        def writer1():
            c = _sqlite3.connect(self._db_path)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=50")
            c.execute("CREATE TABLE IF NOT EXISTS wt2 (k INTEGER PRIMARY KEY, v TEXT)")
            c.execute("DELETE FROM wt2")
            c.commit()

            c.execute("BEGIN IMMEDIATE")
            c.execute("INSERT INTO wt2 (k, v) VALUES (1, 'first')")
            cw_lock.release()
            time.sleep(1.0)
            c.execute("COMMIT")
            c.close()
            writer1_result.append("ok")

        def writer2():
            cw_lock.acquire()
            cw_lock.release()
            c = _sqlite3.connect(self._db_path)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=50")

            start = time.time()
            try:
                c.execute("INSERT INTO wt2 (k, v) VALUES (2, 'second')")
                c.commit()
                elapsed = time.time() - start
                writer2_result.append(("ok", elapsed))
            except _sqlite3.OperationalError as e:
                elapsed = time.time() - start
                writer2_result.append(("busy", elapsed, str(e)))
            c.close()

        t1 = threading.Thread(target=writer1)
        t2 = threading.Thread(target=writer2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(writer1_result[0], "ok")
        status, elapsed = writer2_result[0][0], writer2_result[0][1]
        if status == "ok":
            self.fail("Expected busy_timeout=50ms to expire before writer1 releases "
                      f"the lock (1s hold), got success after {elapsed:.2f}s")
        elif status == "busy":
            self.assertGreaterEqual(elapsed, 0.04,
                                    "Should have waited some time before giving up")
            self.assertLess(elapsed, 2.0,
                            "Should fail before writer1 releases (~1000ms)")

    def test_rollback_reverses_all_changes_in_transaction(self):
        c = self._make_conn()
        try:
            self._prepare_table(c)
            c.execute("INSERT INTO ctest (k, v) VALUES (1, 'will-commit')")
            c.execute("INSERT INTO ctest (k, v) VALUES (2, 'will-rollback')")
            c.execute("INSERT INTO ctest (k, v) VALUES (3, 'also-rollback')")

            c.execute("DELETE FROM ctest WHERE k = 2")

            c.execute("ROLLBACK")

            rows = c.execute("SELECT * FROM ctest").fetchall()
            self.assertEqual(len(rows), 0, "ROLLBACK must undo all changes in transaction")
        finally:
            c.close()

    def test_autocommit_rollback_on_disconnect(self):
        c = self._make_conn()
        try:
            self._prepare_table(c)
            c.execute("BEGIN")
            c.execute("INSERT INTO ctest (k, v) VALUES (1, 'lost-on-close')")
            c.close()

            c2 = self._make_conn()
            try:
                rows = c2.execute("SELECT * FROM ctest").fetchall()
                self.assertEqual(len(rows), 0,
                                 "Uncommitted transaction must be rolled back on close")
            finally:
                c2.close()
        except Exception:
            c.close()
            raise


class TestConnectionConsistency(unittest.TestCase):
    """Every database entry point must use get_sql_connection()."""

    def test_no_direct_sq_connect_outside_get_sql_connection(self):
        import db.client as dc
        import ast, inspect

        source = inspect.getsource(dc)
        tree = ast.parse(source)

        class _DirectConnectFinder(ast.NodeVisitor):
            def __init__(self):
                self.found: list[int] = []

            def visit_Call(self, node):
                if (isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "_sq"
                        and node.func.attr == "connect"):
                    self.found.append(node.lineno)
                self.generic_visit(node)

        finder = _DirectConnectFinder()
        finder.visit(tree)

        in_get_sql_connection = False
        allowed_lines = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_sql_connection":
                in_get_sql_connection = True
                allowed_lines = list(range(node.lineno, node.end_lineno + 1))
                break

        violations = [ln for ln in finder.found if ln not in allowed_lines]
        self.assertEqual(
            violations, [],
            f"Direct _sq.connect() calls outside get_sql_connection() at lines: {violations}"
        )


class TestForeignKeyEnforcement(TestSqliteContentionBase):
    """Referential integrity under concurrent operations."""

    def test_fk_violation_in_transaction_is_rolled_back(self):
        c = self._make_conn()
        try:
            c.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            c.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, pid INTEGER REFERENCES parent(id))")
            c.execute("INSERT INTO parent (id) VALUES (1)")
            c.commit()

            with self.assertRaises(_sqlite3.IntegrityError):
                c.execute("INSERT INTO child (id, pid) VALUES (100, 999)")
            c.commit()

            rows = c.execute("SELECT * FROM child").fetchall()
            self.assertEqual(len(rows), 0, "FK violation must not leave partial data")
        finally:
            c.close()

    def test_fk_concurrent_write_with_busy_timeout(self):
        cw_lock = threading.Lock()
        cw_lock.acquire()

        results = []

        def writer1():
            c = _sqlite3.connect(self._db_path)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=3000")
            c.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            c.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, pid INTEGER REFERENCES parent(id))")
            c.execute("INSERT INTO parent (id) VALUES (1)")
            c.commit()

            c.execute("BEGIN IMMEDIATE")
            c.execute("INSERT INTO parent (id) VALUES (2)")
            cw_lock.release()
            time.sleep(0.3)
            c.execute("COMMIT")
            c.close()
            results.append("ok")

        def writer2():
            cw_lock.acquire()
            cw_lock.release()
            c = _sqlite3.connect(self._db_path)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=3000")
            try:
                c.execute("INSERT INTO child (id, pid) VALUES (1, 2)")
                c.commit()
                results.append("ok")
            except Exception as e:
                results.append(str(e))
            c.close()

        t1 = threading.Thread(target=writer1)
        t2 = threading.Thread(target=writer2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(results, ["ok", "ok"],
                         "Valid FK insert with busy_timeout must succeed after commit")
