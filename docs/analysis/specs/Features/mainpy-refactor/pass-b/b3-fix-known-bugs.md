# Pass B3 — Fix Known Bugs

**Mode:** AFK per fix, HITL collectively  
**Branch:** `feature/mainpy-refactor-pass-b`  
**Depends on:** Pass A complete

---

## Goal

Apply four small bug fixes identified in the structure report. Each fix is independent and gets its own commit. This pass comes FIRST in Phase B to avoid ambiguity ("did the class extraction break it or did the bug fix break it?").

---

## Fix 1: `_int_cfg` — Narrow bare `except Exception`

**File:** `backend/services/job_targets.py`  
**Risk:** Low

**Current:**
```python
def _int_cfg(cfg: dict, key: str, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(str(cfg.get(key, "") or "").strip())
    except Exception:
        value = default
    return max(min_value, min(value, max_value))
```

**Fix:** Catch `(ValueError, TypeError)` only. These are the only exceptions `int()` and `.strip()` can raise in normal use. Catching bare `Exception` masks bugs like `AttributeError` if `cfg` is `None`.

```python
def _int_cfg(cfg: dict, key: str, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(str(cfg.get(key, "") or "").strip())
    except (ValueError, TypeError):
        value = default
    return max(min_value, min(value, max_value))
```

**Verify:**
```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

**Commit:** `fix(b3): narrow _int_cfg exception to ValueError and TypeError`

---

## Fix 2: `_CM.broadcast()` — Dead-socket cleanup inside lock

**File:** `backend/core/ws_manager.py`  
**Risk:** Low (behavioral change, but only for edge case of concurrent WS disconnect during broadcast)

**Current:** Dead sockets are collected outside the lock, then cleaned up inside a re-acquired lock. Between collection and cleanup, a new socket could be added that happens to have the same identity (unlikely in Python, but a race nonetheless).

**Fix:** Move the dead cleanup inside the same lock scope as the snapshot:

```python
    async def broadcast(self, msg: dict):
        if msg.get("type") == "agent":
            try:
                from db.client import record_event
                await asyncio.to_thread(
                    record_event, msg.get("job_id") or "__system__", _agent_event_action(msg)
                )
            except Exception:
                _log.warning("Failed to record agent event: job_id=%s", msg.get("job_id"))
        async with self._lock:
            snapshot = list(self._ws)
            dead = []
            for w in snapshot:
                try:
                    await w.send_text(json.dumps(msg))
                except Exception:
                    dead.append(w)
            if dead:
                self._ws = [w for w in self._ws if not any(w is d for d in dead)]
```

**Verify:**
```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

**Commit:** `fix(b3): move ws cleanup inside lock in _CM.broadcast()`

---

## Fix 3: Job target lists → immutable tuples

**File:** `backend/services/job_targets.py`  
**Risk:** Very low

**Change:** `DEFAULT_JOB_TARGETS` and `INDIA_JOB_TARGETS` from `list[str]` to `tuple[str, ...]` to prevent accidental mutation at runtime.

**Note:** The `_job_targets()` function calls `list(INDIA_JOB_TARGETS if ... else DEFAULT_JOB_TARGETS)` which already creates a copy — so callers won't notice the change.

**Verify:**
```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

**Commit:** `fix(b3): change job target lists to immutable tuples`

---

## Fix 4: Remove unreachable `require_http_token` guard

**File:** `backend/main.py`  
**Risk:** Very low

**Current:**
```python
if request.method == "OPTIONS" or request.url.path == "/health":
    return await call_next(request)
if request.url.path != "/health":
    creds = await _bearer(request)
```

The `if request.url.path != "/health"` on line 3 is unreachable — `/health` already returned on line 2. Remove it.

**Fix:**
```python
if request.method == "OPTIONS" or request.url.path == "/health":
    return await call_next(request)
creds = await _bearer(request)
```

**Verify:**
```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

**Commit:** `fix(b3): remove unreachable health path guard in auth middleware`

---

## Collective Verification

After all 4 fixes:
```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 300 tests must pass.
