# Backend Docstrings Pass

**Branch:** `chore/backend-docstrings`
**Parent:** linux-base

---

## Goal

Add docstrings and inline comments to all backend Python files. No behavioral changes. No refactoring. Pure documentation.

## Scope

All `.py` files under `backend/` except:
- `db/client.py` — separate effort (large, complex, needs characterization)
- `agents/*` — separate effort
- `graph/*` — separate effort
- `tests/*` — test files (test names are self-documenting)

## Style

Google-style docstrings:

```python
def func_name(param1: str, param2: int) -> bool:
    """Short description of what the function does.

    Longer description if the behavior is non-obvious.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When something bad happens.
    """
```

For classes:

```python
class MyClass:
    """Short description of the class.

    Longer description of its role and responsibilities.
    """
```

For modules, a top-level docstring explaining the module's purpose.

## Files in scope

| File | Priority | Lines | Notes |
|------|----------|-------|-------|
| `services/job_targets.py` | High | ~200 | Core logic, typed accessors need docs |
| `services/scanner.py` | High | ~250 | ScanManager class + orchestration |
| `services/ghost.py` | High | ~200 | GhostService class + phases |
| `services/scout.py` | Medium | ~100 | X + free source scanning |
| `services/generator.py` | Medium | ~200 | PDF generation, blocking logic |
| `services/provider_probe.py` | Low | ~50 | API key probing |
| `core/ws_manager.py` | High | ~50 | _CM broadcast manager |
| `core/config_constants.py` | Medium | ~30 | Config module |
| `routes/misc.py` | Medium | ~110 | Health, events, template |
| `routes/settings.py` | High | ~110 | Settings CRUD + job-targets endpoints |
| `routes/scan.py` | Medium | ~75 | Scan lifecycle routes |
| `routes/profile.py` | Low | ~90 | Profile CRUD |
| `routes/leads.py` | High | ~255 | Most complex router |
| `routes/ingest.py` | Medium | ~280 | Many routes, various |
| `routes/actions.py` | Medium | ~140 | Fire, form, identity, selectors |
| `routes/ws.py` | High | ~50 | WebSocket auth + handler |
| `schemas/requests.py` | Low | ~160 | Pydantic models (self-documenting) |
| `schemas/responses.py` | Low | ~80 | Response models |
| `main.py` | High | ~150 | App entrypoint |
| `logger.py` | Medium | ~80 | Logging setup |
| `log_context.py` | Medium | ~60 | Correlation context |
| `config/*.py` | Low | ~200 total | Config schemas (self-documenting) |

## Execution

1. One file at a time. Commit after each.
2. Add module docstring first, then class docstrings, then function docstrings.
3. Focus on what each function does, its contract (params/returns), and any non-obvious behavior.
4. No behavioral changes. No refactoring.
5. Run full test suite after each significant chunk.

## Commit format

```
docs: add docstrings to services/job_targets.py
```

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All tests must pass.

## Non-goals

- Refactoring or renaming
- Adding type annotations (already done in C2)
- Changing behavior
- Documenting test files
- Documenting db.client, agents, graph (separate efforts)
