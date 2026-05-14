# AGENTS.md — JustHireMe

## Config Architecture

The config system lives in `backend/config/` with domain-aligned Pydantic schemas:

| Module | Values | Access pattern |
|--------|--------|----------------|
| `config/llm.py` | Provider models, URLs, env key names, timeouts | `settings.llm.timeout_seconds` |
| `config/scraping.py` | Source URLs, timeouts, limits, ATS endpoints | `settings.scraping.timeouts.default_http` |
| `config/scoring.py` | Rubric weights, quality thresholds, taxonomies | `settings.scoring.rubric.role_alignment` |
| `config/generator.py` | PDF defaults, word limits, colors | `settings.generator.word_limits.resume_max` |
| `config/contact.py` | Hunter.io/Proxycurl endpoints, limits | `settings.contact.request_timeout` |
| `config/app.py` | Ghost mode, WS timeout, ports, freshness | `settings.app.ghost_mode.interval_hours` |
| `config/logging.py` | Log level, format, destination | `settings.logging.default_level` |

Usage:
```python
from config import settings, validate_all
# Validation at startup:
errs = validate_all()
# Access values:
settings.scraper.timeout  # typed, validated
```

Resolution hierarchy: CLI `--config-dir` → `JHM_CONFIG_DIR` → XDG → fallback.

### Authority Boundaries

| Owner | Location | Examples |
|-------|----------|----------|
| Developer | `backend/config/*.py` Python modules | Score weights, taxonomies, threshold defaults |
| Operator | Env vars (`JHM_*`, `ANTHROPIC_API_KEY`) | API keys, log level, config dir override |
| User | `data/config/*.yaml` files | Job sources, filters, ghost mode schedule |
| System | SQLite/Kuzu/LanceDB | Ephemeral state, runtime data |

## Branch Rules

- All work branches from `linux-base`
- Feature branches: `feature/short-description`
- Fix branches: `fix/short-description`
- Merge back to `linux-base`, delete branch
- Never push to `upstream`

## Test Commands

```bash
# Run all backend tests:
cd backend && uv run python -m pytest tests/

# Run specific test file:
cd backend && uv run python -m pytest tests/test_regressions.py -v
```

## Backend Logging

The Python backend logs structured lines with correlation IDs to **stderr**.
When running via `npm run tauri dev`, Tauri forwards these to the terminal
with a `[sidecar]` prefix.

| Env var | Purpose | Example |
|---------|---------|---------|
| `JHM_LOG_LEVEL` | Override log level (default: INFO) | `JHM_LOG_LEVEL=DEBUG` |
| `JHM_LOG_FILE` | Enable file logging to path | `JHM_LOG_FILE=/tmp/jhm.log` |

Example to see full structured logs:
```bash
JHM_LOG_LEVEL=DEBUG JHM_LOG_FILE=/tmp/jhm.log npm run tauri dev
# In another terminal:
tail -f /tmp/jhm.log
```

## Current Phase

Phase C (Reliability, Observability & Concurrency) — active.
