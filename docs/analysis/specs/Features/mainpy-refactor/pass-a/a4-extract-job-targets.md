# Pass A4 — Extract Job Targets Service

**Lines affected:** 213-418
**Target file:** `backend/services/job_targets.py`
**Mode:** AFK

---

## Goal

Move all job board configuration constants and helper functions into `services/job_targets.py`. These are pure functions with no side effects — the safest extraction.

---

## What Moves

| Item | Lines in main.py |
|------|-----------------|
| `DEFAULT_JOB_TARGETS` | 213-233 |
| `INDIA_JOB_TARGETS` | 235-249 |
| `_BLOCKED_JOB_TARGET_MARKERS` | 251-254 |
| `_split_configured_targets` | 257-267 |
| `_dedupe_targets` | 270-278 |
| `_job_market_focus` | 281-283 |
| `_is_hn_target` | 286-288 |
| `_job_targets` | 291-318 |
| `_desired_position` | 321-326 |
| `_profile_for_discovery` | 329-340 |
| `_terms_for_discovery` | 343-362 |
| `_profile_free_source_targets` | 365-372 |
| `_profile_x_queries` | 375-382 |
| `_has_x_token` | 385-392 |
| `_int_cfg` | 395-400 |
| `_truthy` | 403-404 |
| `_free_sources_enabled` | 407-408 |
| `_broadcast_x_source_errors` | 411-417 |

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| Resolve function-local lazy imports to top-of-file imports | No longer inside main.py |
| `main.py` imports moved functions via `from services.job_targets import ...` | Required after extraction |

**No behavioral changes.** Functions remain module-level functions. Same signatures. Same logic.

---

## Dependencies

- `core/ws_manager.py` must exist (A3) — `_broadcast_x_source_errors` uses `cm.broadcast`

---

## Verification

```bash
# 1. Compile check
python -m py_compile backend/services/job_targets.py
python -m py_compile backend/main.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line
```

---

## Commit

```
refactor(a1): extract job targets and profile helpers to services/job_targets.py
```
