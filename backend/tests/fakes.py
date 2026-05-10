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
    def executescript(self, *_args, **_kwargs):
        return self

    def execute(self, *_args, **_kwargs):
        return self

    def fetchone(self):
        return None

    def fetchall(self):
        return []

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


def _install_storage_fakes():
    """Replace storage backends with fakes. Must call before importing any backend module."""
    mock.patch.object(os, "makedirs", return_value=None).start()
    sys.modules.setdefault(
        "kuzu",
        types.SimpleNamespace(
            Database=lambda _path: object(),
            Connection=lambda _db: _FakeConnection(),
        ),
    )
    sys.modules["sqlite3"] = types.SimpleNamespace(
        connect=lambda _path: _FakeSqlConnection()
    )
    sys.modules.setdefault(
        "lancedb",
        types.SimpleNamespace(
            LanceDBConnection=_FakeVectorStore,
            connect=lambda _path: _FakeVectorStore(),
        ),
    )
