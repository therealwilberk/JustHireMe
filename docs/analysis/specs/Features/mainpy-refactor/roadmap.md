# main.py Refactor — Mini Roadmap

> **Living document.** Update phase status as work progresses.
> Three sequential passes: Extract → Improve → Polish. Each pass is a separate feature branch.
> Every phase within a pass is one branch-and-merge cycle.

---

## Project Status

| Field | Value |
|-------|-------|
| Current pass | Pass A — Pure Extraction |
| Branch pattern | `feature/mainpy-refactor-pass-a` |
| Last updated | 2026-05-14 |
| Overall status | `[x] Complete` |

---

## Rationale

`backend/main.py` is 2162 lines with 50 routes, a WebSocket connection manager, background task orchestration, and ad-hoc helper functions. The structure report identified the split points. This roadmap sequences the work in three passes that progressively reduce risk:

1. **Pass A** — Pure file splitting. Zero behavioral changes. If it breaks, it's an import error.
2. **Pass B** — Structural improvements now that the code is modular.
3. **Pass C** — Add `response_model=` and missing type annotations.

Each pass is a separate feature branch from `linux-base`. Each phase within a pass is one commit.

---

## Deferred / Not In Scope

- Refactoring `db/client.py` (separate effort)
- Refactoring `agents/` modules (separate effort)
- Adding new functionality
- Performance optimization
- Replacing `asyncio.to_thread` with proper async patterns

---

## Pass A — Pure Extraction

**Goal:** Extract `main.py` into modular files with zero behavioral changes. Functions stay as functions. No new classes. No bug fixes. No response models.

**Branch:** `feature/mainpy-refactor-pass-a`
**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `AFK` (every phase is file moves + import updates)
**Blocks:** `Pass B`

### Phases

| # | Phase | Mode | Doc | Verification |
|---|-------|------|-----|-------------|
| A1 | Scaffold directory structure | AFK | [a1-scaffold.md](pass-a/a1-scaffold.md) | `py_compile main.py` |
| A2 | Extract schemas → `schemas/requests.py` | AFK | [a2-extract-schemas.md](pass-a/a2-extract-schemas.md) | Full test suite |
| A3 | Extract core → `core/ws_manager.py`, `core/config_constants.py` | AFK | [a3-extract-core.md](pass-a/a3-extract-core.md) | Full test suite + app launch |
| A4 | Extract job targets → `services/job_targets.py` | AFK | [a4-extract-job-targets.md](pass-a/a4-extract-job-targets.md) | Full test suite |
| A5 | Extract scanner → `services/scanner.py` | AFK | [a5-extract-scanner.md](pass-a/a5-extract-scanner.md) | Full test suite |
| A6 | Extract ghost + scout → `services/ghost.py`, `services/scout.py` | AFK | [a6-extract-ghost.md](pass-a/a6-extract-ghost.md) | Full test suite |
| A7 | Extract generator + probe → `services/generator.py`, `services/provider_probe.py` | AFK | [a7-extract-generator-probe.md](pass-a/a7-extract-generator-probe.md) | Full test suite |
| A8 | Extract routes → `routes/*.py` (8 files, one per commit) | AFK per file, HITL verify | [a8-extract-routes.md](pass-a/a8-extract-routes.md) | Full test suite after each |
| A9 | Strip main.py to app entrypoint | HITL | [a9-cleanup-main.md](pass-a/a9-cleanup-main.md) | Full test suite + route smoke test |

### Pass A Validation

- [x] All Pydantic models moved to `schemas/requests.py` with zero field changes
- [x] `_CM` class moved to `core/ws_manager.py`, imported by all callers
- [x] All 49 HTTP routes + 1 WebSocket route functional from their new router modules
- [x] No behavioral changes — every function works identically to before
- [x] Full test suite passes (`uv run python -m pytest tests/ -q --tb=line`) — 298 passed
- [x] App launches via `uvicorn main:app`
- [x] `main.py` under 150 lines (137 lines)
- [x] Startup time under 3s (was 19.7s, now 2.5s cumulative import time)

### Key Discovery: Lazy Imports Required for Startup Performance

During Pass A, all lazy imports (inside function bodies) were moved to top-of-file. This caused `db.client` (~7s via lancedb), `llm` (~3s via instructor+anthropic), and `graph`/`langgraph` (~1.6s) to load during module import, pushing total startup past the 15s sidecar timeout.

**Fix applied:** Top-of-file imports were reverted to lazy per-function imports for all slow transitive dependencies (`db.client`, `agents.*`, `graph`, `llm`, `services.generator`). Only fast modules (stdlib, `core/*`, `schemas/*`) remain at top level. The `__main__` block was also moved before heavy imports (early fix) as defense-in-depth.

**Lesson for future passes:** Slow imports (>1s) should always remain lazy unless the module is used on every single request. The original `main.py` used lazy imports everywhere for this exact reason — the refactor should preserve that pattern.

---

## Pass B — Structural Improvements

**Goal:** Now that code is modular, improve structure without changing behavior. Extract globals into classes, fix known bugs, narrow broad exceptions.

**Branch:** `feature/mainpy-refactor-pass-b`
**Type:** `Infra`
**Mode:** `HITL` (each improvement needs verification)
**Blocked by:** `Pass A`
**Requires:** Full test suite to pass before starting

### Phases

#### B1 — ScanManager Class (HITL)

Wrap `_scan_task`, `_scan_stop`, `_reevaluate_task`, `_reevaluate_stop`, `_ghost_lock` into a `ScanManager` class. Methods: `start_scan()`, `stop_scan()`, `start_reevaluate()`, `stop_reevaluate()`, `is_scanning()`, `is_reevaluating()`.

- [ ] Create `ScanManager` class wrapping all scan state
- [ ] Expose as `scan_manager = ScanManager()` singleton
- [ ] Update all route handlers and services to use `scan_manager` instead of module globals
- [ ] Verify: scan/stop/reevaluate lifecycle works
- [ ] Verify: tests pass
- [ ] Commit: `refactor(b1): encapsulate scan state in ScanManager class`

#### B2 — GhostService Decomposition (HITL)

Decompose `_ghost_tick_impl` into phase methods. Verify the decomposed version produces identical outcomes.

- [ ] Create `GhostService` class
- [ ] Decompose into: `phase_preflight()`, `phase_scout()`, `phase_eval()`, `phase_gen()`, `phase_apply()`
- [ ] Keep `run()` as the public entrypoint that calls phases sequentially
- [ ] Verify: ghost mode tick executes without error
- [ ] Verify: tests pass
- [ ] Commit: `refactor(b2): decompose ghost tick into GhostService phase methods`

#### B3 — Fix Known Bugs (AFK per fix, HITL collectively)

Apply fixes identified in the structure report, each in a separate commit:

- [ ] Fix `_int_cfg` bare `except Exception` → `except (ValueError, TypeError)`
  - Commit: `fix(b3): narrow _int_cfg exception to ValueError and TypeError`
- [ ] Fix `_CM.broadcast()` dead-socket cleanup to happen inside the lock
  - Commit: `fix(b3): move ws cleanup inside lock in _CM.broadcast()`
- [ ] Change `DEFAULT_JOB_TARGETS` and `INDIA_JOB_TARGETS` to `tuple[str, ...]`
  - Commit: `fix(b3): change job target lists to immutable tuples`
- [ ] Remove dead `if request.url.path != "/health"` guard in `require_http_token`
  - Commit: `fix(b3): remove unreachable health path guard in auth middleware`

#### B4 — Resolve Lazy Imports (AFK)

Move lazy imports to top of each file where safe. Flag any circular import issues.

- [ ] Audit all per-function imports in extracted modules
- [ ] Move to top of file where no circular import risk
- [ ] Document any that must remain lazy with a comment explaining why
- [ ] Verify: tests pass
- [ ] Commit: `refactor(b4): resolve lazy imports to top-of-file where safe`

### Pass B Validation

- [ ] Scan state encapsulated in `ScanManager` class
- [ ] Ghost phases independently testable
- [ ] `_int_cfg` catches `(ValueError, TypeError)` only
- [ ] `_CM.broadcast()` no longer has dead-socket race
- [ ] Job target lists are immutable tuples
- [ ] Lazy imports resolved where safe
- [ ] Full test suite passes
- [ ] App launches

---

## Pass C — Response Models & Type Annotations

**Goal:** Add `response_model=` to every route and complete missing type annotations now that the code is modular and easier to audit.

**Branch:** `feature/mainpy-refactor-pass-c`
**Type:** `Infra`
**Mode:** `HITL` (must verify each route returns correct shape)
**Blocked by:** `Pass B`

### Phases

#### C1 — Response Models (HITL, per router)

For each router, define response Pydantic models and add `response_model=` to every route handler. Verify the response shape hasn't changed after adding the model.

- [ ] Define response schemas in `schemas/responses.py`
- [ ] Wire `response_model=` on every route in each router
- [ ] Verify each route returns the expected shape (Pydantic strips extra fields — must not lose data)
- [ ] Commit: `refactor(c1): add response models to routes/`

#### C2 — Type Annotations (AFK)

Add missing `-> ...` return types and param type annotations to all service functions.

- [ ] Audit all functions lacking annotations (identified in structure report)
- [ ] Add complete type annotations
- [ ] Run static check if available
- [ ] Commit: `chore(c2): add missing type annotations to services`

### Pass C Validation

- [ ] Every route specifies `response_model=`
- [ ] No fields silently dropped by response model validation
- [ ] All service functions have complete type annotations
- [ ] Full test suite passes
- [ ] App launches

---

## Verification Protocol

Every phase follows this checklist before commit:

```bash
# 1. Compile check
python -m py_compile backend/main.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line

# 3. App launch check (smoke)
cd backend && timeout 5 uv run python -m uvicorn main:app --port 9999 || true
```

If any step fails: **stop.** Do not proceed. Report the error. Do not auto-fix.

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-14 | Initial mini-roadmap created | Planning main.py refactor after Phase C completion |
