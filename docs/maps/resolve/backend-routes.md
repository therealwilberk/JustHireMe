# Resolve: backend-routes

Source: `docs/maps/backend-routes.md`
Branch: `fix/resolve-routes`

Files in scope:
- `routes/misc.py` (145 lines)
- `routes/ingest.py` (356 lines)
- `routes/actions.py` (210 lines)
- `routes/leads.py` (404 lines)
- `routes/scan.py` (125 lines)
- `routes/settings.py` (160 lines)
- `routes/ws.py` (59 lines)
- `routes/profile.py` (203 lines)
- `routes/__init__.py` (0 lines)

## Slice strategy

Horizontal by severity: 🔴 → 🔵 → 🟡 → 🟢. 🟣 deferred.

## Pass 1: 🔴 DEAD code removal

| Item | File:Line | Verified | Action |
|------|-----------|----------|--------|
| `HTTPException` import | `misc.py:9` | ✅ `from fastapi import APIRouter, HTTPException` — `HTTPException` never used in file | Remove from import |
| `JSONResponse` import | `misc.py:10` | ✅ `from fastapi.responses import JSONResponse` — never used | Remove entire line |

Ripple: `APIRouter` import on line 9 stays (used by `router = APIRouter(...)`). After removal, line 9 becomes `from fastapi import APIRouter`.

Test: `pytest tests/test_regressions.py tests/test_observability.py -q --tb=short`

## Pass 2: 🔵 HARDCODED → config

### Direct swaps (config key exists)

| Value | File:Line | Config key | Notes |
|-------|-----------|-----------|-------|
| `hours=6` (ghost interval) | `settings.py:95` | `cfg_settings.app.ghost_mode.interval_hours` | Exists in `config/app.py:17`, default `6`. Direct swap: `hours=cfg_settings.app.ghost_mode.interval_hours` |

### New config keys needed

| Value | File:Line | Config key | Notes |
|-------|-----------|-----------|-------|
| `50 * 1024 * 1024` file size | `ingest.py:95` | Add `max_upload_size` to `config/app.py` (new `UploadLimits` model or `AppConfig` field) | Magic number, should be configurable |
| `"selectors_fetched_at": "0"` | `actions.py:182` | Create module-level constant `_SELECTORS_RESET_AT = "0"` | Magic reset string, extract to named constant |
| Provider list `["anthropic", "gemini", "openai", "groq", ...]` | `settings.py:50-51` | Already in `config/llm.py` as `LLMProviderDefaults` model fields | Source of truth is `_KEY_NAMES` dict — the inline list duplicates it |
| `timeout=2.0` heartbeat | `ws.py:49` | Add `heartbeat_interval` to `config/app.py` (WebSocket config section) | Magic number |
| `[:100]` broadcast cap | `scan.py:81` | Add `cleanup_broadcast_limit` to `config/scraping.py` limits | Magic number |

### Domain data (no change)

Seniority strings (`"fresher"`, `"junior"` etc) — domain vocabulary, acceptable as constants.

## Pass 3: 🟡 SUSPECT items

| Item | Verdict |
|------|---------|
| `_annotate_job_lead` in routes | Noted — lives in routes but belongs in services.scout. Deferred. |
| `save_lead` 20+ kwargs in `leads.py` | Noted — brittle pattern. Deferred. |

## 🟣 Deferred (structural refactor)

| Item | Reason |
|------|--------|
| `help_chat` duplicate route (misc.py + scan.py) | Needs route deduplication — structural |
| Private-name imports (scan.py, settings.py) | Needs public API on services modules — structural |

## Verification

```bash
cd backend && uv run python -c "from main import app; print(len(app.routes))"
cd backend && uv run python -m pytest tests/ -q --tb=short
```
