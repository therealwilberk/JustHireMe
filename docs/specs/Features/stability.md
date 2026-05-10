# Feature Spec — Phase 2: Stability

> Written before any code. Source of truth for scope, requirements, and validation.
> Agent: do not begin implementation until this file is approved.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | Stability — test infra, startup validation, error handling, concurrency |
| Roadmap phase | Phase 2 |
| Branch | `feature/phase2` |
| Status | `[ ] Draft / [ ] Approved / [ ] In Progress / [ ] Done` |
| Depends on | Phase 1 complete |
| Created | 2026-05-10 |
| Last updated | 2026-05-10 |

---

## 1. Goal

Backend is reliable, debuggable, and testable — errors surface clearly, tests are maintainable, startup validates real dependencies, ghost mode can't race with manual operations, and sidecar port discovery can't hang forever.

---

## 2. Background & Context

Phase 1 delivered on XDG paths, browser detection, and Linux builds, but left the test infrastructure in a messy state: identical fake classes are copy-pasted across three test files, `os.makedirs` is monkey-patched globally at import time, and core utility functions (`data_base()`, `chromium_executable()`) have zero tests. The `/health` endpoint returns a static "alive" status without checking actual dependencies. The ghost mode scheduler runs independently from manual scans with no mutual exclusion, risking concurrent DB writes. Sidecar stdout parsing in both Rust and the frontend has no timeout — if the sidecar fails silently during startup, the frontend polls forever. These gaps make debugging harder and regressions easier to miss.

---

## 3. Scope

### In scope

- [ ] Extract triplicated fakes into `tests/fakes.py` — shared `_FakeResult`, `_FakeConnection`, `_FakeSqlConnection`, `_FakeVectorStore`, `_install_storage_fakes()`, plus the `_FakeSemantic*` classes used by `test_regressions.py` and `test_api.py`
- [ ] Remove global `os.makedirs = lambda ...` monkey-patch from all three test files — replace with `unittest.mock.patch` targeting `db.client._ensure_dir`
- [ ] Add direct unit tests for `data_base()` covering the full priority chain (`JHM_APP_DATA_DIR` → `XDG_DATA_HOME` → `LOCALAPPDATA` → `~`) and the `_ensure_dir` fallback behaviour
- [ ] Add direct unit tests for `chromium_executable()` covering `$BROWSER` env var, `PLAYWRIGHT_CHROMIUM_EXECUTABLE`, Linux PATH candidates (google-chrome, chromium, firefox, brave), and the `None` fallback
- [ ] Enhance `/health` endpoint to probe DB writability, browser binary availability, and LLM API key presence — return structured dependency status alongside the existing alive/uptime response
- [ ] Add timeout to sidecar port/token stdout scanning in Rust (`tokio::time::timeout` around `rx.recv().await`) and a retry ceiling in the frontend polling loop
- [ ] Add concurrency lock for ghost mode — prevent `_ghost_tick()` from running concurrently with manual scans (`POST /api/v1/scan`) or re-evaluations (`POST /api/v1/leads/reevaluate`)

### Out of scope

- Full test coverage for all agents (scout, evaluator, generator, actuator — separate effort)
- Release CI / automated build testing (Phase 4)
- Wayland/Hyprland rendering fixes (Phase 4)
- OS keychain integration for API keys (upstream concern)
- Moving to pytest from unittest (use existing test runner)

---

## 4. Requirements

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | All three test files import fakes from a single `tests/fakes.py` module | `Must` |
| F2 | `os.makedirs` is not globally monkey-patched — only `db.client._ensure_dir` is mocked per-test where needed | `Must` |
| F3 | `data_base()` is tested for: `JHM_APP_DATA_DIR`, `XDG_DATA_HOME`, `LOCALAPPDATA`, fallback to `~`, and the `_ensure_dir` fallback when `os.makedirs` fails | `Must` |
| F4 | `chromium_executable()` is tested for: `$BROWSER` resolved via PATH, `PLAYWRIGHT_CHROMIUM_EXECUTABLE`, Linux candidate names, and the `None` return when no browser is found | `Must` |
| F5 | `GET /health` returns `dependencies` object with `database` (ok/error), `browser` (found/not_found), and `api_keys` (configured/missing) alongside existing fields | `Must` |
| F6 | Rust sidecar stdout recv loop has a timeout (e.g. 15s). If neither port nor token arrives within the window, a `sidecar-error` event is emitted and the loop stops waiting | `Must` |
| F7 | Frontend polling for port/token has a retry ceiling (e.g. 30 attempts ≈ 30s). If exceeded, a user-visible error is shown and polling stops | `Should` |
| F8 | Ghost mode acquires a lock before starting cycle work; manual scan/reevaluate acquire the same lock. Concurrent execution is prevented — second caller gets 409 or a clean skip | `Must` |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | No hardcoded values | All paths, timeouts, and limits via env vars or constants |
| NF2 | All errors caught and logged with context | No silent failures |
| NF3 | Structured logging at all boundaries | Use project logging library |
| NF4 | Existing tests continue to pass | No regressions from refactoring |
| NF5 | `_ensure_dir` mock does not break Windows test environments | Use `@mock.patch` with `autospec` where possible |
| NF6 | Health endpoint responds in < 200ms | Lightweight probes — no network calls |

---

## 5. Implementation Plan

- [ ] **Task 1 (parallel):** Create `tests/fakes.py` — extract shared fakes + `_install_storage_fakes()` from all three test files. Update imports in `test_api.py`, `test_graph.py`, `test_regressions.py`
- [ ] **Task 2 (parallel):** Remove global `os.makedirs` monkey-patch from `test_api.py`, `test_graph.py`, `test_regressions.py`. Replace with targeted `mock.patch.object(os, "makedirs")` inside `_install_storage_fakes()` so it's applied before any backend module loads
- [ ] **Task 3 (parallel):** Write unit tests for `data_base()` in a new `test_paths.py` — cover priority chain, `_ensure_dir` fallback
- [ ] **Task 4 (parallel):** Write unit tests for `chromium_executable()` in the same `test_paths.py` — cover `$BROWSER`, `PLAYWRIGHT_CHROMIUM_EXECUTABLE`, Linux candidates, `None` fallback
- [ ] **Task 5:** Enhance `GET /health` — add `dependencies` block with lightweight probes for DB (try `SELECT 1` against SQLite), browser (`chromium_executable()` result), and API keys (check configured settings / env vars)
- [ ] **Task 6:** Add timeout to Rust sidecar stdout scanning — wrap `rx.recv().await` with `tokio::time::timeout`. Kill sidecar process on timeout. Add `tokio` dep to `Cargo.toml`
- [ ] **Task 7:** Add retry ceiling to frontend polling in `useWS.ts` — stop after 30 attempts (30s), set user-visible sidecar error. Tear down event listeners on exhaustion
- [ ] **Task 8:** Add concurrency lock for ghost mode — use `asyncio.Lock()` with non-blocking `wait_for(lock.acquire(), timeout=0)` so `_ghost_tick()` skips silently if lock is held, and manual scan/reevaluate return 409. Preserve existing `_scan_task.done()` / `_reevaluate_task.done()` guards as complementary layer

> Tasks 1–4 can run in parallel. Tasks 5–8 are sequential (each builds on the test infra from 1–4).

---

## 6. API / Interface Design

### Enhanced `GET /health` response

```
GET /health

Response 200:
{
  "status": "alive",
  "uptime_seconds": 42.0,
  "timestamp": "2026-05-10T12:00:00Z",
  "log_level": "INFO",
  "dependencies": {
    "database": {
      "status": "ok",              // "ok" | "error"
      "latency_ms": 3
    },
    "browser": {
      "status": "found",           // "found" | "not_found"
      "path": "/usr/bin/google-chrome"  // null if not found
    },
    "api_keys": {
      "status": "configured",      // "configured" | "missing"
      "configured_providers": ["openai", "anthropic"]  // [] if none
    }
  }
}
```

### Ghost mode concurrency lock (internal)

```python
_ghost_lock = asyncio.Lock()

# Used by _ghost_tick(), _run_scan_task(), _run_reevaluate_jobs_task()
# Non-blocking acquisition — if lock is held, skip/409 instead of waiting
```

---

## 7. Error Handling Map

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| DB unwritable on health check | `dependencies.database.status = "error"`, log full details | Yes — WARN | Included in health response |
| No browser found on health check | `dependencies.browser.status = "not_found"`, `path = null` | No (noisy) | N/A — informational only |
| No API keys configured on health check | `dependencies.api_keys.status = "missing"`, empty providers list | Yes — WARN | N/A — informational only |
| Sidecar stdout timeout (Rust) | Emit `sidecar-error` with "Sidecar startup timed out" message | Yes — in Rust side | "Sidecar startup timed out — check backend logs" |
| Frontend port/token poll exhausted | Set `sidecarError` state and stop polling | N/A | "Sidecar failed to start — check logs" |
| Ghost mode blocked by running scan | `_ghost_tick()` returns early without logging error | Yes — INFO | Nothing (silent skip) |
| Manual scan blocked by running ghost | `POST /api/v1/scan` returns 409 | Yes — WARN | "Scan already in progress (ghost mode active)" |

---

## 8. Validation Checklist

### Automated tests

- [ ] `tests/fakes.py` exists and is imported by all three test files
- [ ] All existing tests pass with fakes imported from shared module: `cd backend && uv run python -m pytest tests/ -v`
- [ ] `os.makedirs` monkey-patch removed — grep confirms zero occurrences in test files
- [ ] `test_paths.py::test_data_base_jhm_app_data_dir` — env var takes priority
- [ ] `test_paths.py::test_data_base_xdg_data_home` — XDG used on Linux when JHM not set
- [ ] `test_paths.py::test_data_base_localappdata` — LOCALAPPDATA used on Windows
- [ ] `test_paths.py::test_data_base_fallback` — expanduser used when no env var set
- [ ] `test_paths.py::test_data_base_ensure_dir_fallback` — fallback dir used when makedirs fails
- [ ] `test_paths.py::test_chromium_executable_browser_env` — $BROWSER resolved via PATH
- [ ] `test_paths.py::test_chromium_executable_playwright_env` — PLAYWRIGHT_CHROMIUM_EXECUTABLE
- [ ] `test_paths.py::test_chromium_executable_linux_candidates` — candidate names via shutil.which
- [ ] `test_paths.py::test_chromium_executable_not_found` — returns None
- [ ] `test_paths.py` does not import from kuzu/lancedb/sqlite3 (stays fast)

### Manual checks

- [ ] `curl GET /health` — verify dependencies block present with correct statuses
- [ ] Sidecar startup without browser binary — confirm `/health` shows `browser.not_found`
- [ ] Trigger ghost mode while scan is running — confirm ghost skips (log check)
- [ ] Trigger manual scan while ghost is running — confirm 409 returned
- [ ] Run tests on Windows — confirm no regression (no `os.makedirs` monkey-patch to break)

### Code quality gates

- [ ] No hardcoded values in any new or modified file
- [ ] All error paths handled and logged
- [ ] `.env.example` updated if new env vars added
- [ ] No `console.log` / `print()` left in code
- [ ] All new functions have explicit return types / type hints
- [ ] Branch is clean — no unrelated changes
- [ ] Windows paths still work (no regression)

---

## 9. Ripple Effects

<!-- Every change has secondary effects. This section maps them per task to
     prevent surprises during and after implementation. -->

### Task 1 — Extract fakes

| File | Nature of change | Cascade |
|------|------------------|---------|
| `tests/fakes.py` | NEW — single source for all fake classes | No cascade; pure refactor |
| `tests/test_api.py` | DELETE fake class defs, import from `fakes` | Must keep same module-level `_install_storage_fakes()` call ordering |
| `tests/test_graph.py` | DELETE fake class defs, import from `fakes` | Same as above; `_FakeSemantic*` defs not used here but import is harmless |
| `tests/test_regressions.py` | DELETE fake class defs, import from `fakes` | Same as above; `_FakeSemantic*` classes must be included in shared module |
| `tests/test_mcp_server.py` | No change | Does not import from storage modules; unaffected |

### Task 2 — Remove `os.makedirs` monkey-patch

| File | Nature of change | Cascade |
|------|------------------|---------|
| `tests/fakes.py` | `_install_storage_fakes()` now does `mock.patch.object(os, "makedirs", return_value=None).start()` | ⚠️ CRITICAL: patch must be applied *before* any backend module is imported, because `db.client._ensure_dir()` calls `os.makedirs()` at import time |
| `tests/test_api.py` | Remove line `os.makedirs = lambda ...` | If `_install_storage_fakes()` mock is correctly in place, no behaviour change. Must verify ordering: env vars → fakes install → imports |
| `tests/test_graph.py` | Same as above | Same |
| `tests/test_regressions.py` | Same as above | Same |
| All test files | Import order invariant | Current: `os.environ["LOCALAPPDATA"]=...` → `os.makedirs=lambda ...` → `_install_storage_fakes()` → `import`. New: env vars → `_install_storage_fakes()` (which patches `os.makedirs`) → `import` |

> ⚠️ The `mock.patch.object(os, "makedirs")` inside `_install_storage_fakes()` patches the `os` module object directly, so when `db.client` does `import os; os.makedirs(...)` it sees the mocked version. This replaces the global lambda with a proper `unittest.mock.MagicMock` that can be inspected, asserted, and cleaned up.

### Task 3 — Unit tests for `data_base()`

| File | Nature of change | Cascade |
|------|------------------|---------|
| `tests/test_paths.py` | NEW | Must call `_install_storage_fakes()` before `from db.client import data_base` because importing `db.client` triggers module-level `_ensure_dir()` call |
| `tests/test_paths.py` | Tests set `os.environ` per test | `data_base()` reads env vars fresh each call. Tests must use `@mock.patch.dict(os.environ, ...)` to set env vars before calling `data_base()` |
| `tests/test_paths.py` | `_ensure_dir` fallback test | Must mock `os.makedirs` to raise an exception, then call `data_base()` again via import or re-import. The module-level `_b = data_base()` already ran once — subsequent calls to `data_base()` work fine since the function re-reads env vars |

### Task 4 — Unit tests for `chromium_executable()`

| File | Nature of change | Cascade |
|------|------------------|---------|
| `tests/test_paths.py` | Test additions in same file | `chromium_executable()` uses `shutil.which()`, `os.path.exists()`, `os.environ.get()`. Tests must mock these. No backend side effects on import |
| `tests/test_paths.py` | Import of `agents.browser_runtime` | Safe — module-level code is only `_log = get_logger(...)` and a constant. No storage or IO at import time |

### Task 5 — Enhance `/health` endpoint

| File | Nature of change | Cascade |
|------|------------------|---------|
| `backend/main.py` | Enhance `health()` function | Add import of `chromium_executable` from `agents.browser_runtime`. This is `main.py`'s first import from that module — minimal overhead, no side effects |
| `backend/main.py` | DB probe in health | Simple `SELECT 1` against SQLite. Must use existing `db.client.sql` connection path. If DB is unavailable, gracefully set status to `"error"` — never crash the endpoint |
| `backend/main.py` | API key probe | Reuse logic similar to `/api/v1/settings/validate` but lighter: check if at least one provider key is configured in env or settings. No network calls |
| `backend/main.py` | Health latency | Spec requires <200ms. DB probe is local (SQLite query < 5ms). Browser probe is `chromium_executable()` call (< 10ms). API key probe is env/settings read (< 1ms). Total well under 200ms. |
| Frontend consumers | None | Frontend does not call `/health` endpoint. Only external monitoring tools. No UI impact. |

### Task 6 — Rust sidecar timeout

| File | Nature of change | Cascade |
|------|------------------|---------|
| `src-tauri/Cargo.toml` | Add `tokio = { version = "1", features = ["time"] }` | Tauri already depends on tokio; adding it explicitly is safe. The `time` feature is minimal. |
| `src-tauri/src/lib.rs` | Wrap `rx.recv().await` with `tokio::time::timeout` | ⚠️ Must restructure from `while let Some(event) = rx.recv().await` to a loop with timeout. On timeout: emit `sidecar-error` event AND kill the sidecar child process via `SidecarChild` state |
| `src-tauri/src/lib.rs` | Sidecar process cleanup on timeout | After timeout, retrieve child from `SidecarChild` state, call `child.kill()`, and break the loop. The `shutdown_sidecar()` function uses `kill_process_tree()` — can reuse that |
| Frontend | `sidecar-error` event fires on timeout | Frontend event listener (useWS.ts line 101) sets `sidecarError` state. UI already has paths to display this error. |

### Task 7 — Frontend retry ceiling

| File | Nature of change | Cascade |
|------|------------------|---------|
| `src/hooks/useWS.ts` | Add retry counter and cap at 30 | Current: `while !cancelled && (!token || !currentPort)` — polls forever. New: stop polling after 30 attempts, set `sidecarError`, clear interval |
| `src/hooks/useWS.ts` | Tear down event listeners on exhaustion | If polling stops, the `sidecar-port`/`sidecar-token`/`sidecar-error` event listeners should also be unregistered to prevent stale callbacks |

### Task 8 — Ghost mode concurrency lock

| File | Nature of change | Cascade |
|------|------------------|---------|
| `backend/main.py` | Add `_ghost_lock = asyncio.Lock()` | New module-level global near `_scan_stop` / `_reevaluate_stop` |
| `backend/main.py` | `_ghost_tick()` acquires lock with `wait_for(..., timeout=0)` | If lock is held: log INFO and return silently (ghost skips gracefully). If acquired: release in `finally` block |
| `backend/main.py` | `scan()` checks `_ghost_lock.locked()` | Returns 409 if ghost is running. Existing `_scan_task.done()` check is preserved — it prevents double manual scans independently of ghost lock |
| `backend/main.py` | `reevaluate_jobs()` checks `_ghost_lock.locked()` | Same as scan. Returns 409 if ghost is running. |
| `backend/main.py` | `_run_scan_task()` acquires ghost lock | Ensures scan body doesn't run if ghost tick snuck in between HTTP check and task creation |
| `backend/main.py` | `_run_reevaluate_jobs_task()` acquires ghost lock | Same as scan |
| **DEGRADED BEHAVIOUR** | Both locks active | Two independent guard layers: (a) `_scan_task.done()` / `_reevaluate_task.done()` prevents double manual ops, (b) `_ghost_lock` prevents ghost+manual concurrency. Neither replaces the other. |
| **DEADLOCK RISK** | `_ghost_tick()` cannot re-enter | Ghost tick is a single APScheduler job — it will never try to acquire the lock twice in the same call stack. No re-entrancy concern. |
| **DEADLOCK RISK** | `_run_scan()` vs `_run_reevaluate_jobs()` | Both acquire the same ghost lock, and neither calls the other. No circular dependency. `_scan_task.done()` guard prevents a scan from starting while another scan runs. Safe. |

### Cross-cutting concern: Import order in test files

All test files that import from `db.client` (or any module that imports `db.client`) must follow this exact ordering:

```python
# 1. Set env vars for deterministic paths
os.environ["JHM_APP_DATA_DIR"] = "/tmp/jhm-test"

# 2. Install all storage fakes (patches os.makedirs, kuzu, lancedb, sqlite3)
from tests.fakes import _install_storage_fakes
_install_storage_fakes()

# 3. Now import backend modules — os.makedirs is already mocked
from db.client import data_base
```

**Files affected by this ordering requirement:** `test_api.py`, `test_graph.py`, `test_regressions.py`, `test_paths.py` (new).

**Files NOT affected:** `test_mcp_server.py` (imports only `mcp_server._handle`, no storage deps).

---

## 10. Open Questions

<!-- Unresolved decisions that must be answered before or during implementation.
     Clear these before marking the spec as Approved.
     Move to Decisions Log once resolved. -->

| # | Question | Raised by | Status |
|---|----------|-----------|--------|
| Q1 | What timeout value for sidecar stdout scan? | Agent | `[ ] Open` |
| Q2 | How many retries for frontend polling ceiling? | Agent | `[ ] Open` |
| Q3 | Should health endpoint remain open (no auth) or require valid token? | Agent | `[ ] Open` — currently no auth for `/health` |

---

## 11. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-10 | Fakes extracted into `tests/fakes.py` | Single source of truth, no copy-paste drift | Inline per file (current mess) |
| 2026-05-10 | `asyncio.Lock` for ghost mode concurrency | Simple, matches existing asyncio pattern | threading.Lock, APScheduler coalesce, Redis lock |
| 2026-05-10 | Health endpoint stays unauthenticated | Matches current behaviour; breaking change to require auth | Requiring auth (would break monitoring tools) |

---

*Last updated: 2026-05-10 — Agent*
