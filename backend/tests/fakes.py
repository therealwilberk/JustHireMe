import os
import sys
import types
from unittest import mock


class _FakeResult:
    def has_next(self):
        return False

    def get_next(self):
        return [0]


class _FakeConnection:
    def execute(self, *_args, **_kwargs):
        return _FakeResult()


class _FakeSqlConnection:
    _store: dict[str, list[tuple]] = {}

    def executescript(self, *_args, **_kwargs):
        return self

    def execute(self, sql: str, params: tuple = ()):
        upper = sql.upper()
        if "INSERT" in upper and "INTO SETTINGS" in upper:
            key, val = params
            tbl = self._store.setdefault("settings", [])
            for i, (k, _) in enumerate(tbl):
                if k == key:
                    tbl[i] = (key, val)
                    break
            else:
                tbl.append((key, val))
        elif upper.startswith("SELECT") and "FROM SETTINGS" in upper:
            rows = self._store.get("settings", [])
            if "WHERE KEY=?" in upper:
                key = params[0]
                self._result = [r for r in rows if r[0] == key]
            else:
                self._result = rows
        return self

    def fetchone(self):
        return self._result[0] if getattr(self, "_result", None) else None

    def fetchall(self):
        return self._result if getattr(self, "_result", None) else []

    def commit(self):
        return None

    def close(self):
        return None


class _FakeVectorStore:
    def list_tables(self):
        return []

    def create_table(self, *_args, **_kwargs):
        return None

    def open_table(self, *_args, **_kwargs):
        return self

    def add(self, *_args, **_kwargs):
        return None


class _FakeSemanticSearch:
    def __init__(self, rows):
        self.rows = list(rows)
        self._limit = len(self.rows)

    def metric(self, *_args, **_kwargs):
        return self

    def where(self, clause, *_args, **_kwargs):
        self.rows = [row for row in self.rows if f"'{row['id']}'" in clause]
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def to_list(self):
        return self.rows[: self._limit]


class _FakeSemanticTable:
    def __init__(self, rows):
        self.rows = rows

    def search(self, *_args, **_kwargs):
        return _FakeSemanticSearch(self.rows)


class _FakeSemanticStore:
    def __init__(self, tables):
        self.tables = tables

    def list_tables(self):
        return list(self.tables)

    def open_table(self, name):
        return _FakeSemanticTable(self.tables[name])


_SQLITE_FAKE = types.SimpleNamespace(
    connect=lambda _path: _FakeSqlConnection()
)


def _install_storage_fakes(*, use_real_sqlite: bool = False):
    """Replace storage backends with fakes. Must call before importing any backend module.

    Args:
        use_real_sqlite: If True, don't fake sqlite3 — uses real SQLite DB at
                         the path resolved by db.client.data_base(). The caller
                         must ensure JHM_APP_DATA_DIR points to a writable temp dir
                         and that the directory exists before importing backend modules.
                         Kuzu and LanceDB are still faked.

    By default (use_real_sqlite=False), patches os.makedirs and stubs kuzu, sqlite3,
    and lancedb in sys.modules so their imports resolve to fakes.
    """
    if not use_real_sqlite:
        mock.patch.object(os, "makedirs", return_value=None).start()
    sys.modules.setdefault(
        "kuzu",
        types.SimpleNamespace(
            Database=lambda _path: object(),
            Connection=lambda _db: _FakeConnection(),
        ),
    )
    if not use_real_sqlite:
        sys.modules["sqlite3"] = _SQLITE_FAKE
    sys.modules.setdefault(
        "lancedb",
        types.SimpleNamespace(
            LanceDBConnection=_FakeVectorStore,
            connect=lambda _path: _FakeVectorStore(),
        ),
    )
