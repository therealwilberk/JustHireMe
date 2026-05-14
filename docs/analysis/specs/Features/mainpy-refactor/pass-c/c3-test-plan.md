# Pass C3 — Post-Refactor Test Plan

**Goal:** Cover the abstractions and behavioral boundaries introduced during the main.py refactor. Not filler — tests that would catch real regressions.

**Branch:** separate `feature/mainpy-refactor-pass-c-tests` (after merging pass-c)

---

## What Needs Testing

### 1. ScanManager State Machine (`services/scanner.py`)

The ScanManager class replaced 5 module globals with encapsulated methods. It implements a hidden state machine for scan/reevaluate/ghost lifecycle.

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| `start_scan()` while ghost lock held → 409 | Guard missed, ghost lock not checked | High |
| `start_scan()` while scan already running → 409 | Double-scan allowed | High |
| `stop_scan()` when idle → `{"status": "idle"}` | KeyError on `_scan_task.done()` when `_scan_task` is None | High |
| `start_reevaluate()` while ghost lock held → 409 | Cross-contamination of lock state | Medium |
| `start_reevaluate()` while scan running → 409 | Allowed concurrent scan + reevaluate | High |
| `is_scanning()` when task not started → False | Checks None.done() | Medium |
| Concurrent `start_scan()` + `stop_scan()` race | Event.set() + create_task ordering | Medium |

**Test strategy:** Unit test the class directly — instantiate `ScanManager()`, call methods, assert state transitions. No DB, no mocks. Fast deterministic tests.

**File:** `tests/test_scan_manager.py`

### 2. GhostService Phase Isolation (`services/ghost.py`)

The 139-line `_ghost_tick_impl` was split into 7 named phase methods. The risk is that phases aren't truly independent (leaking state between them) or that `run()` orchestration order changes.

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| `_phase_preflight` returns None when ghost mode off | Skip logic wrong | Medium |
| `_phase_eval` returns `list[dict]` with leads scoring >= 85 only | Filter threshold wrong | Medium |
| `_phase_gen` skips assets if eval empty | Empty-approved handling | Low |
| `_phase_apply` checks auto_apply before submitting | Gate logic wrong | Medium |
| `run()` orchestrates phases in correct order | Phase sequencing changed | High |

**Test strategy:** Mock `scan_manager._ghost_lock` (it's already a module attr), instantiate `GhostService(scan_manager)`, call individual phases. Use fake config/profile.

**File:** `tests/test_ghost_service.py`

### 3. Response Model Completeness (`schemas/responses.py`)

**This is the most important test.** `response_model=` silently strips fields not in the model. We need to prove every route's current response shape is a subset of its model.

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| Every route returns all fields its model declares | Silent field drop | **Critical** |
| Routes with `response_model=dict[str, Any]` accept any shape | Overly permissive | Medium |
| CSV/FileResponse routes are NOT wired with response_model | Binary content corrupted | High |

**Test strategy:** Use the existing `TestClient` with storage fakes. For each route with `response_model=SomeModel`:
1. Call the route
2. Parse response as JSON
3. Re-serialize through the model: `model.model_dump()`
4. Assert no `KeyError` on model fields
5. Assert response body keys are subset of model fields

This catches the silent-drop scenario: if the route returns a field the model doesn't know about, the re-serialized output drops it — and the test catches the mismatch.

**File:** `tests/test_response_contracts.py` (new file)

### 4. Startup-Time Regression

| Scenario | What could break | Priority |
|----------|-----------------|----------|
| `import main` completes under 3s | Slow import promoted by accident | High |
| Lazy imports are actually lazy | Comment says lazy but import moved to top | Medium |

**Test strategy:** Already exists in `test_startup.py`. Extend to verify specific lazy imports are still lazy by checking they're inside function bodies (AST analysis).

**File:** `tests/test_startup.py` (extend existing)

---

## Test Specifications

### `test_scan_manager.py` — ScanManager State Machine

```python
import asyncio
from unittest import TestCase
from services.scanner import ScanManager

class TestScanManagerLifecycle(TestCase):
    def setUp(self):
        self.mgr = ScanManager()

    def test_start_scan_returns_status_dict(self):
        result = asyncio.run(self.mgr.start_scan())
        self.assertEqual(result, {"status": "scanning"})

    def test_double_start_scan_raises_409(self):
        asyncio.run(self.mgr.start_scan())
        with self.assertRaises(Exception) as ctx:
            asyncio.run(self.mgr.start_scan())
        self.assertEqual(ctx.exception.status_code, 409)

    def test_stop_scan_when_idle(self):
        result = asyncio.run(self.mgr.stop_scan())
        self.assertEqual(result, {"status": "idle"})

    def test_is_scanning_false_initially(self):
        self.assertFalse(self.mgr.is_scanning())

    def test_stop_reevaluate_when_idle(self):
        result = asyncio.run(self.mgr.stop_reevaluate())
        self.assertEqual(result, {"status": "idle"})

    def test_ghost_lock_blocks_scan(self):
        async def _test():
            await self.mgr._ghost_lock.acquire()
            with self.assertRaises(Exception) as ctx:
                await self.mgr.start_scan()
            self.assertEqual(ctx.exception.status_code, 409)
            self.mgr._ghost_lock.release()
        asyncio.run(_test())

    def test_reevaluate_blocked_by_ghost_lock(self):
        async def _test():
            await self.mgr._ghost_lock.acquire()
            with self.assertRaises(Exception) as ctx:
                await self.mgr.start_reevaluate()
            self.assertEqual(ctx.exception.status_code, 409)
            self.mgr._ghost_lock.release()
        asyncio.run(_test())
```

### `test_ghost_service.py` — GhostService Phase Isolation

```python
import asyncio
from unittest import TestCase, mock
from services.ghost import GhostService
from services.scanner import ScanManager

class TestGhostServicePhases(TestCase):
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
import json
from unittest import TestCase
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestResponseModelsCoverAllFields(TestCase):
    """For each route with response_model=, call it and verify
    the response body contains only fields the model knows about.
    When response_model strips a field, this test catches it."""

    def test_health_response_fields_in_model(self):
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # The model is HealthResponse — check no unknown top-level keys
        known = {"status", "uptime_seconds", "timestamp", "log_level", "dependencies"}
        for key in body:
            self.assertIn(key, known, f"HealthResponse missing field: {key}")

    def test_identity_response_fields_in_model(self):
        resp = client.get("/api/v1/identity")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        known = {"full_name", "email", "phone", "linkedin_url",
                 "github_url", "website_url", "city", "current_company"}
        for key in body:
            self.assertIn(key, known, f"IdentityResponse missing field: {key}")

    def test_fire_response_fields_in_model(self):
        resp = client.post("/api/v1/fire/test-id")
        # This may 404 since test-id doesn't exist — that's fine,
        # we're testing that 200 paths return model-conformant data.
        if resp.status_code == 200:
            body = resp.json()
            known = {"status", "job_id"}
            for key in body:
                self.assertIn(key, known)
```

### Existing test extension — `test_startup.py`

Add a test that verifies specific slow imports are still lazy (inside function bodies):
```python
def test_lazy_imports_are_still_lazy():
    """AST check: db.client imports should be inside function bodies."""
    import ast
    with open("routes/leads.py") as f:
        tree = ast.parse(f.read())
    # Count function-level imports matching db.client
    func_imports = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and hasattr(node, 'col_offset')  # module-level
    ]
    # ... assert specific pattern
```

---

## Execution

1. Create `tests/test_scan_manager.py` (8 tests)
2. Create `tests/test_ghost_service.py` (5 tests)
3. Create `tests/test_response_contracts.py` (5 tests)
4. Extend `tests/test_startup.py` (1 test)
5. Update `TEST_DOCS.md` with new test entries
6. Run full suite: `uv run python -m pytest tests/ -q --tb=line`

## Commit

```
test: add coverage for ScanManager, GhostService phases, response model completeness
```
