# Pass C3 — Post-Refactor Test Plan

**Goal:** Cover the architectural boundaries introduced by the refactor. Not filler — tests that would catch real regressions.

**Branch:** separate `feature/mainpy-refactor-pass-c-tests` (after merging pass-c)

---

## What Needs Testing

### 1. ScanManager State Machine (`services/scanner.py`)

The ScanManager class is a lifecycle state machine with concurrency and exclusivity semantics — not "just a utility." The invariants that matter operationally:

- no overlapping scans
- no ghost/scan contamination
- idle behavior correctness
- task lifecycle integrity

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| `start_scan()` while ghost lock held → 409 | Guard missed, ghost lock not checked | High |
| `start_scan()` while scan already running → 409 | Double-scan allowed | High |
| `stop_scan()` when idle → `{"status": "idle"}` | `None.done()` crash | High |
| `start_reevaluate()` while ghost lock held → 409 | Cross-contamination of lock state | Medium |
| `start_reevaluate()` while scan running → 409 | Allowed concurrent scan + reevaluate | High |
| `is_scanning()` when task not started → False | Checks None.done() | Medium |
| Concurrent `start_scan()` + `stop_scan()` race | Event.set() + create_task ordering | Medium |

**Test strategy:** Unit test the class directly with real in-memory behavior. State-machine tests should avoid mocks — lock semantics, task lifecycle, and transition correctness are exactly the things mocks tend to hide.

**Framework:** `IsolatedAsyncioTestCase` (not `asyncio.run()` inside `TestCase` — that pattern becomes fragile with nested event loops, locks, and cancellations).

**File:** `tests/test_scan_manager.py`

### 2. GhostService Phase Contracts (`services/ghost.py`)

The 139-line `_ghost_tick_impl` was split into 7 named phase methods. Phase methods are decomposition artifacts — their exact structure may evolve. The real protected contracts are:

- **What each phase consumes** (input contract)
- **What each phase produces** (output contract)  
- **Orchestration sequencing** (run() order guarantees)
- **Side-effect boundaries** (each phase's external effects)

Tests should validate these contracts, not the internal method names or decomposition shape.

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| `_phase_preflight` returns `None` when ghost mode off | Skip logic wrong | Medium |
| `_phase_eval` returns leads with score >= 85 only | Filter threshold wrong | Medium |
| `_phase_apply` respects `auto_apply` gate before submitting | Gate logic bypassed | Medium |
| `run()` orchestrates phases in correct order | Phase sequencing changed | High |

**Test strategy:** Use `IsolatedAsyncioTestCase`. Mock the slow dependencies (`get_settings`, `get_profile`), instantiate `GhostService(scan_manager)`, call individual phase methods with known inputs, assert known outputs. Verify `run()` sequencing by mocking side-effect boundaries and asserting call order.

**File:** `tests/test_ghost_service.py`

### 3. Response Model Completeness (`schemas/responses.py`)

**This is the highest-value suite.** `response_model=` is an active serialization boundary — it silently strips fields not in the model. Most teams never test this explicitly, meaning API contracts slowly drift without anyone realizing fields are disappearing.

The approach: re-serialize the route's actual response through its model, then compare. If the model drops a field the route returns, the test catches the mismatch.

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| Every route's response model is a superset of actual response | Silent field drop | **Critical** |
| Routes with `response_model=dict[str, Any]` accept any shape | Overly permissive | Medium |
| CSV/FileResponse routes are NOT wired with response_model | Binary content corrupted | High |

**Future direction:** Auto-derive expected fields from `route.response_model` introspection rather than maintaining manual `known = {...}` sets. That way the suite scales with the API automatically. Manual sets are acceptable for the migration phase.

**File:** `tests/test_response_contracts.py`

### 4. Startup-Time Regression

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| `import main` completes under 3s | Slow import promoted by accident | High |

**Strategy:** Test observable startup behavior first (import duration), implementation shape second. An AST-based assertion that specific imports are inside function bodies is acceptable as a narrow guardrail but should remain minimal — brittle to non-semantic restructuring.

**File:** `tests/test_startup.py` (extend existing, 1 test max)

---

## Test Specifications

### `test_scan_manager.py` — ScanManager State Machine

```python
from unittest import IsolatedAsyncioTestCase
from services.scanner import ScanManager

class TestScanManagerLifecycle(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mgr = ScanManager()

    async def test_start_scan_returns_status_dict(self):
        result = await self.mgr.start_scan()
        self.assertEqual(result, {"status": "scanning"})

    async def test_double_start_scan_raises_409(self):
        await self.mgr.start_scan()
        with self.assertRaises(Exception) as ctx:
            await self.mgr.start_scan()
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_stop_scan_when_idle(self):
        result = await self.mgr.stop_scan()
        self.assertEqual(result, {"status": "idle"})

    def test_is_scanning_false_initially(self):
        self.assertFalse(self.mgr.is_scanning())

    async def test_stop_reevaluate_when_idle(self):
        result = await self.mgr.stop_reevaluate()
        self.assertEqual(result, {"status": "idle"})

    async def test_ghost_lock_blocks_scan(self):
        await self.mgr._ghost_lock.acquire()
        with self.assertRaises(Exception) as ctx:
            await self.mgr.start_scan()
        self.assertEqual(ctx.exception.status_code, 409)
        self.mgr._ghost_lock.release()

    async def test_reevaluate_blocked_by_ghost_lock(self):
        await self.mgr._ghost_lock.acquire()
        with self.assertRaises(Exception) as ctx:
            await self.mgr.start_reevaluate()
        self.assertEqual(ctx.exception.status_code, 409)
        self.mgr._ghost_lock.release()
```

### `test_ghost_service.py` — GhostService Phase Contracts

```python
from unittest import IsolatedAsyncioTestCase, mock
from services.ghost import GhostService
from services.scanner import ScanManager

class TestGhostServicePhases(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mgr = ScanManager()
        self.ghost = GhostService(self.mgr)

    @mock.patch("services.ghost.get_setting", return_value="false")
    async def test_preflight_skips_when_ghost_off(self, _):
        result = await self.ghost._phase_preflight()
        self.assertIsNone(result)

    @mock.patch("services.ghost._job_targets", return_value=["board1"])
    @mock.patch("services.ghost.get_setting", return_value="true")
    @mock.patch("services.ghost.get_settings", return_value={})
    @mock.patch("services.ghost._profile_for_discovery", return_value={})
    async def test_preflight_returns_cfg_profile_boards(self, *mocks):
        result = await self.ghost._phase_preflight()
        self.assertIsNotNone(result)
        cfg, profile, boards = result
        self.assertIsInstance(cfg, dict)
        self.assertIsInstance(boards, list)
```

### `test_response_contracts.py` — Response Model Completeness

```python
"""Verify every route's response_model= is a superset of actual response."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_response_fields_in_model():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    # When HealthResponse is missing a field the route returns,
    # that field is silently stripped. This test catches it.
    known = {"status", "uptime_seconds", "timestamp", "log_level", "dependencies"}
    for key in body:
        assert key in known, f"HealthResponse missing field: {key}"


def test_identity_response_fields_in_model():
    resp = client.get("/api/v1/identity")
    assert resp.status_code == 200
    body = resp.json()
    known = {"full_name", "email", "phone", "linkedin_url",
             "github_url", "website_url", "city", "current_company"}
    for key in body:
        assert key in known, f"IdentityResponse missing field: {key}"
```

---

## Execution

1. Create `tests/test_scan_manager.py` (7 tests, `IsolatedAsyncioTestCase`)
2. Create `tests/test_ghost_service.py` (2+ tests, `IsolatedAsyncioTestCase`)
3. Create `tests/test_response_contracts.py` (5+ tests)
4. Update `TEST_DOCS.md` with new test entries
5. Run full suite: `uv run python -m pytest tests/ -q --tb=line`

## Commit

```
test: add coverage for ScanManager, GhostService phases, response model completeness
```
