"""Tests for backend.config.secrets.resolve_secret."""

import os
import logging
from unittest.mock import patch

import pytest

from config.secrets import resolve_secret, _warn_sqlite_fallback


@pytest.fixture(autouse=True)
def clear_lru_cache():
    _warn_sqlite_fallback.cache_clear()
    yield


def test_env_var_takes_precedence():
    with patch.dict(os.environ, {"TEST_KEY": "env-val"}, clear=True):
        with patch("config.secrets.get_setting", return_value="db-val") as mock_get:
            result = resolve_secret("TEST_KEY", "test_settings_key")
            assert result == "env-val"
            mock_get.assert_not_called()


def test_falls_back_to_sqlite_when_env_missing():
    with patch.dict(os.environ, {}, clear=True):
        with patch("config.secrets.get_setting", return_value="db-val") as mock_get:
            result = resolve_secret("TEST_KEY", "test_settings_key")
            assert result == "db-val"
            mock_get.assert_called_once_with("test_settings_key")


def test_returns_none_when_both_missing():
    with patch.dict(os.environ, {}, clear=True):
        with patch("config.secrets.get_setting", return_value=""):
            result = resolve_secret("TEST_KEY", "test_settings_key")
            assert result is None


def test_returns_none_when_env_missing_and_no_settings_key():
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_secret("TEST_KEY")
        assert result is None


def test_logs_warning_on_sqlite_fallback(caplog):
    caplog.set_level(logging.WARNING)
    with patch.dict(os.environ, {}, clear=True):
        with patch("config.secrets.get_setting", return_value="db-val"):
            resolve_secret("TEST_KEY", "test_settings_key")
            assert any("resolved from SQLite" in rec.message for rec in caplog.records)
            assert "TEST_KEY" in caplog.text


def test_no_warning_on_env_var_hit(caplog):
    caplog.set_level(logging.WARNING)
    with patch.dict(os.environ, {"TEST_KEY": "env-val"}, clear=True):
        with patch("config.secrets.get_setting", return_value="db-val"):
            resolve_secret("TEST_KEY", "test_settings_key")
            assert not any("resolved from SQLite" in rec.message for rec in caplog.records)


def test_warn_once_dedup(caplog):
    caplog.set_level(logging.WARNING)
    with patch.dict(os.environ, {}, clear=True):
        with patch("config.secrets.get_setting", return_value="db-val"):
            resolve_secret("TEST_KEY", "test_settings_key")
            resolve_secret("TEST_KEY", "test_settings_key")
            warnings = [r for r in caplog.records if "resolved from SQLite" in r.message]
            assert len(warnings) == 1


def test_different_env_same_settings_key_triggers_separate_warnings():
    _warn_sqlite_fallback.cache_clear()
    with patch.dict(os.environ, {}, clear=True):
        with patch("config.secrets.get_setting", return_value="db-val"):
            resolve_secret("ENV_A", "settings_key")
            resolve_secret("ENV_B", "settings_key")
            assert _warn_sqlite_fallback.cache_info().misses >= 2
