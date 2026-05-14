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

## Fix 2: `_CM.broadcast()` — ~~Dead-socket cleanup inside lock~~ **DROPPED**

**File:** `backend/core/ws_manager.py`  
**Risk:** ~~Low~~ **BREAKS the test suite**

The proposed fix moves `await w.send_text()` inside the lock scope. This holds an `asyncio.Lock` across an I/O await, causing deadlocks in the WS concurrency tests (tests hang, ~15s baseline blows up to indefinite).

**Why the original code is correct:** The identity comparison `w is d` means a newly-added socket can never match as "dead" — it's a different object with a different `id()`. The theoretical identity-reuse race is effectively impossible in CPython. The lock-release pattern (snapshot under lock → send outside lock → cleanup under re-acquired lock) is the correct async pattern: never hold a lock during I/O.

**Verdict:** Original code stands. Fix 2 skipped.

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

## Fix 4: Remove unreachable `require_http_token` guard — **ALREADY APPLIED**

**File:** `backend/main.py`

Already fixed on `linux-base` (cleaned up during Pass A or earlier). The guard is absent from the current code — no action needed.

---

## Collective Verification

After all 4 fixes:
```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 300 tests must pass.
