# Externalize Job Market Lists

**Branch:** `chore/externalize-job-targets`
**Parent:** linux-base

---

## Problem

`DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`, and `_BLOCKED_JOB_TARGET_MARKERS` are hardcoded tuples in `services/job_targets.py`. Users cannot modify job board sources without editing code. These are living data — board URLs change, new sources appear, regional preferences differ.

## Design

Store overrides as JSON arrays in SQLite settings (existing `save_settings`/`get_settings` mechanism). Three new settings keys:

| Key | Overrides | Default value |
|-----|-----------|---------------|
| `job_targets_defaults` | `DEFAULT_JOB_TARGETS` | The current tuple |
| `job_targets_india` | `INDIA_JOB_TARGETS` | The current tuple |
| `blocked_target_markers` | `_BLOCKED_JOB_TARGET_MARKERS` | The current tuple |

`_job_targets()` checks these settings first. If a key is absent (not yet configured), it falls back to the hardcoded constants. This preserves backward compatibility — existing installs see no change until they set overrides.

## Ripple Effects

### 1. `services/job_targets.py` — Core logic change

Modify `_job_targets()` to read overrides from settings before falling back to constants:

```python
def _job_targets(raw: str, market_focus: str = "global") -> list[str]:
    focus = _job_market_focus(market_focus)
    targets = _split_configured_targets(raw)
    if not targets:
        # Check for user-configured overrides in settings
        from db.client import get_settings
        cfg = get_settings()
        if focus == "india":
            override = cfg.get("job_targets_india", "")
        else:
            override = cfg.get("job_targets_defaults", "")
        if override:
            try:
                return json.loads(override)
            except (json.JSONDecodeError, TypeError):
                pass  # fall through to hardcoded defaults
        return list(INDIA_JOB_TARGETS if focus == "india" else DEFAULT_JOB_TARGETS)
    ...
```

Similarly, `_BLOCKED_JOB_TARGET_MARKERS` usage in the filter loop should check for overrides.

**Files changed:** `services/job_targets.py`

### 2. New API routes — CRUD for job target lists

Add endpoints to `routes/settings.py` or a new `routes/job_targets.py`:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/settings/job-targets` | Return current lists (merged defaults + overrides) |
| `PUT` | `/api/v1/settings/job-targets` | Save custom lists (validates before storing) |
| `DELETE` | `/api/v1/settings/job-targets` | Reset all lists to factory defaults |

**Validation on PUT:**
- Each list must be a JSON array of strings
- No empty strings
- No duplicates within a list
- No duplicates across `defaults` and `india` lists (warning, not error)
- Max 100 entries per list
- Invalid entries are rejected with specific error detail

**Response shapes:**

```python
class JobTargetsResponse(BaseModel):
    defaults: list[str]
    india: list[str]
    blocked_markers: list[str]

class JobTargetsUpdateBody(BaseModel):
    defaults: list[str] | None = None  # None = keep current
    india: list[str] | None = None
    blocked_markers: list[str] | None = None
```

**Files created:** None (add to existing router) or `routes/job_targets.py` (new)
**Files changed:** `routes/settings.py` or new file, `schemas/requests.py`, `schemas/responses.py`

### 3. Validation helpers

Add validation to `services/job_targets.py`:

```python
def _validate_job_targets(lists: dict) -> list[str]:
    """Validate proposed target lists. Returns list of error messages (empty = valid)."""
    errors = []
    for name, entries in lists.items():
        if not isinstance(entries, list):
            errors.append(f"{name}: must be a list")
            continue
        if len(entries) > 100:
            errors.append(f"{name}: exceeds maximum of 100 entries")
        seen = set()
        for i, entry in enumerate(entries):
            if not isinstance(entry, str) or not entry.strip():
                errors.append(f"{name}[{i}]: entry must be a non-empty string")
            elif entry.strip().lower() in seen:
                errors.append(f"{name}[{i}]: duplicate entry '{entry}'")
            else:
                seen.add(entry.strip().lower())
    return errors
```

### 4. Frontend settings UI

The existing settings page (`SettingsModal`) needs a section for job board management:
- Text area or list editor for each list (defaults, india, blocked)
- Save button with validation feedback
- Reset to defaults button

**Files changed:** Frontend settings components (TBD — need to check current structure)

### 5. Config schema

If using YAML-based config override (`JHM_CONFIG_DIR`), add optional keys for these lists. The resolution order: CLI/env config → SQLite settings → hardcoded defaults.

**Files changed:** `config/settings_schema.py` or similar (TBD)

### 6. Tests

| Test file | What to add |
|-----------|-------------|
| `test_job_targets.py` (new) | Read overrides from settings, fallback to defaults, validation rejects bad input, CRUD endpoints return correct shapes |
| `test_response_contracts.py` | Add contract checks for new job-targets endpoints |

### 7. `TEST_DOCS.md`

Add entries for new test file and updated API surface.

---

## Tasks

### Phase 1: Backend — Read overrides in `_job_targets()`
- [ ] Add `import json` to `services/job_targets.py`
- [ ] Modify `_job_targets()` to check settings for overrides before falling back
- [ ] Modify `_BLOCKED_JOB_TARGET_MARKERS` usage to check settings
- [ ] Run `uv run python -m pytest tests/ -q --tb=line`

### Phase 2: Backend — CRUD API
- [ ] Define request/response schemas in `schemas/requests.py` and `schemas/responses.py`
- [ ] Add validation helpers to `services/job_targets.py`
- [ ] Add `GET/PUT/DELETE /api/v1/settings/job-targets` routes
- [ ] Wire `response_model=` on new routes
- [ ] Run full test suite

### Phase 3: Backend — Config schema (optional)
- [ ] Add job-target keys to config layer if YAML overrides are desired

### Phase 4: Tests
- [ ] Create `tests/test_job_targets.py` with override/fallback/validation tests
- [ ] Extend `tests/test_response_contracts.py` for new endpoints
- [ ] Update `TEST_DOCS.md`
- [ ] Run full test suite

### Phase 5: Frontend (separate effort, outline only)
- [ ] Add job board management section to `SettingsModal`
- [ ] Wire to new API endpoints
- [ ] Validation feedback in UI

---

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All existing 314 tests + new tests must pass. Existing behavior unchanged when no overrides configured.

## Commit

```
feat: externalize job target lists to user-configurable settings
```
