# Pass A6 — Extract Ghost Service

**Lines affected:** 420-507, 533-685
**Target file:** `backend/services/ghost.py`, `backend/services/scout.py`
**Mode:** AFK

---

## Goal

Move ghost mode orchestration and the two scout functions into `services/`. `_ghost_tick_impl` stays as one monolithic function (not decomposed — that's Pass B).

---

## What Moves

### To `services/scout.py`

| Item | Lines in main.py |
|------|-----------------|
| `_run_x_signal_scan` | 420-467 |
| `_run_free_source_scan` | 471-507 |

### To `services/ghost.py`

| Item | Lines in main.py |
|------|-----------------|
| `_ghost_tick` | 533-543 |
| `_ghost_tick_impl` | 546-685 |

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| Scout functions in `services/scout.py` import from `services/job_targets.py` instead of inline imports | Natural dependency chain |
| Ghost functions in `services/ghost.py` import from `services/scout.py`, `services/job_targets.py` | Dependency chain |
| `main.py` route handlers and `lifespan` import from `services/ghost.py` | `_ghost_tick` is used by `lifespan` |

**No behavioral changes.** `_ghost_tick_impl` is not decomposed. Scout functions are not modified.

---

## Dependencies

- `core/ws_manager.py` (A3) — `cm.broadcast`
- `core/config_constants.py` (A3) — `_log`
- `services/job_targets.py` (A4) — all helper functions
- `services/scanner.py` (A5) — `_ghost_tick` references `_ghost_lock` and scan state

---

## Verification

```bash
# 1. Compile checks
python -m py_compile backend/services/scout.py
python -m py_compile backend/services/ghost.py
python -m py_compile backend/main.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line
```

---

## Commit

```
refactor(a1): extract ghost mode and scout functions to services/
```
