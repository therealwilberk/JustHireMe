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

## Remaining India References (Separate Scope)

These files still contain India-specific logic that was part of the old hardcoded job target system. They are NOT modified by the `chore/externalize-job-targets` branch — that branch only removed India from `services/job_targets.py` and `config/app.py`.

| File | What has India | Why not removed |
|------|----------------|-----------------|
| `agents/query_gen.py` | `_india_clause()`, market focus branching in prompt templates | Agent layer — separate effort |
| `agents/help_agent.py` | Help prompt text mentions India presets | Agent layer — separate effort |
| `agents/lead_intel.py` | `if "india" in lower` → "Remote India" | Agent layer — separate effort |
| `config/scoring.py` | Location list includes "india" | Scoring engine — not target config |
| `agents/scoring_engine.py` | Location scoring includes India | Scoring engine — not target config |
| `src/settings/shared.tsx` | `INDIA_SOURCE_PRESET`, market focus toggle | Frontend — separate branch |
| `src/settings/DiscoverySettings.tsx` | India market button, India quick-add buttons | Frontend — separate branch |
| `src/components/OnboardingWizard.tsx` | India dropdown option | Frontend — separate branch |

## Known Issues (Deferred)

### Textarea input bypasses validation

The `job_boards` textarea (frontend → `POST /api/v1/settings`) has no input validation. Entries like `site:opp ("jobs" OR "careers")` pass through `_split_configured_targets()` unscathed. Validation only runs on the new `PUT /api/v1/settings/job-targets` CRUD API. Fix: wire the textarea through validation, or replace it with the CRUD UI (Phase 5: Frontend).

### Stop scan button may not update UI state

`POST /api/v1/scan/stop` force-cancels the running task and releases the ghost lock. Backend returns `{"status": "stopping"}` and broadcasts an `eval_done` WS event. If the button stays stuck, the `AgentOnline` component likely isn't handling the HTTP response or WS event — investigate its state management.
