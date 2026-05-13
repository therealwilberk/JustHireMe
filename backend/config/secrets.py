"""Secret resolution: env var preferred, SQLite fallback with deprecation."""

import os
import logging
from functools import lru_cache
from db.client import get_setting

_log = logging.getLogger(__name__)


def resolve_secret(
    env_var_name: str,
    settings_key: str | None = None,
    warn_once: bool = True,
) -> str | None:
    """Resolve a secret. Checks env var first, then SQLite (deprecated).

    Resolution order:
    1. os.environ[env_var_name] — returned immediately, no warning
    2. get_setting(settings_key) — returned with WARN-level deprecation log
    3. Neither found — returns None

    When warn_once=True, each (env_var_name, settings_key) pair is logged
    at most once per process lifetime.
    """
    env_val = os.environ.get(env_var_name)
    if env_val:
        return env_val

    if settings_key:
        db_val = get_setting(settings_key)
        if db_val:
            if warn_once:
                _warn_sqlite_fallback(env_var_name, settings_key)
            else:
                _log.warning(
                    "Secret '%s' resolved from SQLite (deprecated). "
                    "Set %s environment variable instead.",
                    settings_key, env_var_name,
                )
            return db_val

    return None


@lru_cache(maxsize=None)
def _warn_sqlite_fallback(env_var_name: str, settings_key: str) -> None:
    """Warn once per (env, settings_key) pair to avoid log spam."""
    _log.warning(
        "Secret '%s' resolved from SQLite (deprecated). "
        "Set %s environment variable instead.",
        settings_key, env_var_name,
    )
