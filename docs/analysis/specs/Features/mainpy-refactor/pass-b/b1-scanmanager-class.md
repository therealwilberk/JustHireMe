# Pass B1 — ScanManager Class

**Mode:** HITL  
**Branch:** `feature/mainpy-refactor-pass-b`  
**Blocked by:** Pass B3 (bug fixes)

---

## Goal

Encapsulate the five correlated module-level globals into a `ScanManager` class. These globals implement a hidden state machine for scan/reevaluate lifecycle — making them instance variables on a class makes the state machine explicit and testable.

## What Changes

### Current state (in `services/scanner.py`)

```python
_scan_stop = asyncio.Event()
_scan_task: asyncio.Task | None = None
_reevaluate_stop = asyncio.Event()
_reevaluate_task: asyncio.Task | None = None
_ghost_lock = asyncio.Lock()
```

These are accessed from `routes/scan.py` via `scanner._scan_task`, `scanner._scan_stop`, etc.

### Target state

```python
class ScanManager:
    def __init__(self):
        self._scan_task: asyncio.Task | None = None
        self._scan_stop: asyncio.Event = asyncio.Event()
        self._reevaluate_task: asyncio.Task | None = None
        self._reevaluate_stop: asyncio.Event = asyncio.Event()
        self._ghost_lock: asyncio.Lock = asyncio.Lock()

    async def start_scan(self) -> None:
        if self._ghost_lock.locked():
            raise HTTPException(status_code=409, detail="...")
        if self._scan_task and not self._scan_task.done():
            raise HTTPException(status_code=409, detail="...")
        if self._reevaluate_task and not self._reevaluate_task.done():
            raise HTTPException(status_code=409, detail="...")
        self._scan_stop.clear()
        self._scan_task = asyncio.create_task(self._run_scan_task())

    async def stop_scan(self) -> dict:
        if not self._scan_task or self._scan_task.done():
            return {"status": "idle"}
        self._scan_stop.set()
        await cm.broadcast(...)
        return {"status": "stopping"}

    async def start_reevaluate(self) -> None:
        ...

    async def stop_reevaluate(self) -> dict:
        ...

    def is_scanning(self) -> bool:
        return bool(self._scan_task and not self._scan_task.done())

    def is_reevaluating(self) -> bool:
        return bool(self._reevaluate_task and not self._reevaluate_task.done())

    async def _run_with_ghost_lock(self, coro) -> None:
        try:
            await asyncio.wait_for(self._ghost_lock.acquire(), timeout=0)
        except asyncio.TimeoutError:
            _log.warning("...")
            return
        try:
            await coro
        except Exception as exc:
            _log.error("...")
            await cm.broadcast(...)
        finally:
            self._task_ref = None
            self._ghost_lock.release()
```

### What moves as methods

- `_run_scan_task` → `ScanManager._run_scan_task()` (private)
- `_run_reevaluate_jobs_task` → `ScanManager._run_reevaluate_jobs_task()` (private)
- `_run_scan` → stays as module-level function (pure orchestration, no state)
- `_run_reevaluate_jobs` → stays as module-level function (pure orchestration, no state)

### What updates

- `routes/scan.py` — replace `scanner._scan_task` etc. with `scan_manager.start_scan()` etc.
- `services/ghost.py` — replace `_ghost_lock` reference with `scan_manager._ghost_lock`
- `services/scout.py` — `_scan_stop` reference (check if still needed)

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line

# Manual smoke test:
# POST /api/v1/scan → expect 200/409
# POST /api/v1/scan/stop → expect 200
# POST /api/v1/leads/reevaluate → expect 200/409
# POST /api/v1/leads/reevaluate/stop → expect 200
```

All 300 tests must pass.

## Commit

```
refactor(b1): encapsulate scan state in ScanManager class
```
