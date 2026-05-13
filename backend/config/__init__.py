from types import SimpleNamespace
from pathlib import Path

from . import llm, scraping, scoring, generator, contact, app, logging as cfg_logging
from .resolver import resolve_config_dir

_config_dir: Path | None = None


def init_config_dir(argv: list[str] | None = None) -> Path:
    global _config_dir
    if _config_dir is None:
        _config_dir = resolve_config_dir(argv)
    return _config_dir


def get_config_dir() -> Path:
    if _config_dir is None:
        return init_config_dir()
    return _config_dir


def validate_all() -> list[str]:
    errors: list[str] = []
    domains = {
        "llm": llm.config,
        "scraping": scraping.config,
        "scoring": scoring.config,
        "generator": generator.config,
        "contact": contact.config,
        "app": app.config,
        "logging": cfg_logging.config,
    }
    for name, cfg in domains.items():
        try:
            cfg.model_rebuild()
            cfg.model_validate(cfg.model_dump(), strict=False)
        except Exception as exc:
            errors.append(f"config.{name}: {exc}")
    return errors


settings = SimpleNamespace(
    llm=llm.config,
    scraping=scraping.config,
    scoring=scoring.config,
    generator=generator.config,
    contact=contact.config,
    app=app.config,
    logging=cfg_logging.config,
)
