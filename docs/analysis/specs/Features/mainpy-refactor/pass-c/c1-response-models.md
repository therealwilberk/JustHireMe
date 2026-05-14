# Pass C1 — Response Models

**Mode:** HITL (per-router verification)
**Branch:** `feature/mainpy-refactor-pass-c`
**Blocked by:** Pass B

---

## Goal

Add `response_model=` to every route so that:
- FastAPI validates outbound payloads against explicit schemas
- OpenAPI spec becomes trustworthy
- Response shape ownership moves from ad hoc route implementations to explicit schema contracts
- Future route extractions become safer (stabilized interface boundaries)

## Core Framing

**`response_model=` is not documentation. It is an active serialization boundary.**

When you wire `response_model=`, FastAPI filters the outbound payload against the model. Fields present in the implementation but absent from the model are **silently dropped**. The model becomes the authoritative contract — the route implementation is allowed to return more, but only the model's fields reach clients.

This means: **schema incompleteness is now behavior-changing.**

The migration strategy treats this as a contract migration, not a cosmetic cleanup.

## Risks

### 1. Silent field dropping (primary risk)

If the model omits a field the route currently returns, that field vanishes from the API response. No error. No warning. Just gone.

**Mitigation:** One router at a time. Run `test_api.py` structured contract assertions after each router. The existing tests (`assert_success_response`, `assert_list_response`, `assert_ok_response`) verify required key presence and types — they will catch missing fields.

### 2. Polymorphic / conditional responses

Routes where the response shape changes based on input or state:
- Success vs error envelopes with different fields
- Optional fields that only appear in certain conditions
- Legacy endpoints with mixed payload structures

**Mitigation:** Use broader transitional models, unions, or discriminated response types rather than forcing one rigid shape. Flag these routes during audit.

### 3. Validation errors at runtime

If a route's implementation violates the response model (wrong type, missing required field), FastAPI raises `ResponseValidationError`. By default this surfaces as a generic 500.

**Mitigation:** Log validation failures explicitly during rollout so they're visible, not silent 500s. Catch `ResponseValidationError` in development and log the full detail.

### 4. Routes that must NOT get `response_model=`

- `StreamingResponse` routes (CSV download, file download) — these return raw bytes
- `FileResponse` routes — binary response
- Redirect responses
- WebSocket routes — they don't use `response_model`
- Custom media type responses

Identify and skip these explicitly.

## Schema Design Principles

### Transitional envelope typing, progressive interior typing

Start with `dict` for complex data payloads, but treat it as a migration layer:

```python
# Transitional (C1):
class LeadResponse(BaseModel):
    ok: bool
    data: dict  # acceptable for now

# Target (future):
class LeadResponse(BaseModel):
    ok: bool
    data: LeadSchema  # typed interior
```

Do not let `dict` fields become permanent architecture. Each `dict` field is a TODO for progressive interior typing.

### `Extra.ignore` is active filtering, not passive

FastAPI's default `Extra.ignore` means the model filters outbound data. It does NOT mean "also include extras from the implementation." The model alone determines shape.

**Define models as strict supersets of current responses:** include every field the route currently returns. Run tests after each router to confirm nothing was dropped.

### Use Literal types for status enums where stable

```python
from typing import Literal

class ScanResponse(BaseModel):
    status: Literal["scanning", "idle", "stopping"]
```

This documents valid values in OpenAPI and catches drift. Only do this for truly stable status strings (not user-facing messages that change freely).

## What to Build

### `schemas/responses.py`

```python
from pydantic import BaseModel
from typing import Any


# ── Status responses ──────────────────────────────────────

class StatusResponse(BaseModel):
    status: str


# ── Scan lifecycle ────────────────────────────────────────

class ScanResponse(StatusResponse):
    pass  # status: "scanning" | "idle" | "stopping"


# ── Leads ─────────────────────────────────────────────────

class LeadsListResponse(BaseModel):
    ok: bool
    leads: list[dict]  # TODO: type interior
    total: int
    offset: int


class LeadDetailResponse(BaseModel):
    ok: bool
    data: dict  # TODO: type interior


# ── Settings ───────────────────────────────────────────────

class SettingsResponse(BaseModel):
    ok: bool
    config: dict  # TODO: type interior


# ── Health ─────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
```

### Routes to skip

| Route | Reason |
|-------|--------|
| `/api/v1/leads/download-csv` | Returns `StreamingResponse` |
| WebSocket at `/ws` | WS protocol, no `response_model` |
| Any redirect | Not JSON |

## Execution Plan

1. Create `schemas/responses.py` with all response models
2. Wire `response_model=` on one router at a time:
   - `routes/misc.py` (lowest risk — health, version)
   - `routes/settings.py`
   - `routes/scan.py`
   - `routes/profile.py`
   - `routes/ingest.py`
   - `routes/actions.py`
   - `routes/leads.py` (highest risk — most routes, polymorphic)
   - `routes/ws.py` (skip — WebSocket)
3. After each router: `uv run python -m pytest tests/ -q --tb=line`

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 300 tests must pass. The existing contract assertions in `test_api.py` are the enforcement infrastructure — they will catch field drops.

## Commit

```
refactor(c1): add response models to all routes
```
