# Pass C1 — Response Models

**Mode:** HITL (per-router verification)
**Branch:** `feature/mainpy-refactor-pass-c`
**Blocked by:** Pass B

---

## Goal

Add `response_model=` to every route so that:
- FastAPI documents the return type in OpenAPI
- Response shape is validated at the framework level
- Clients get a typed contract

## Risk

**`response_model=` strips extra fields by default.** If a route returns data that isn't in the model, it gets silently dropped. This is the #1 risk — the response changes shape and tests don't cover all fields.

### Mitigation strategy

1. **Define response models that are *strict supersets* of current responses.** Use `Extra.forbid` would break things — use the default `Extra.ignore` but make sure the model includes all known fields.
2. **Run existing API tests before and after** — `test_api.py` has structured contract assertions (`assert_success_response`, `assert_list_response`, `assert_ok_response`). If they pass after wiring `response_model=`, the models are correct.
3. **One router at a time** — wire models to one router, run tests, verify. Don't batch all routers.

## What to Build

### `schemas/responses.py`

Define per-route response models. Use `BaseModel` with all known response fields:

```python
from pydantic import BaseModel
from typing import Any


class HealthResponse(BaseModel):
    status: str
    version: str


class ScanResponse(BaseModel):
    status: str


class StopScanResponse(BaseModel):
    status: str  # "idle" | "stopping"


class LeadsListResponse(BaseModel):
    ok: bool
    leads: list[dict]
    total: int
    offset: int
```

**Important design choice:** Do NOT use `response_model_exclude_unset=True` — we want to explicitly assert field presence. Just define the shapes as they already are. If a model is missing a field, the test will catch it (the field stops appearing in the response).

### Key patterns per route category

**Simple status responses** (`/scan`, `/scan/stop`, `/leads/reevaluate`, etc.):
```python
class StatusResponse(BaseModel):
    status: str
```

**List responses** (`/leads`, leads filtering, etc.):
```python
class LeadsResponse(BaseModel):
    ok: bool
    leads: list[dict]
    total: int
    offset: int
```

**Detail/CRUD responses** (single lead, profile, settings):
```python
class LeadDetailResponse(BaseModel):
    ok: bool
    data: dict  # or a typed Lead schema

class SettingsResponse(BaseModel):
    ok: bool
    config: dict
```

**CSV responses** — these return `StreamingResponse` with `text/csv` content-type. Don't add `response_model=` to CSV routes (they return raw bytes).

## Execution Plan

1. Create `schemas/responses.py` with all response models
2. Wire `response_model=` on one router at a time:
   - `routes/misc.py` (health, version)
   - `routes/settings.py`
   - `routes/scan.py`
   - `routes/leads.py`
   - `routes/profile.py`
   - `routes/ingest.py`
   - `routes/actions.py`
   - `routes/ws.py` (WebSocket routes don't use response_model)
3. After each router: run `uv run python -m pytest tests/ -q --tb=line`

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 300 tests must pass.

## Commit

```
refactor(c1): add response models to all routes
```
