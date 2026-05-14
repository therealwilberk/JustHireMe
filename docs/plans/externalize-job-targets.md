# Externalize Job Market Lists

**Branch:** `chore/externalize-job-targets`
**Parent:** linux-base

---

## Problem

Three hardcoded tuples in `services/job_targets.py`: `DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`, `_BLOCKED_JOB_TARGET_MARKERS`. The INDIA/DEFAULT dualism assumes only two user categories exist. Someone in Kenya, Brazil, Germany, or Nigeria gets nothing useful from either list. These are living data — they should be user-configurable.

## Design

**Collapse to a single configurable list.** Remove the INDIA/DEFAULT split. Users configure their own preferred targets regardless of location.

| Current | After |
|---------|-------|
| `DEFAULT_JOB_TARGETS` + `INDIA_JOB_TARGETS` | One `_DEFAULT_JOB_TARGETS` tuple (hardcoded fallback) |
| `_job_targets()` checks `market_focus == "india"` | `_job_targets()` reads user override from settings |
| `INDIA_JOB_TARGETS` list | Removed — replaced by user config |

**Storage:** A single JSON array in SQLite settings key `job_targets`:
- `job_targets` — user's custom list (JSON array of strings). Absent = use hardcoded defaults.
- `blocked_markers` — user's custom blocked markers. Absent = use hardcoded defaults.

**Resolution order:**
1. User's custom list from settings (`job_targets`)
2. Hardcoded `_DEFAULT_JOB_TARGETS` fallback

The `market_focus` setting (`"global"` / `"india"` / whatever) becomes a UI label, not a code-level lookup key. Users set their own targets through the UI regardless of what `market_focus` says.

## Ripple Effects

### 1. `services/job_targets.py` — Rename + override logic

- Rename `DEFAULT_JOB_TARGETS` → `_DEFAULT_JOB_TARGETS` (internal, not part of public contract)
- **Remove `INDIA_JOB_TARGETS` entirely**
- Modify `_job_targets()` to read `job_targets` override from settings first:

```python
def _job_targets(raw: str, market_focus: str = "global") -> list[str]:
    targets = _split_configured_targets(raw)
    if not targets:
        from db.client import get_settings
        cfg = get_settings()
        override = cfg.get("job_targets", "")
        if override:
            try:
                return json.loads(override)
            except (json.JSONDecodeError, TypeError):
                pass
        return list(_DEFAULT_JOB_TARGETS)
    ...
```

- Remove the `focus == "india"` special case in the filtering logic (lines 98-108)
- The `_job_market_focus()` function can stay (it's used elsewhere for search query generation), but it no longer drives target list selection

### 2. New API route — Replace/customize job targets

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/settings/job-targets` | Return current list (override or defaults) |
| `PUT` | `/api/v1/settings/job-targets` | Save custom list (validates before storing) |
| `DELETE` | `/api/v1/settings/job-targets` | Reset to factory defaults |

**Validation on PUT:**
- Must be a JSON array of strings
- No empty strings
- No duplicates
- Max 100 entries
- Each entry is a valid format (URL or `site:` or valid prefix)

**Response shapes:**

```python
class JobTargetsResponse(BaseModel):
    targets: list[str]
    using_defaults: bool  # true when no user override set

class JobTargetsUpdateBody(BaseModel):
    targets: list[str]
```

### 3. `services/job_targets.py` — Remove stale India-specific logic

Lines that reference `INDIA_JOB_TARGETS` or `india_markers` in `_job_targets()` need cleanup:

- `return list(INDIA_JOB_TARGETS if focus == "india" else DEFAULT_JOB_TARGETS)` → `return list(_DEFAULT_JOB_TARGETS)` (override checked above)
- The `if focus == "india":` block with `india_markers` filtering (lines 101-108) — remove this entire block. Users configure their own targets; they don't need automatic filtering.
- The `focus == "global"` HN-hiring fallback (line 98) — keep (it's a sensible default)

### 4. Frontend settings UI

The `SettingsModal` needs a `job_market_focus` field (already exists as a dropdown) and a new:
- Textarea or list editor for job target URLs
- "Reset to defaults" button
- Validation feedback

### 5. Backward compatibility

- Existing installs see NO change until they set `job_targets` in settings
- The default `job_market_focus` was `"global"` — still works, just no longer maps to a hardcoded list
- The `job_boards` text field (custom newline-separated targets) still works as before — if set, it takes precedence over both settings override and hardcoded defaults
- `_job_targets()` resolution order: `job_boards` (custom text input) → `job_targets` (settings override) → `_DEFAULT_JOB_TARGETS` (hardcoded)

### 6. Tests

- Update `test_regressions.py` — remove India-specific tests, add override tests
- Update `test_response_contracts.py` — add contract check for new endpoint
- Create or use existing test for `_job_targets()` override resolution

### 7. `TEST_DOCS.md`

Update entries for changed test coverage.

---

## Tasks

### Phase 1: Backend — Remove INDIA, add override in `_job_targets()`
- [ ] Rename `DEFAULT_JOB_TARGETS` → `_DEFAULT_JOB_TARGETS`
- [ ] Remove `INDIA_JOB_TARGETS` tuple
- [ ] Add `import json` to `services/job_targets.py`
- [ ] Modify `_job_targets()` to check `job_targets` setting before falling back
- [ ] Remove India-specific filtering block (lines ~98-108)
- [ ] Remove `_BLOCKED_JOB_TARGET_MARKERS` → move to settings
- [ ] Run `uv run python -m pytest tests/ -q --tb=line`

### Phase 2: Backend — CRUD API
- [ ] Define `JobTargetsResponse` and `JobTargetsUpdateBody` in schemas
- [ ] Add validation helpers to `services/job_targets.py`
- [ ] Add `GET/PUT/DELETE /api/v1/settings/job-targets` routes
- [ ] Wire `response_model=` on new routes
- [ ] Run full test suite

### Phase 3: Tests
- [ ] Update `test_regressions.py` — replace India-specific tests with override tests
- [ ] Add contract test for new endpoints in `test_response_contracts.py`
- [ ] Run full test suite

### Phase 4: Frontend (separate branch)
- [ ] Add job board management to `SettingsModal`
- [ ] Wire to new API endpoints

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 314 existing tests + new tests pass. Existing behavior unchanged when no overrides configured.

## Commits

1. `refactor: remove INDIA_JOB_TARGETS, add settings-based job target override`
2. `feat: add CRUD API for job target configuration`
3. `test: update tests for externalized job targets`
