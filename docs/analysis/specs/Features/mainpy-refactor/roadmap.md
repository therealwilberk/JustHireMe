# main.py Refactor — Mini Roadmap

> **Living document.** Update phase status as work progresses.
> Three sequential passes: Extract → Improve → Polish. Each pass is a separate feature branch.
> Every phase within a pass is one branch-and-merge cycle.

---

## Project Status

| Field | Value |
|-------|-------|
| Current pass | Pass C — Response Models & Type Annotations |
| Branch pattern | `feature/mainpy-refactor-pass-c` |
| Last updated | 2026-05-14 |
| Overall status | `[~] Active` |
| **Note** | Mini-roadmap docs will be deleted once the overall refactor is complete `.md` docs |

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

## Future Roadmap Items (Not In Pass C)

- **Externalize job market lists** (`DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`): Move hardcoded job board URLs out of `services/job_targets.py` into a user-editable config (YAML/DB + UI). These are living data — prefer UI update over code change. Needs validation on save (duplicate detection, format checks). Should be a stand-alone feature branch after the refactor is complete.

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

## Pass B — Structural Improvements ✅ Merged

**Goal:** Now that code is modular, improve structure without changing behavior. Extract globals into classes, fix known bugs, narrow broad exceptions.

**Branch:** `feature/mainpy-refactor-pass-b` (deleted after merge)
**Type:** `Infra`
**Mode:** `HITL`

### Phases (execution order)

**Ordering rationale:** B3 (bug fixes) came first so structural changes in B1/B2 didn't share blame with fixes. B4 (lazy imports) ran in parallel with B1/B2.

#### B3 — Fix Known Bugs ✅

| Fix | Status | Commit |
|-----|--------|--------|
| Narrow `_int_cfg` exception | ✅ | `3852204` |
| WS cleanup inside lock | **DROPPED** — holding lock during I/O causes deadlocks | — |
| Job targets → tuples | ✅ | `d68eb77` |
| Unreachable health guard | ✅ Already applied on linux-base | — |

#### B1 — ScanManager Class ✅ (`50f53e9`)

Encapsulated 5 module globals into `ScanManager` class. Routes now use `scanner.scan_manager.start_scan()`.

#### B2 — GhostService Decomposition ✅ (`dcbce4e`)

Split 139-line `_ghost_tick_impl` into 7 named phase methods on `GhostService`.

#### B4 — Resolve Lazy Imports ✅ (`c3a9bac`)

Promoted ~30 fast imports to top-of-file, documented ~58 slow ones with inline comments.

### Pass B Validation ✅

- [x] Scan state encapsulated in `ScanManager` class
- [x] Ghost phases independently readable
- [x] `_int_cfg` catches `(ValueError, TypeError)` only
- [ ] **DROPPED** — `_CM.broadcast()` dead-socket race (original code correct)
- [x] Job target lists are immutable tuples
- [x] Lazy imports resolved where safe
- [x] Full test suite passes (300)
- [x] App launches

---

## Pass C — Response Models & Type Annotations

**Goal:** Add `response_model=` to every route and complete missing type annotations now that the code is modular and easier to audit.

**Branch:** `feature/mainpy-refactor-pass-c`
**Type:** `Infra`
**Mode:** `HITL` (must verify each route returns correct shape)
**Blocked by:** `Pass B`

**Key risk:** Pydantic `response_model=` strips extra fields not in the model. Must verify each route's output shape after wiring — rely on `test_api.py` structured contract assertions to catch silently dropped fields.

### Phases

#### C1 — Response Models (HITL, per router)

Define response Pydantic models in `schemas/responses.py` and add `response_model=` to every route. Wire one router at a time and run tests after each. [Full doc](pass-c/c1-response-models.md)

- [ ] Create `schemas/responses.py` with per-route response models
- [ ] Wire `response_model=` on `routes/misc.py`
- [ ] Wire `response_model=` on `routes/settings.py`
- [ ] Wire `response_model=` on `routes/scan.py`
- [ ] Wire `response_model=` on `routes/leads.py`
- [ ] Wire `response_model=` on `routes/profile.py`
- [ ] Wire `response_model=` on `routes/ingest.py`
- [ ] Wire `response_model=` on `routes/actions.py`
- [ ] Verify no fields silently dropped (run `test_api.py` contract assertions)
- [ ] Commit: `refactor(c1): add response models to all routes`

#### C2 — Type Annotations (AFK, can run parallel with C1)

Add missing `-> ...` return types and param type annotations to all service functions. [Full doc](pass-c/c2-type-annotations.md)

- [ ] Audit all service functions lacking annotations
- [ ] Add complete type annotations to services
- [ ] Run compile check
- [ ] Commit: `chore(c2): add missing type annotations to services`

### Pass C Validation

- [ ] Every route specifies `response_model=`
- [ ] No fields silently dropped by response model validation
- [ ] All service functions have complete type annotations
- [ ] Full test suite passes (300)
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
