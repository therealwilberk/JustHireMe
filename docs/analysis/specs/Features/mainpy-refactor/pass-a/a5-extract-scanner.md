# Pass A5 — Extract Scanner Service

**Lines affected:** 1197-1451, 1454-1477, 510-521
**Target file:** `backend/services/scanner.py`
**Mode:** AFK

---

## Goal

Move all scan orchestration, re-evaluation orchestration, and helper functions to `services/scanner.py`. Functions stay as module-level functions (not yet wrapped in a class). The global state variables (`_scan_task`, `_scan_stop`, etc.) also move to this module.

**Important:** The route handlers (`scan`, `stop_scan`, `reevaluate_jobs`, `stop_reevaluate_jobs`) stay in `main.py` during this pass — they move in A8 (routes). Only the background task wrappers and the scan/reevaluate implementations move.

---

## What Moves

| Item | Lines in main.py |
|------|-----------------|
| `_scan_stop` (asyncio.Event) | 510 |
| `_scan_task` (asyncio.Task \| None) | 511 |
| `_reevaluate_stop` (asyncio.Event) | 512 |
| `_reevaluate_task` (asyncio.Task \| None) | 513 |
| `_ghost_lock` (asyncio.Lock) | 514 |
| `_REEVALUATION_STATUS_LOCKS` | 516 |
| `_should_preserve_job_status` | 519-520 |
| `_job_eval_document` | 523-530 |
| `_run_scan_task` | 1286-1300 |
| `_run_reevaluate_jobs_task` | 1303-1317 |
| `_run_reevaluate_jobs` | 1320-1374 |
| `_run_scan` | 1377-1451 |
| `_sensitive` | 1454-1458 |
| `_log_sensitive_deprecation` | 1461-1477 |

**What stays in main.py:** Route handlers that reference these functions:
- `scan()` (line 1197) — stays, imports from `scanner`
- `stop_scan()` (line 1211) — stays, imports from `scanner`
- `reevaluate_jobs()` (line 1220) — stays, imports from `scanner`
- `stop_reevaluate_jobs()` (line 1234) — stays, imports from `scanner`
- `cleanup_leads()` (line 1243) — stays, imports from `scanner`
- `free_sources_scan()` (line 1269) — stays, imports from `scanner`

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| Move global state vars to `scanner.py` | They define the scan lifecycle |
| Route handlers in `main.py` import `scanner` module | Access scan state via module refs |
| `_run_scan` now references `_scan_stop` via module-level ref in `scanner.py` | Same pattern, different file |

**No behavioral changes.** No class wrapping. No method extraction.

---

## Dependencies

- `core/ws_manager.py` (A3) — `cm.broadcast` used in scan functions
- `core/config_constants.py` (A3) — `_log` used in scan functions
- `services/job_targets.py` (A4) — `_run_scan` calls `_run_x_signal_scan`, `_run_free_source_scan`, job target helpers

---

## Verification

```bash
# 1. Compile check
python -m py_compile backend/services/scanner.py
python -m py_compile backend/main.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line

# 3. Smoke scan lifecycle (optionally)
# POST /api/v1/settings with ghost_mode=false first, then POST /api/v1/scan
```

---

## Commit

```
refactor(a1): extract scanner and re-evaluation logic to services/scanner.py
```
