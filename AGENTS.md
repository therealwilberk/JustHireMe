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

`chore/externalize-job-targets` — active. Moving hardcoded job board lists to user-configurable settings. See `docs/plans/externalize-job-targets.md`.

## Resolve Workflow (per module)

1. **Branch** — `fix/<slug>` from `linux-base`
2. **Resolve plan** — write from `docs/maps/resolve/TEMPLATE.md`, passes by severity (🔴→🔵→🟡)
3. **Verify plan against source** — read actual code files first. Confirm every flagged item is real.
4. **TodoWrite** — before any code
5. **Execute** — pass by pass, commit per pass
6. **Re-check every change** — test viability, ripple effects, doc updates, no "domain data" false dismissals
7. **No-code review** — review pass over all changes before claiming done
8. **Update map** — `docs/maps/<module>.md` file inventory and flags
9. **Delete resolve** — `git rm docs/maps/resolve/<module>.md`
10. **Merge & delete** — `--no-ff` to `linux-base`, delete branch

## Deferred Items

All deferred/backlog items are documented in `docs/deferred/` — one file per topic with status badges. Current items:

| File | Status |
|------|--------|
| `docs/deferred/os-keychain.md` | Pending |
| `docs/deferred/upstream-merge-tracking.md` | Pending |
| `docs/deferred/cors-origin-regex-config.md` | Pending |
| `docs/deferred/settings-dual-path.md` | Pending |
| `docs/deferred/startup-no-config-test.md` | Pending |
| `docs/deferred/api-key-encryption.md` | Pending |
| `docs/deferred/placeholder-phone-in-generator.md` | Pending |
| `docs/deferred/dependency-pins.md` | Pending |
| `docs/deferred/textarea-validation-gap.md` | Pending |
| `docs/deferred/stop-scan-ui-bug.md` | Partial |
| `docs/deferred/india-references-cleanup.md` | Pending |
| `docs/deferred/frontend-component-tests.md` | Partial |
| `docs/deferred/ke-scrapers.md` | Pending (separate project) |
