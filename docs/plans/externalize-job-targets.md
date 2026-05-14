# Externalize Job Market Lists

**Branch:** `chore/externalize-job-targets`
**Parent:** linux-base

---

## Constraint

Zero hardcoded values in source code. All job target configuration lives exclusively in user settings (SQLite). No fallback tuples, no hidden defaults in code.

## Design

### Storage

Two keys in SQLite settings:

| Key | Type | Purpose |
|-----|------|---------|
| `job_targets` | JSON array of strings | URLs and search targets for job discovery |
| `blocked_markers` | JSON array of strings | Freelance/undesired platforms to filter out |

Both keys are **optional**. If absent, the system treats them as empty — user hasn't configured any targets yet. The app does not silently fall back to anything.

### Runtime behavior

The `_job_targets()` function reads **exclusively from settings**. No code-level defaults:

```python
def _job_targets(raw: str, market_focus: str = "global") -> list[str]:
    targets = _split_configured_targets(raw)
    if not targets:
        from db.client import get_settings
        cfg = get_settings()
        stored = cfg.get("job_targets", "")
        if stored:
            try:
                return json.loads(stored)
            except (json.JSONDecodeError, TypeError):
                pass
        return []  # no targets configured — user needs to set them up
    ...
```

Same for `_BLOCKED_JOB_TARGET_MARKERS` — read from settings, no fallback.

### Implications for the app

If `job_targets` is empty (first launch), the system cannot discover job leads. This is intentional and explicit:

- Scan endpoints return empty results (no targets = nothing to scan)
- Ghost mode skips silently (nothing to scout)
- The UI prompts the user to configure targets

This is better than silently using stale defaults the user didn't choose.

### Bootstrap via UI

The settings page provides:
- An empty list with instructional text: "Add URLs or search queries for job boards"
- A "Load recommended defaults" button that populates sensible suggestions
- These suggestions come from the **frontend or a data file**, not from code imports
- Users can add, remove, reorder entries freely

The defaults file (if shipped) lives at `backend/data/defaults/job_targets.json` and is read by the UI, not by the import graph. This keeps it separate from code.

## What Gets Removed

Everything from `services/job_targets.py`:

| Symbol | Action |
|--------|--------|
| `DEFAULT_JOB_TARGETS` | Delete |
| `INDIA_JOB_TARGETS` | Delete |
| `_BLOCKED_JOB_TARGET_MARKERS` | Delete |
| India-specific filtering in `_job_targets()` | Delete |
| `_job_market_focus()` | Delete (no longer drives list selection) |
| `focus == "global"` HN-harding fallback | Delete |

## Ripple Effects

### 1. `services/job_targets.py` — Clean slate

- Remove all tuple constants
- Simplify `_job_targets()` to read only from settings
- Remove `_job_market_focus()`, `_is_hn_target()`, India-related logic
- Remove `_dedupe_targets()` if unused elsewhere (check callers)
- Keep: `_split_configured_targets()`, `_desired_position()`, `_profile_for_discovery()`, `_terms_for_discovery()`, `_profile_free_source_targets()`, `_profile_x_queries()`, `_has_x_token()`, `_int_cfg()`, `_truthy()`, `_free_sources_enabled()`, `_broadcast_x_source_errors()`

### 2. `services/scanner.py` — Handle empty targets

- `_run_scan()` calls `_job_targets()` — if returns `[]`, skip scouting gracefully
- Add early return with broadcast message: "No job targets configured — add targets in Settings"

### 3. `services/ghost.py` — Handle empty targets

- `_phase_preflight()` calls `_job_targets()` — if returns `[]`, skip gracefully
- Update the "no job boards configured" warning to point to Settings UI

### 4. `routes/settings.py` or new routes — CRUD

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/settings/job-targets` | Return current targets + blocked markers |
| `PUT` | `/api/v1/settings/job-targets` | Save targets (validates before storing) |
| `DELETE` | `/api/v1/settings/job-targets` | Clear all targets (reset to empty) |

**Validation on PUT:**
- Must be a JSON object with optional `targets` and `blocked` keys
- Each value must be a JSON array of strings
- No empty strings
- No duplicates within an array
- Max 100 entries per array
- Invalid entries rejected with specific error detail

**Response shapes:**

```python
class JobTargetsResponse(BaseModel):
    targets: list[str]
    blocked: list[str]

class JobTargetsUpdateBody(BaseModel):
    targets: list[str] | None = None
    blocked: list[str] | None = None
```

### 5. `services/job_targets.py` — Validation helpers (new)

```python
def validate_job_targets_list(entries: list[str]) -> list[str]:
    errors = []
    if not isinstance(entries, list):
        return ["must be a list"]
    if len(entries) > 100:
        errors.append("exceeds maximum of 100 entries")
    seen = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(f"[{i}]: entry must be a non-empty string")
        elif entry.strip().lower() in seen:
            errors.append(f"[{i}]: duplicate entry '{entry}'")
        else:
            seen.add(entry.strip().lower())
    return errors
```

### 6. Tests

| File | Change |
|------|--------|
| `test_regressions.py` | Remove India-specific tests (`TestLeadQualityGate` India tests, `test_job_targets_india_fallback`) |
| `test_response_contracts.py` | Add contract check for new `GET /api/v1/settings/job-targets` |
| `test_job_targets.py` (update or new) | Override reads from settings, empty settings = empty list, validation rejects bad input |

### 7. Third-party callers

Check what imports `INDIA_JOB_TARGETS`, `DEFAULT_JOB_TARGETS`, `_BLOCKED_JOB_TARGET_MARKERS`, `_job_market_focus`:

```bash
grep -rn "INDIA_JOB_TARGETS\|DEFAULT_JOB_TARGETS\|_BLOCKED_JOB_TARGET_MARKERS\|_job_market_focus" backend/
```

Update any references.

## Tasks

### Phase 1: Backend — Remove all hardcoded tuples
- [ ] Delete `DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`, `_BLOCKED_JOB_TARGET_MARKERS` from `services/job_targets.py`
- [ ] Delete `_job_market_focus()` and India-specific filtering
- [ ] Modify `_job_targets()` to read exclusively from settings
- [ ] Add validation helpers (`validate_job_targets_list`)
- [ ] Remove unused imports from `services/job_targets.py`
- [ ] Check and update all imports from this module
- [ ] Run `uv run python -m pytest tests/ -q --tb=line`

### Phase 2: Handle empty-targets gracefully
- [ ] Update `services/scanner.py` `_run_scan()` to handle empty target list
- [ ] Update `services/ghost.py` `_phase_preflight()` to handle empty target list

### Phase 3: CRUD API
- [ ] Add `JobTargetsResponse` and `JobTargetsUpdateBody` to schemas
- [ ] Add `GET/PUT/DELETE /api/v1/settings/job-targets` routes
- [ ] Wire `response_model=` on new routes

### Phase 4: Tests
- [ ] Update `test_regressions.py` — remove India-specific tests, add override resolution tests
- [ ] Add contract test for new endpoints
- [ ] Run full test suite

### Phase 5: Frontend (separate branch)
- [ ] Replace hardcoded INDIA/DEFAULT UI with single editable list
- [ ] "Load recommended defaults" button
- [ ] Wire to new API endpoints

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All tests pass. Existing tests that relied on India-specific behavior must be removed or updated.

## Commits

1. `refactor: remove hardcoded job target constants, read from settings exclusively`
2. `feat: add CRUD API for job target configuration`
3. `test: update tests for settings-driven job targets`
