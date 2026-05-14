# Backend Docstrings Pass

**Branch:** `feature/backend-docstrings`
**Parent:** linux-base

---

## Goal

Add docstrings and inline comments to all backend Python files. No behavioral changes. No refactoring. Pure documentation.

## Current State (Pre-Audit)

Audit completed across 22 files. **5% documented.** Breakdown:

### Services (49 functions, 6 documented = 12%)

| File | Functions | Documented | Coverage |
|------|-----------|------------|----------|
| `services/job_targets.py` | 17 | 4 | 23% |
| `services/scanner.py` | 13 | 0 | 0% |
| `services/ghost.py` | 10 | 1 | 10% |
| `services/scout.py` | 2 | 0 | 0% |
| `services/generator.py` | 4 | 0 | 0% |
| `services/provider_probe.py` | 3 | 1 | 33% |

### Routes (61 functions, 3 documented = 5%)

| File | Functions | Documented | Coverage |
|------|-----------|------------|----------|
| `routes/misc.py` | 7 | 2 | 29% |
| `routes/settings.py` | 7 | 0 | 0% |
| `routes/scan.py` | 7 | 0 | 0% |
| `routes/profile.py` | 11 | 0 | 0% |
| `routes/leads.py` | 15 | 0 | 0% |
| `routes/ingest.py` | 6 | 0 | 0% |
| `routes/actions.py` | 6 | 0 | 0% |
| `routes/ws.py` | 2 | 1 | 50% |

### Core + Config + Schemas (70+ classes + functions, 1 documented = 1%)

| File | Classes | Functions | Documented |
|------|---------|-----------|------------|
| `core/ws_manager.py` | 1 class | 1 func + 4 methods | 0 |
| `core/config_constants.py` | 0 | 6 constants | 0 |
| `main.py` | 0 | 6 functions | 1 |
| `logger.py` | 2 classes | 2 methods | 0 |
| `log_context.py` | 1 dataclass | 5 functions | 0 |
| `schemas/requests.py` | 24 classes | 1 method | 0 |
| `schemas/responses.py` | 14 classes | 0 | 0 |
| `config/app.py` | 21 classes | 0 | 0 |

**Totals: ~196 functions/classes, ~10 documented (~5%)**

### Key gaps identified

- **No module-level docstrings exist anywhere** — zero of 22 files
- **No class docstrings exist anywhere** — ScanManager, GhostService, _CM, all config schemas = undocumented
- **The only existing docstrings** are on `_bind_port()`, `health()`, `_configured_api_providers()`, `_require_ws_token()`, `_ghost_tick()`, `_sensitive()`, `get_job_targets()`, `get_blocked_markers()`, `validate_job_targets()`, `validate_blocked_markers()`
- **`profile.py` has nothing** — no docstrings, no comments, not even `# lazy:` annotations
- Most files only have `# lazy:` import annotations as their sole inline comments

## Style

Google-style docstrings:

```python
def func_name(param1: str, param2: int) -> bool:
    """Short description of what the function does.

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

## Scope

All `.py` files under `backend/` except:
- `db/client.py` — separate effort (large, ~1200 lines, needs characterization)
- `agents/*` — separate effort
- `graph/*` — separate effort
- `tests/*` — test names are self-documenting

## Execution Order (priority-sequenced)

### Batch 1: Core infrastructure (high value, small files)

| Order | File | Est. time |
|-------|------|-----------|
| 1 | `core/ws_manager.py` | 10min |
| 2 | `core/config_constants.py` | 5min |
| 3 | `log_context.py` | 10min |
| 4 | `logger.py` | 10min |

### Batch 2: Services (highest behavioral complexity)

| Order | File | Est. time |
|-------|------|-----------|
| 5 | `services/scanner.py` (ScanManager + orchestrators) | 20min |
| 6 | `services/ghost.py` (GhostService + phases) | 20min |
| 7 | `services/job_targets.py` (typed accessors + validation) | 15min |
| 8 | `services/generator.py` | 10min |
| 9 | `services/scout.py` | 10min |
| 10 | `services/provider_probe.py` | 5min |

### Batch 3: Routes (HTTP contract documentation)

| Order | File | Est. time |
|-------|------|-----------|
| 11 | `routes/leads.py` (most routes) | 20min |
| 12 | `routes/ingest.py` | 15min |
| 13 | `routes/actions.py` | 10min |
| 14 | `routes/settings.py` | 10min |
| 15 | `routes/scan.py` | 5min |
| 16 | `routes/misc.py` | 10min |
| 17 | `routes/profile.py` | 10min |
| 18 | `routes/ws.py` | 5min |

### Batch 4: Entrypoint and schemas

| Order | File | Est. time |
|-------|------|-----------|
| 19 | `main.py` | 15min |
| 20 | `schemas/requests.py` | 10min |
| 21 | `schemas/responses.py` | 5min |
| 22 | `config/app.py` | 10min |

## Execution Rules

1. One file at a time. Commit after each.
2. Add module docstring first, then class docstrings, then function docstrings.
3. Focus on what each function does, its contract (params/returns), and any non-obvious behavior.
4. No behavioral changes. No refactoring.
5. The existing `# lazy:` import annotations are good — preserve and add to where missing.
6. Run full test suite after each commit.

## Commit format

```
docs: add docstrings to services/scanner.py
```

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 328 tests must pass after each commit.

## Non-goals

- Refactoring or renaming
- Adding type annotations (already done in C2)
- Changing behavior
- Documenting test files
- Documenting db.client, agents, graph (separate efforts)
