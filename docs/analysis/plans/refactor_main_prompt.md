# Prompt — Refactor `main.py` into Modular Structure
> Feed this prompt the structure report. Work one module at a time.
> App must launch and all 50 routes must work after every phase.

---

## Context

You are refactoring `backend/main.py` (2162 lines, 50 routes, 1 WebSocket)
into a clean modular structure. A full structural analysis has already been
done. You are working from that report — do not re-analyse the file.

This is a solo Linux fork of JustHireMe. The app must be fully functional
after every phase. No big-bang rewrites. One module extracted at a time,
verified, committed, then the next.

---

## Guiding principles

**Modularity** — each file has one responsibility. Routes handle HTTP only.
Services contain business logic. Core contains shared infrastructure.

**Deep modules** — prefer fewer, larger well-bounded modules over many small
ones. A route file for 12 related routes is better than 12 separate files.

**Proper exceptions** — replace bare `except Exception` with typed catches
where the exception type is knowable. Create custom exception classes in
`core/exceptions.py` for domain errors.

**Proper logging** — every module gets its own logger via `get_logger(__name__)`.
No print statements. No silent failures.

**Abstract base classes** — where services share an interface (agents, scanners,
ingestors) define ABCs in `core/abstracts.py`.

**Dependency injection over globals** — `cm`, `_sched`, scan state should be
injectable, not grabbed from module-level globals where possible.

**Type annotations** — add return types and param types to all functions
that currently lack them during the move.

**Response models** — add `response_model=` to routes during extraction.
This is the right moment — not a separate pass.

---

## Target structure

```
backend/
├── main.py                    # app init, middleware, router inclusion, lifespan, CLI only
├── core/
│   ├── __init__.py
│   ├── config_constants.py    # _UP, _API_TOKEN, _LOCAL_ORIGIN_RE, _bearer
│   ├── exceptions.py          # custom exception classes
│   ├── abstracts.py           # ABCs for agents, scanners, ingestors
│   ├── logging.py             # logging setup (if not already in logger.py)
│   └── ws_manager.py          # _CM class + cm singleton
├── routes/
│   ├── __init__.py
│   ├── leads.py               # 12 lead routes + export + versions + manual + followups
│   ├── profile.py             # 11 profile routes
│   ├── settings.py            # 3 settings routes
│   ├── ingest.py              # 6 ingest routes
│   ├── scan.py                # 6 scan lifecycle routes
│   ├── actions.py             # fire, generate, pipeline, form, apply, pdf
│   ├── ws.py                  # WebSocket endpoint
│   └── misc.py                # health, events, graph, template, help, selectors
├── services/
│   ├── __init__.py
│   ├── ghost.py               # _ghost_tick, _ghost_tick_impl + decomposed phases
│   ├── scanner.py             # _run_scan, _run_reevaluate_jobs + task wrappers
│   ├── scout.py               # _run_x_signal_scan, _run_free_source_scan
│   ├── scheduler.py           # _sched, scheduler setup
│   ├── generator.py           # _generate_one, _actuate
│   ├── job_targets.py         # _job_targets, DEFAULT/INDIA targets, helpers
│   ├── profile_helpers.py     # _profile_for_discovery, _terms_for_discovery etc
│   └── provider_probe.py      # _probe_provider_key
└── schemas/
    ├── __init__.py
    └── requests.py            # StrictBody + all Pydantic request models
```

---

## Decision answers (from open questions in report)

Answer these before the agent proceeds — fill in your decisions:

1. **`cm` global** → [ ] Injectable dependency via `Depends()` / [x] Module-level singleton imported from `core/ws_manager.py`
   > Recommended: singleton for now. 25 call sites is too much surface area to change safely in one pass. Move it to `core/ws_manager.py`, import from there. Revisit later.

2. **Scan state machine** → [x] Extract into `ScanManager` class in `services/scanner.py`
   > Recommended: yes. `_scan_task`, `_scan_stop`, `_reevaluate_task`, `_reevaluate_stop`, `_ghost_lock` become `self.*` on a `ScanManager` instance. Methods: `start_scan()`, `stop_scan()`, `start_reevaluate()`, `stop_reevaluate()`, `is_scanning()`.

3. **`_ghost_tick_impl` decomposition** → [x] Decompose phases into private methods on a `GhostService` class
   > 139 lines / 6 phases → `_phase_x_scan()`, `_phase_free_scan()`, `_phase_scout()`, `_phase_eval()`, `_phase_gen()`, `_phase_apply()` — each under 30 lines.

4. **Shared task wrapper** → [x] `_run_with_ghost_lock(coro)` utility in `services/scanner.py`

5. **`ingest_linkedin` / `import_profile_json` DRY** → [x] Refactor to loop over `(extractor, persister, field_name)` tuples

6. **`_int_cfg` broad except** → catch `(ValueError, TypeError)` only

7. **Target list mutability** → [x] Change to `tuple[str, ...]`

8. **Pydantic models** → [x] Move all to `schemas/requests.py`

9. **`require_http_token` dead code** → [x] Remove the unreachable `if request.url.path != "/health"` guard

10. **Response models** → [x] Add during extraction pass

---

## Phase plan

Work through these phases in order. Do not begin a phase until the
previous phase is verified and committed.

### Phase 0 — Scaffolding (AFK)
Create the empty directory and `__init__.py` structure.
No logic moved yet. Just folders and empty files.
Verify: `python -m py_compile backend/main.py` still passes.
Commit: `chore: scaffold modular backend structure`

---

### Phase 1 — Core infrastructure (HITL)
Extract in this order:

1. `core/exceptions.py` — define custom exception classes:
   - `ScanAlreadyRunningError`
   - `ScanNotRunningError`
   - `AssetNotReadyError`
   - `ProviderKeyInvalidError`
   - `IngestError`
   Add docstrings to each.

2. `core/abstracts.py` — define ABCs:
   - `BaseAgent(ABC)` — abstract `run()` method
   - `BaseScanner(ABC)` — abstract `scan()` method
   - `BaseIngestor(ABC)` — abstract `ingest()` method

3. `core/ws_manager.py` — move `_CM` class exactly as-is.
   Export `cm = _CM()` singleton from this module.
   Update `main.py` to import `cm` from here.
   Fix the known race condition: `broadcast()` currently mutates
   `self._ws` outside the lock during dead-socket cleanup.
   Move the cleanup inside the lock.

4. `core/config_constants.py` — move `_UP`, `_API_TOKEN`,
   `_LOCAL_ORIGIN_RE`, `_bearer`.
   Update all references in `main.py`.

Verify after each file: app launches, `/health` responds.
Commit: `refactor: extract core infrastructure modules`

---

### Phase 2 — Schemas (AFK)
Move all Pydantic models to `schemas/requests.py`:
- `StrictBody` and all 10 subclasses (lines 91-169)
- `SettingsBody` (line 159)
- Ingest models (lines 1623-1684)
- `FormReadBody` (line 1948)

Update all imports in `main.py`.
Verify: app launches, all routes still importable.
Commit: `refactor: move all Pydantic schemas to schemas/requests.py`

---

### Phase 3 — Services layer (HITL, one file at a time)

#### 3a — `services/job_targets.py`
Move: `DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`, `_BLOCKED_JOB_TARGET_MARKERS`,
`_split_configured_targets`, `_dedupe_targets`, `_job_market_focus`,
`_is_hn_target`, `_job_targets`, `_desired_position`, `_profile_for_discovery`,
`_terms_for_discovery`, `_profile_free_source_targets`, `_profile_x_queries`,
`_has_x_token`, `_int_cfg`, `_truthy`, `_free_sources_enabled`,
`_broadcast_x_source_errors`.

Fix during move:
- Change `DEFAULT_JOB_TARGETS` and `INDIA_JOB_TARGETS` to `tuple[str, ...]`
- Change `_int_cfg` to catch `(ValueError, TypeError)` only
- Resolve lazy imports at top of module

Verify: app launches.
Commit: `refactor: extract job targets + profile helpers to services`

#### 3b — `services/scanner.py`
Create `ScanManager` class:
```python
class ScanManager:
    def __init__(self):
        self._scan_task: asyncio.Task | None = None
        self._scan_stop: asyncio.Event = asyncio.Event()
        self._reevaluate_task: asyncio.Task | None = None
        self._reevaluate_stop: asyncio.Event = asyncio.Event()
        self._ghost_lock: asyncio.Lock = asyncio.Lock()

    async def start_scan(self) -> None: ...
    async def stop_scan(self) -> None: ...
    async def start_reevaluate(self) -> None: ...
    async def stop_reevaluate(self) -> None: ...
    def is_scanning(self) -> bool: ...
    def is_reevaluating(self) -> bool: ...
    async def _run_with_ghost_lock(self, coro) -> None: ...
```

Move `_run_scan`, `_run_scan_task`, `_run_reevaluate_jobs`,
`_run_reevaluate_jobs_task` as methods.
Export `scan_manager = ScanManager()` singleton.
Update all references in `main.py`.

Verify: `/api/v1/scan` and `/api/v1/scan/stop` work end-to-end.
Commit: `refactor: extract ScanManager to services/scanner.py`

#### 3c — `services/ghost.py`
Create `GhostService` class.
Decompose `_ghost_tick_impl` into 6 phase methods.
Move `_ghost_tick`, `_should_preserve_job_status`, `_job_eval_document`.
Move `_run_x_signal_scan`, `_run_free_source_scan` to `services/scout.py`.
Export `ghost_service = GhostService()` singleton.

Verify: ghost mode tick executes without error.
Commit: `refactor: extract GhostService to services/ghost.py`

#### 3d — Remaining services
Move in separate commits:
- `services/generator.py` — `_generate_one`, `_actuate`
- `services/provider_probe.py` — `_probe_provider_key`, `_sensitive`,
  `_log_sensitive_deprecation`

Verify after each.

---

### Phase 4 — Routes layer (AFK per router, HITL verification)

Extract one router file at a time. For each:
1. Create the router: `router = APIRouter(prefix="/api/v1", tags=[...])`
2. Move route handlers exactly — no logic changes yet
3. Resolve lazy imports to top-of-file imports
4. Add `response_model=` to each route
5. Add type annotations to handler params and returns
6. Register router in `main.py` with `app.include_router(...)`
7. Remove extracted routes from `main.py`
8. Verify all routes in that file return correct responses

Order:
- `routes/misc.py` — lowest risk (health, events, graph)
- `routes/settings.py` — 3 routes
- `routes/leads.py` — 12 routes
- `routes/profile.py` — 11 routes
- `routes/scan.py` — 6 routes (uses ScanManager)
- `routes/ingest.py` — 6 routes (apply DRY fix here)
- `routes/actions.py` — fire, generate, pipeline, pdf etc
- `routes/ws.py` — WebSocket endpoint

Commit per router: `refactor: extract routes/leads.py`

---

### Phase 5 — Clean up `main.py` (HITL)
After all extractions, `main.py` should contain only:
- Imports of routers, core modules
- `app = FastAPI(lifespan=lifespan)`
- Middleware registrations
- `app.include_router(...)` calls
- `lifespan` function
- `if __name__ == "__main__"` entrypoint

Target: under 100 lines.
Verify: full app launch, all 50 routes accessible, WS connects.
Commit: `refactor: main.py reduced to app entrypoint only`

---

### Phase 6 — Verification pass (HITL)
Run the full test suite.
Fix any import errors or broken references.
Run `black backend/` and `python -m mypy backend/ --ignore-missing-imports`.
Verify app launches from cold start.
Commit: `chore: post-refactor lint and type check pass`

---

## Rules that apply throughout

**One phase at a time.** Do not begin Phase N+1 until Phase N is
committed and verified.

**No logic changes during extraction.** Move code exactly as-is.
The only permitted changes during a move are:
- Lazy imports → top-of-file imports
- Adding type annotations
- Adding `response_model=`
- Fixes explicitly listed in the phase (e.g. `_int_cfg` catch type,
  `_CM` broadcast race fix, tuple constants)

**Verify before commit.** After every file extraction:
```bash
python -m py_compile backend/main.py
black backend/ --check
# then manually verify affected routes respond correctly
```

**If a move breaks something, stop.** Do not proceed. Report the
breakage with the exact error. Do not auto-fix without confirmation.

**Smart zone rule.** Each phase is one agent session.
Do not attempt two phases in one session.
If a phase is marked HITL, pause after producing the plan for
that phase and wait for approval before writing any code.

**Commit messages follow the format:**
```
refactor: <what was moved>
chore: <non-logic changes>
fix: <bug fixed during move>
```
