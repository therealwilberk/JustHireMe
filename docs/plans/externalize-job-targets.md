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

### Typed accessors (not raw JSON parsing)

Instead of `json.loads(stored)` scattered through services, use dedicated helpers:

```python
# services/job_targets.py

def get_job_targets() -> list[str]:
    """Read configured job targets from settings. Empty = none configured."""
    from db.client import get_settings
    cfg = get_settings()
    stored = cfg.get("job_targets", "")
    if not stored:
        return []
    try:
        result = json.loads(stored)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def get_blocked_markers() -> list[str]:
    """Read configured blocked markers from settings."""
    from db.client import get_settings
    cfg = get_settings()
    stored = cfg.get("blocked_markers", "")
    if not stored:
        return []
    try:
        result = json.loads(stored)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def save_job_targets(targets: list[str], blocked: list[str]) -> None:
    from db.client import save_settings
    save_settings({
        "job_targets": json.dumps(targets),
        "blocked_markers": json.dumps(blocked),
    })
```

This centralizes serialization, keeps it consistent, and avoids scattered `json.loads` calls.

### Runtime behavior

`_job_targets()` reads exclusively from settings via the typed accessor:

```python
def _job_targets(raw: str, market_focus: str = "global") -> list[str]:
    targets = _split_configured_targets(raw)
    if not targets:
        return get_job_targets()  # typed accessor, no raw json.loads
    ...
```

Blocked markers filtering likewise:

```python
blocked = get_blocked_markers()
for target in targets:
    if any(marker in target.lower() for marker in blocked):
        continue
```

### "No targets" is visible, not silent

Scan and ghost modes emit explicit operational visibility when no targets are configured:

```python
# In _run_scan() / ghost phases:
if not targets:
    await cm.broadcast({
        "type": "agent",
        "event": "scan_skipped",
        "msg": "No job targets configured — add targets in Settings",
    })
    _log.warning("Scan skipped: no job targets configured")
    return  # or []
```

This applies to:
- Scan endpoint → returns `{"status": "skipped", "reason": "no targets configured"}` with WS event
- Ghost mode → emits structured warning, WS event, scheduler log entry. Not silent.

### Bootstrap via UI

The settings page provides:
- An empty list with instructional text: "Add URLs or search queries for job boards"
- A "Load recommended defaults" button that populates sensible suggestions
- Suggestions come from the frontend or a data file, not from code imports

The defaults file (if shipped) lives at `backend/data/defaults/job_targets.json` and is read by the UI, not by the import graph.

## What Gets Removed

| Symbol | Action |
|--------|--------|
| `DEFAULT_JOB_TARGETS` | Delete |
| `INDIA_JOB_TARGETS` | Delete |
| `_BLOCKED_JOB_TARGET_MARKERS` | Delete |
| India-specific filtering in `_job_targets()` | Delete |
| `_job_market_focus()` | Delete (no longer drives list selection) |
| `focus == "global"` HN-harding fallback | Delete |

## Validation

Validation runs server-side on PUT. Checks:

| Check | Why |
|-------|-----|
| Must be valid JSON array of strings | Structural integrity |
| No empty strings | Meaningless entries |
| No duplicates | Redundant entries waste scan budget |
| Max 100 entries per list | Sanity limit |
| Max 500 chars per entry | Prevents junk / garbage input |
| URL-like entries: scheme must be http/https or `site:` prefix | Catches typos, javascript: URLs |
| Whitespace stripped from each entry | Normalization |

```python
def validate_job_targets(entries: list[str]) -> list[str]:
    """Returns list of error messages (empty = valid)."""
    errors = []
    if not isinstance(entries, list):
        return ["must be a list of strings"]
    if len(entries) > 100:
        errors.append("exceeds maximum of 100 entries")
    seen = set()
    for i, entry in enumerate(entries):
        cleaned = entry.strip()
        if not isinstance(entry, str) or not cleaned:
            errors.append(f"[{i}]: entry must be a non-empty string")
        elif len(cleaned) > 500:
            errors.append(f"[{i}]: entry exceeds 500 character limit")
        elif cleaned.lower() in seen:
            errors.append(f"[{i}]: duplicate entry '{cleaned}'")
        else:
            seen.add(cleaned.lower())
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                pass  # valid URL
            elif cleaned.startswith("site:") or cleaned.startswith("github:") or cleaned.startswith("hn:") or cleaned.startswith("reddit:"):
                pass  # valid search prefix
            else:
                errors.append(f"[{i}]: entry must start with http://, https://, site:, github:, hn:, or reddit:")
    return errors
```

## Blocked markers — safety consideration

Removing `_BLOCKED_JOB_TARGET_MARKERS` from code means users can accidentally remove all filtering and ingest spam/freelance listings. This is acceptable philosophically (user-owned configuration), but the UI should:

- Always show the current blocked list visibly, not hidden in advanced settings
- Warn when blocked list is empty: "No blocked markers configured. Freelance and low-quality platforms will not be filtered."
- Consider future immutable internal safety filters (separate effort)

## Frontend-Backend Compatibility

### Current data flow

```
Frontend textarea (job_boards)  ──POST /api/v1/settings──►  SQLite settings
                                                            │
Backend _job_targets() reads job_boards ──► split/parse ──► fallback to 
                                                            DEFAULT_JOB_TARGETS / INDIA_JOB_TARGETS
Frontend preset buttons  ──► append URLs to job_boards textarea
Frontend market toggle   ──► writes job_market_focus to settings
```

### After changes — resolution order preserved

```
job_boards (frontend textarea) ──► parsed directly ──► used if non-empty
                                    │
job_targets (new settings key)  ──► JSON parse ──► used if job_boards empty
                                    │
[] (empty)                      ──► no targets configured
```

### What stays the same (no frontend changes needed)

| Concern | Status | Why |
|---------|--------|-----|
| `job_boards` textarea | ✅ Unchanged | Backend still reads `job_boards` first in `_job_targets()` |
| Quick-add buttons | ✅ Unchanged | They append to `job_boards` textarea — same behavior |
| `GLOBAL_SOURCE_PRESET` / `INDIA_SOURCE_PRESET` | ✅ Unchanged | They populate the textarea — backend parses it the same way |
| `job_market_focus` toggle | ✅ Unchanged | Backend ignores it for target selection, but still accepts it in settings passthrough |
| `POST /api/v1/settings` | ✅ Unchanged | Still saves all flat key-value pairs including `job_boards` |

### What changes (backend only, invisible to frontend until new UI)

| Concern | Change | Frontend impact |
|---------|--------|-----------------|
| `_job_targets()` no fallback | Returns `[]` instead of hidden defaults | Behavioral — user sees "no targets" instead of invisible scan |
| `blocked_markers` in settings | Moved from code constant to SQLite | None — frontend doesn't reference this |
| New `GET /api/v1/settings/job-targets` | Additive API | None until new Settings UI consumes it |
| `job_market_focus` decoupled | Backend ignores for target list selection | None — field still saved/loaded via settings passthrough |

### Verification strategy

Each phase is verifiable independently:

1. **Phase 1** — `git diff` shows removed constants, added accessors. `pytest` proves behavioral equivalence when `job_boards` is populated.
2. **Phase 2** — `job_boards=""` + `job_targets=""` → scan returns empty with WS event. Verify via `JHM_LOG_LEVEL=DEBUG`.
3. **Phase 3** — CRUD API via `curl` or `httpx`. Round-trip: PUT → GET returns same data.
4. **Phase 4** — `pytest` proves all edge cases covered.
5. **Phase 5** — Start app, navigate to Settings, verify textarea still works, new CRUD UI shows correct state.

The API shape (`targets: list[str]`) is a single flat list. This is correct now. Future discovery profiles (region-specific, role-specific, source-type-specific) would extend the schema with additional fields, not replace it. Avoid designing yourself into "one flat list forever" — the schema should accept additional keys gracefully (ignore extras, validate known ones).

## Ripple Effects

### 1. `services/job_targets.py` — Clean slate

- Remove all tuple constants
- Add `get_job_targets()`, `get_blocked_markers()`, `save_job_targets()` typed accessors
- Add `validate_job_targets()` validation
- Simplify `_job_targets()` to read only from typed accessors
- Remove `_job_market_focus()`, `_is_hn_target()`, India-related logic
- Remove `_dedupe_targets()` if unused elsewhere
- Keep: `_split_configured_targets()`, `_desired_position()`, `_profile_for_discovery()`, `_terms_for_discovery()`, `_profile_free_source_targets()`, `_profile_x_queries()`, `_has_x_token()`, `_int_cfg()`, `_truthy()`, `_free_sources_enabled()`, `_broadcast_x_source_errors()`

### 2. `services/scanner.py` — Handle empty targets with visibility

- `_run_scan()` — if `_job_targets()` returns `[]`, broadcast WS warning + return early
- Return `{"status": "skipped", "reason": "no targets configured"}`

### 3. `services/ghost.py` — Handle empty targets with visibility

- `_phase_preflight()` — if `_job_targets()` returns `[]`, broadcast ghost_warn + log + return None
- Not silent — structured warning, WS event, scheduler log

### 4. CRUD API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/settings/job-targets` | Return current targets + blocked markers |
| `PUT` | `/api/v1/settings/job-targets` | Save targets (validates before storing) |
| `DELETE` | `/api/v1/settings/job-targets` | Clear all targets (reset to empty) |

**Response shapes:**

```python
from pydantic import Field

class JobTargetsResponse(BaseModel):
    targets: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)

class JobTargetsUpdateBody(BaseModel):
    targets: list[str] | None = None
    blocked: list[str] | None = None
```

### 5. Third-party callers

```bash
grep -rn "INDIA_JOB_TARGETS\|DEFAULT_JOB_TARGETS\|_BLOCKED_JOB_TARGET_MARKERS\|_job_market_focus" backend/
```

Update any references.

### 6. Tests

| File | Change |
|------|--------|
| `test_regressions.py` | Remove India-specific tests, add typed accessor resolution tests |
| `test_response_contracts.py` | Add contract check for new endpoints |
| Test file for validation | Validate rejects bad entries, accepts valid ones |

## Tasks

### Phase 1: Backend — Remove all hardcoded tuples
- [ ] Delete `DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`, `_BLOCKED_JOB_TARGET_MARKERS`
- [ ] Add `get_job_targets()`, `get_blocked_markers()`, `save_job_targets()` typed accessors
- [ ] Add `validate_job_targets()` with URL scheme + length + duplicate checks
- [ ] Replace raw `json.loads` references with typed accessors
- [ ] Delete `_job_market_focus()` and India-specific filtering
- [ ] Remove unused imports
- [ ] Check and update all import references
- [ ] Run full test suite

### Phase 2: Handle empty-targets visibly
- [ ] Update `_run_scan()` — broadcast WS warning, return early with status
- [ ] Update ghost `_phase_preflight()` — broadcast ghost_warn, log, return None

### Phase 3: CRUD API
- [ ] Add schemas with `Field(default_factory=list)`
- [ ] Add `GET/PUT/DELETE /api/v1/settings/job-targets` routes
- [ ] Wire `response_model=` on new routes

### Phase 4: Tests
- [ ] Update tests for removed India behavior
- [ ] Add typed accessor tests (empty settings, valid stored, corrupt stored)
- [ ] Add validation tests (bad URLs, duplicates, over limit)
- [ ] Add contract test for new endpoints
- [ ] Run full test suite

### Phase 5: Frontend (separate branch)
- [ ] Replace INDIA/DEFAULT UI with single editable list
- [ ] "Load recommended defaults" button
- [ ] Wire to new API endpoints
- [ ] Show blocked markers list visibly

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All tests pass. Existing tests that relied on India-specific behavior are removed or updated.

## Commits

1. `refactor: remove hardcoded job target constants, add typed settings accessors`
2. `feat: add CRUD API for job target configuration`
3. `test: update tests for settings-driven job targets`
