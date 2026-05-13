import os
import sys
from pathlib import Path
from typing import Optional


def resolve_config_dir(argv: list[str] | None = None) -> Path:
    """
    Resolve config directory using priority hierarchy:

    1. CLI --config-dir PATH  (highest)
    2. JHM_CONFIG_DIR env var
    3. $XDG_CONFIG_HOME/JustHireMe/  (XDG platform convention)
    4. ~/.config/JustHireMe/          (XDG fallback)
    5. ./data/config/                 (local/development fallback)
    """
    cli_path = _from_cli(argv or sys.argv[1:])
    if cli_path:
        return cli_path

    env_path = _from_env()
    if env_path:
        return env_path

    xdg_path = _from_xdg()
    if xdg_path:
        return xdg_path

    return _local_fallback()


def _from_cli(argv: list[str]) -> Optional[Path]:
    for i, arg in enumerate(argv):
        if arg == "--config-dir" and i + 1 < len(argv):
            p = Path(argv[i + 1]).resolve()
            if p.is_dir() or not p.exists():
                return p
    return None


def _from_env() -> Optional[Path]:
    raw = os.environ.get("JHM_CONFIG_DIR")
    if raw:
        return Path(raw).resolve()
    return None


def _from_xdg() -> Optional[Path]:
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_home:
        p = Path(xdg_home) / "JustHireMe"
        if p.is_dir():
            return p.resolve()
    fallback = Path.home() / ".config" / "JustHireMe"
    if fallback.is_dir():
        return fallback.resolve()
    return None


def _local_fallback() -> Path:
    return (Path.cwd() / "data" / "config").resolve()
