# Pass C2 — Type Annotations

**Mode:** AFK
**Branch:** `feature/mainpy-refactor-pass-c`
**Blocked by:** Can run in parallel with C1 (no file overlap)

---

## Goal

Add missing return types and param type annotations to all service functions. This is **static-analysis hardening only** — no behavioral changes, no logic refactors, no architecture cleanup mixed in.

## Scope Discipline

This pass does ONE thing: annotate what's already there. Do NOT:
- Refactor logic while touching signatures
- Change function bodies
- Add new abstractions
- Fix bugs found along the way (note them, move on)
- Mix with architecture cleanup

The value is cognitive compression — answering "what comes in? what goes out? nullable? sync or async? side-effect only?" without reading the implementation body.

## Async annotations matter disproportionately

Explicit return types on async functions are far more valuable than sync ones because async workflows already carry high cognitive load:

```python
# Weak:
async def run_scan(...) -> Any:

# Strong:
async def run_scan(...) -> ScanResult:
```

## Avoid `dict[str, Any]` spread unless truly necessary

Many service functions have implicit stable structure. Prefer:
- `TypedDict` for dict-shaped returns
- `dataclass` for simple containers
- Existing Pydantic models where they already match

`dict[str, Any]` is acceptable as transitional typing, but if it becomes the universal answer the pass loses most of its value.

## What to Annotate

All functions in:
- `services/scanner.py`
- `services/ghost.py`
- `services/scout.py`
- `services/job_targets.py`
- `services/generator.py`
- `services/provider_probe.py`
- `core/ws_manager.py`
- `core/config_constants.py`

## What NOT to Annotate

- Route handlers — `response_model=` covers outbound shape; route annotations can be deferred (route files are still being stabilized)
- Pydantic models in `schemas/` — already typed
- `db/client.py`, `agents/*`, `graph/*` — out of scope (need characterization before aggressive typing)

## Execution

1. Read each file, find functions missing annotations
2. Add return types and param types (no body changes)
3. Run tests after each file

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
uv run python -m py_compile backend/services/scanner.py  # syntax check
```

`py_compile` proves syntax validity only. For deeper validation, consider running:
```bash
cd backend && uv run python -m mypy --ignore-missing-imports backend/services/  # informational
```

Not as a CI gate yet, but as informational analysis — otherwise annotations exist but may be semantically meaningless.
