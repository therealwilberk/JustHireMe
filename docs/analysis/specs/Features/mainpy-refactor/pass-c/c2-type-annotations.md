# Pass C2 — Type Annotations

**Mode:** AFK
**Branch:** `feature/mainpy-refactor-pass-c`
**Blocked by:** Pass C1 (recommended, but can run in parallel)

---

## Goal

Add missing `-> ...` return types and param type annotations to all service functions. This is purely cosmetic/static-analysis — no behavioral change.

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

- Route handlers — they're annotated by `response_model=` in C1
- Pydantic models in `schemas/` — already typed
- `db/client.py`, `agents/*`, `graph/*` — out of scope (separate effort)

## Execution

1. Read each service file, find functions missing annotations
2. Add return types and param types
3. No behavioral changes
4. Run tests after each significant file

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
uv run python -m py_compile backend/services/scanner.py  # compile check
```
