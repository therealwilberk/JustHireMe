# Pass A9 — Clean Up main.py

**Lines affected:** entire file rewrite
**Target:** `main.py` under 150 lines
**Mode:** HITL

---

## Goal

Strip `main.py` down to the minimal app entrypoint. After all extractions, it should contain only:

1. Top-level imports (routers, core modules, FastAPI components)
2. `app = FastAPI(lifespan=lifespan)`
3. Middleware registrations (CORS, correlation context, auth)
4. `app.include_router(...)` for each router
5. `lifespan` function (config validation, scheduler start/stop)
6. `if __name__ == "__main__"` entrypoint

---

## Expected `main.py` Structure

```python
import asyncio
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from core.config_constants import _log, _UP, _sched, _API_TOKEN, _LOCAL_ORIGIN_RE, _bearer
from core.ws_manager import cm
from log_context import new_context, set_context, reset_context
from routes import misc, settings, leads, profile, scan, ingest, actions, ws


app = FastAPI(title="JustHireMe", version="0.1.0", lifespan=lifespan)

app.add_middleware(...)
app.add_middleware(...)
app.add_middleware(...)

app.include_router(misc.router)
app.include_router(settings.router)
app.include_router(leads.router)
app.include_router(profile.router)
app.include_router(scan.router)
app.include_router(ingest.router)
app.include_router(actions.router)
app.include_router(ws.router)


async def lifespan(app: FastAPI):
    _validate_config_on_startup()
    _log_startup_secret_diagnostics()
    if _sched.get_job("ghost"):
        _sched.remove_job("ghost")
    _sched.add_job(_ghost_tick, "interval", hours=6, id="ghost")
    _sched.start()
    _log.info("FastAPI live.")
    yield
    _sched.shutdown(wait=False)
    _log.info("FastAPI shutdown.")
```

**Note:** `_validate_config_on_startup` and `_log_startup_secret_diagnostics` must stay in `main.py` or move to `core/` — they're startup-only and not used by services. Decision below.

---

## Open Decision

**Where do `_validate_config_on_startup` and `_log_startup_secret_diagnostics` live?**

Option A: Move to `core/startup.py` — cleaner separation, keeps main.py truly minimal
Option B: Leave in `main.py` — they're only called once at startup, no benefit to moving

(Arise during HITL review.)

---

## What Changes

| Change | Reason |
|--------|--------|
| Remove all extracted handler code | Now in routers |
| Remove all extracted service functions | Now in services/ |
| Remove all extracted schema definitions | Now in schemas/ |
| Add router imports + `app.include_router(...)` calls | Wire up the modular structure |
| Ensure `lifespan` references `_ghost_tick` from `services/ghost.py` | Cross-module import |

---

## Verification

```bash
# 1. Compile check
python -m py_compile backend/main.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line

# 3. Full app smoke test
cd backend && timeout 10 uv run python -m uvicorn main:app --port 9999 &

# Test routes
curl http://127.0.0.1:9999/health
curl http://127.0.0.1:9999/api/v1/leads
curl http://127.0.0.1:9999/api/v1/profile
curl http://127.0.0.1:9999/api/v1/settings
# ... key routes respond with 200

kill %1 2>/dev/null || true
```

---

## Commit

```
refactor(a1): main.py reduced to app entrypoint under 150 lines
```
