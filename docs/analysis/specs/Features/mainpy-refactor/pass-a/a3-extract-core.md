# Pass A3 — Extract Core Infrastructure

**Lines affected:** 27-41, 178-211
**Target files:** `backend/core/ws_manager.py`, `backend/core/config_constants.py`
**Mode:** AFK

---

## Goal

Move the WebSocket connection manager and app-wide constants into `core/`. These are shared by multiple future modules so they must be extracted first.

---

## What Moves

### To `core/ws_manager.py`

| Item | Lines in main.py |
|------|-----------------|
| `_agent_event_action` function | 172-175 |
| `_CM` class | 178-208 |
| `cm = _CM()` singleton | 211 |

### To `core/config_constants.py`

| Item | Lines in main.py |
|------|-----------------|
| `_log` (logger instance) | 27 |
| `_UP` (startup timestamp) | 36 |
| `_sched` (APScheduler) | 37 |
| `_API_TOKEN` (bearer token) | 38 |
| `_LOCAL_ORIGIN_RE` (CORS regex) | 39 |
| `_bearer` (HTTPBearer scheme) | 40 |

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| `core/ws_manager.py` adds `import json, asyncio, logging` + `from logger import get_logger` | Required by `_CM` |
| `core/config_constants.py` adds `import secrets, re, time, socket` + `from fastapi.security import HTTPBearer` + `from apscheduler.schedulers.asyncio import AsyncIOScheduler` + `from logger import get_logger` + `from config import settings` | Required by constants |
| `main.py` removes the class, function, and constant definitions | Moved to core |
| `main.py` adds `from core.ws_manager import cm, _agent_event_action` | Import from new location |
| `main.py` adds `from core.config_constants import _log, _UP, _sched, _API_TOKEN, _LOCAL_ORIGIN_RE, _bearer` | Import from new location |
| All other modules that import from `main.py` now import from `core/` | No other modules do this currently — `cm` is only used within `main.py` |

**Export exactly as-is.** Same function signatures, same singleton instance, same API.

---

## Verification

```bash
# 1. Compile checks
python -m py_compile backend/main.py
python -m py_compile backend/core/ws_manager.py
python -m py_compile backend/core/config_constants.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line

# 3. App launch smoke test
cd backend && timeout 5 uv run python -m uvicorn main:app --port 9999 || true
```

All three must pass. No test should fail.

---

## Commit

```
refactor(a1): extract core infrastructure to core/ws_manager.py and core/config_constants.py
```
