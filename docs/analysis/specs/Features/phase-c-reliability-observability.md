# Feature Spec — Phase C: Reliability, Observability & Concurrency

> Written before any code. Source of truth for scope, requirements, and validation.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | Reliability, Observability & Concurrency |
| Roadmap phase | Phase C |
| Branch | `feature/phase-c-reliability-observability` |
| Type | `Infra` (horizontal — exempt from vertical-slice rule) |
| Mode | `AFK` (all tasks deterministic per audit analysis) |
| Status | `[x] Complete` |
| Depends on | Phase A (config layer for constants extracted from error paths) |
| Blocks | Phase D+ |
| Created | 2026-05-14 |
| Last updated | 2026-05-14 |

---

## 1. Goal

Silent failures become visible, concurrent operations are safe, and the application emits structured logs with correlation context — so production incidents can be traced from one or two log lines without reconstructing the entire execution path manually.

---

## 2. Background & Context

The codebase contains **40 `except: pass` instances** in production code that silently swallow exceptions — concentrated in `backend/db/client.py` (21), `backend/main.py` (7), and `backend/agents/` (12). These hide the very events operators need to see, erase evidence, and conceal partial failures.

The WebSocket `_CM` class (`backend/main.py:177`) uses a plain `list[WebSocket]` with no locks — `add()`, `remove()`, and `broadcast()` can race between coroutines, and `broadcast()` mutates the list during iteration.

SQLite connections are opened fresh for each of 30+ call sites with no WAL mode, no connection pooling, no busy timeout — fragile under concurrent access.

Logging is ad hoc: only 2 files use the custom `get_logger()`, the rest use `print()` or raw `logging.getLogger`. No structured format, no correlation context, no file handler.

The frontend silently swallows save failures in `SettingsModal` (no `catch` block) and `ProfileView` (delete errors only `console.error`, save handlers have no try/catch at all).

Phase A established the config layer including `config/logging.py` schema. Phase B established the `resolve_secret()` pattern. Phase C makes the operational surface predictable.

---

## 3. Scope

### In scope

- [x] **Task 5 — WebSocket `_CM` Async-Safety**: Add `asyncio.Lock` to `_CM` class, safe mutation semantics for `add`/`remove`/`broadcast`. *(Done)*
- [x] **Task 6 — SQLite WAL Mode & Connection Management**: Set `PRAGMA journal_mode=WAL` on all connections, add connection wrapper, set busy timeout. *(Done)*
- [x] **Task 7 — Frontend Error Handling**: `SettingsModal` save failure shows user-facing error. `ProfileView` delete/save failures show user-facing error. *(Done)*
- [x] **Task 8 — Build Configuration Fixes**: Enable `createUpdaterArtifacts`, set platform-specific bundle targets. *(Done)*
- [x] **Task 11 — Frontend Reliability & User-Truthfulness Tests**: Add vitest component tests for SettingsModal and ProfileView error handling. *(Done)*
- [x] **Task 4 — Replace Silent Exception Suppression With Structured Error Reporting**: Replace every `except: pass` with logged warnings or structured errors carrying identifiers. *(Done)*
- [x] **Task 9 — Structured Logging Infrastructure**: Centralized `get_logger()` with consistent format/levels. Correlation ID propagation via `contextvars`, contextual fields, optional `RotatingFileHandler`. *(Done)*

### Out of scope

- OS keychain integration (deferred — not on current roadmap)
- Monolith splitting (`main.py`, `db/client.py` — deferred)
- New feature work (Phase D+)
- Frontend component tests (full React UI test suite — upstream problem)

---

## 4. Requirements

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | Every `except: pass` in production code replaced with logged warning or structured error | `Must` |
| F2 | Each replaced error path carries identifiers (request ID, job ID, lead ID, node name, subsystem) where available | `Must` |
| F3 | Recoverable errors emit structured log (warning/error with context) and continue via fallback | `Must` |
| F4 | Terminal errors log once and stop in a controlled way | `Must` |
| F5 | Tracebacks preserved in exception logs — not reduced to strings | `Must` |
| F6 | Logging configured centrally — no ad hoc `logging.basicConfig`/`getLogger` in random modules | `Must` |
| F7 | Logs carry consistent fields across all error paths (timestamp, level, logger, message, exception_info, correlation_id) | `Must` |
| F8 | WebSocket `_CM` class is safe under concurrent async `add`/`remove`/`broadcast` | `Must` |
| F9 | SQLite connections use `PRAGMA journal_mode=WAL` | `Must` |
| F10 | SettingsModal save failure shows user-facing error message | `Must` |
| F11 | ProfileView delete/save failures show user-facing error message | `Must` |
| F12 | `createUpdaterArtifacts` set to `true` in Tauri config | `Should` |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | Error path changes must not change user-visible behavior for happy paths | Degradation is observable, not breaking |
| NF2 | Exception suppression replacements must preserve existing graceful degradation | Silent → audible, not silent → crash |
| NF3 | Log format change must not break existing log-based tooling | Add fields, don't remove them |
| NF4 | WebSocket broadcasts remain non-blocking under lock | Lock held only for list mutation, not per-send |

> NF1–NF3 are inherited from `tech-stack.md` and apply to every feature.
> NF4 is Phase C-specific.

---

## 5. Implementation Plan

### Vertical slice check _(Feature phases only — skip for Infra/Chore)_
- N/A (Infra phase — horizontal reliability work across all layers)

### Tasks

- [x] `[AFK]` **Task 5 — WebSocket Async-Safety:** Add `asyncio.Lock` to `_CM.__init__()`, guard `add()`/`remove()` with lock, refactor `broadcast()` to snapshot under lock then send outside lock. Write 15 concurrency tests.
- [x] `[AFK]` **Task 6 — SQLite WAL Mode:** Add `get_sql_connection()` wrapper with `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`. Replace all 34 call sites. Write 10 pragma verification tests.
- [x] `[AFK]` **Task 7 — Frontend Error Handling:** Add `saveError`/`actionError` state and catch blocks to `SettingsModal.tsx` (save) and `ProfileView.tsx` (delete, saveEdit, saveCandidate). Display user-facing error messages.
- [x] `[AFK]` **Task 8 — Build Configuration:** Set `createUpdaterArtifacts: true`, add `deb` to bundle targets in `tauri.conf.json`.
- [x] `[AFK]` **Task 11 — Frontend Reliability & User-Truthfulness Tests:** Add vitest component tests for SettingsModal (9) and ProfileView (11) verifying error visibility, retry, loading state, actionable messaging, and no false-success behavior. *(Done)*
- [x] `[AFK]` **Task 4 — Replace Silent Exception Suppression:** Replace all 40 `except: pass` instances across `db/client.py`, `main.py`, and `agents/` with logged warnings carrying identifiers. Document intentional passes (WebSocket ping/disconnect) with comments. *(Done)*
- [x] `[AFK]` **Task 9 — Structured Logging:** Centralize all `print()`/ad hoc logger calls through `backend/logger.py`. Add structured fields (correlation ID, subsystem, traceback). Add optional file handler. *(Done)*

**Blocking relationships:**
- Tasks 5–8, 11, 4 independent (no cross-blocking) — completed in parallel
- Task 9 core infra done (logger.py, get_logger adoption); enhancements (correlation IDs, file handler) have no hard blockers

---

## 6. API / Interface Design

This phase is Infra — no new API endpoints, schemas, or CLI commands. Changes are internal:

- **`_CM` class**: `add()` and `remove()` now async with `asyncio.Lock`. `broadcast()` uses snapshot pattern.
- **`get_sql_connection()`**: New function in `db/client.py` returning pragma-configured connections.
- **SettingsModal/ProfileView**: Add error state variables and catch blocks — no API contract changes.
- **`tauri.conf.json`**: `createUpdaterArtifacts` toggled `true`, `targets` gains `"deb"`.

---

## 7. Error Handling Map

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| Vector store add fails (fire-and-forget) | Log WARNING with entity ID, continue | Yes — WARNING | None (background op) |
| Profile snapshot save fails | Log WARNING with profile ID, continue | Yes — WARNING | None (background op) |
| Duplicate entity insert (education, cert, etc.) | Log INFO, skip, continue | Yes — INFO | None (expected idempotency) |
| Page screenshot fails during portfolio ingest | Log WARNING with URL, continue with partial result | Yes — WARNING | None (degraded graceful) |
| JSON cache parse fails | Log DEBUG with cache key, continue | Yes — DEBUG | None (transient) |
| Scoring engine budget parse fails | Log WARNING with raw value, default to 0 | Yes — WARNING | None (degraded score) |
| Quality gate date parse fails | Log DEBUG with raw date string, treat as missing | Yes — DEBUG | None (permissive) |
| WebSocket concurrent add/remove race | No longer possible — locked mutation | N/A | N/A |
| SQLite concurrent write contention | Retry up to 5s via busy_timeout | WARNING on timeout | N/A |
| SettingsModal API save fails | Catch error, set error state, show red message | Yes — ERROR | "Failed to save settings: {message}" |
| ProfileView delete/save fails | Catch error, set error state, show red message | Yes — ERROR | "Failed to {action}: {message}" |

---

## 8. Validation Checklist

### Task 4 — Silent Exception Suppression *(Done)*

- [x] Every `except: pass` in production code replaced with logged warning/error carrying identifiers
- [x] `backend/db/client.py`: all 21 instances classified and replaced (no bare `pass`)
- [x] `backend/main.py`: all 7 instances classified and replaced (or documented)
- [x] `backend/agents/`: all 12 instances classified and replaced (no bare `pass`)
- [x] Recoverable errors log and continue — no behavior change for happy paths
- [x] Terminal errors log once and stop in controlled way
- [x] Tracebacks preserved via `exc_info=True` or `logger.exception()`

### Task 5 — WebSocket Async-Safety *(Done)*

- [x] `asyncio.Lock` guards `_CM.add()` and `_CM.remove()`
- [x] `broadcast()` snapshots list under lock, sends outside lock
- [x] 15 tests verify concurrent add/remove/broadcast under asyncio

### Task 6 — SQLite WAL/Pragmas *(Done)*

- [x] `PRAGMA journal_mode=WAL` set on all new connections
- [x] `PRAGMA foreign_keys=ON` set on all new connections
- [x] `PRAGMA busy_timeout=5000` set for contention resilience
- [x] `get_sql_connection()` wrapper replaces all raw `_sq.connect(sql)` calls (34 sites)
- [x] 10 tests verify pragma behavior (WAL persists, FK enforcement, busy timeout)

### Task 7 — Frontend Error Handling *(Done)*

- [x] SettingsModal save failure shows user-facing error (not silent)
- [x] ProfileView delete failure shows user-facing error
- [x] ProfileView saveEdit shows user-facing error on failure
- [x] ProfileView saveCandidate shows user-facing error on failure
- [x] No unhandled promise rejections in save/delete handlers

### Task 11 — Frontend Reliability & User-Truthfulness Tests *(Done)*

- [x] SettingsModal tests (9): error visibility for 500/422/503/network errors, success state, loading indicator reset after failure, retry clears error, stale success cleared by subsequent failure
- [x] ProfileView deleteItem tests (5): error visibility on 500, no false error on success, server detail on 422, retry clears error, fallback on thrown error
- [x] ProfileView saveEdit tests (2): error visibility on 500, server detail on 422
- [x] ProfileView saveCandidate tests (4): error visibility on 500, server detail on 422, retry clears error, fallback on thrown error
- [x] Tests simulate backend failure responses (500, 422, network error) and verify: explicit error state, no false-success, retry interaction, stale state clearing, loading indicator resolution, actionable error messages
- [x] `renderView` helper uses unique DOM selector (`"1 SKILLS"` pill text) to avoid multi-element match
- [x] Full test suite passes: 33 frontend tests + 280 backend tests

### Task 8 — Build Config *(Done)*

- [x] `createUpdaterArtifacts` set to `true`
- [x] Bundle targets include `["appimage", "deb"]`

### Task 9 — Structured Logging *(In Progress)*

### Task 9 — Structured Logging *(Done)*

- [x] Centralized `get_logger()` in `backend/logger.py` — all agent modules use it
- [x] Log format: `%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s` with contextual fields (`lead=`, `job=`, `flow=`, `sub=`, `node=`, `DEGRADED`, `RETRYING`)
- [x] Zero `print()` calls in production code (remaining print calls are in operational scripts only)
- [x] Zero ad hoc `logging.getLogger` in production code (all through `get_logger()`)
- [x] Log level configurable via env var (`JHM_LOG_LEVEL`)
- [x] Logs go to stderr (consistent with CLI convention)
- [x] `logger.propagate = False` — no duplicate log lines
- [x] **CorrelationContext**: `contextvars`-based `CorrelationContext` dataclass with `correlation_id`, `workflow_type`, `lead_id`, `job_id`, `node`, `subsystem`, `degraded`, `retrying` fields
- [x] **Correlation ID propagation**: `new_context()`/`set_context()`/`reset_context()`/`enrich()` functions with `try/finally` lifecycle discipline at every entrypoint
- [x] **FastAPI middleware**: `correlation_context_middleware` sets context per request, injects `X-Correlation-ID` response header, accepts client-initiated IDs
- [x] **Background job entrypoints**: `_ghost_tick_impl`, `run_pipeline`, `_run_x_signal_scan`, `_run_free_source_scan` wrapped with `try/finally` context lifecycle
- [x] **File handler**: Optional `RotatingFileHandler` via `settings.logging.log_file` config with configurable `maxBytes` and `backupCount`
- [x] **Immutability**: `enrich()` uses `dataclasses.replace()`, returns `Token` for chained cleanup
- [x] **CorrelationFilter**: Injects context fields into every `LogRecord` (`correlation_id`, `_ctx_subsystem`, `_ctx_workflow`, `_ctx_lead`, `_ctx_job`, `_ctx_node`, `_ctx_degraded`, `_ctx_retrying`)
- [x] **ContextFormatter**: Appends extra fields to log output (`| lead= job= flow= ...`)
- [x] 18 tests verify context isolation, enrich immutability, CorrelationFilter output, ContextFormatter output, file handler creation, middleware `X-Correlation-ID` header propagation

### Code quality gates

- [x] Zero `except: pass` remaining in production code (verify with `git grep 'except.*:.*pass' backend/ | grep -v test`)
- [x] All changed files have explicit type hints
- [x] Zero new `print()` calls in production code (remaining print calls are in operational scripts: `force_model.py`, `run_diagnostics.py`, `update_settings.py`)
- [x] Branch is clean — no unrelated changes
- [x] Full test suite passes: **298 backend tests** + **33 frontend tests** = **331 total**

---

## 9. Open Questions

| # | Question | Raised by | Status |
|---|----------|-----------|--------|
| Q1 | Should the `_safe_call()` helper in `db/client.py` log as WARNING or ERROR for fire-and-forget vector ops? | Agent | `[x] Resolved` — WARNING. Fire-and-forget means degraded but non-terminal. ERROR reserved for terminal failures. |
| Q2 | Should structured logging use JSON format or enriched plain-text with correlation IDs? | Agent | `[x] Resolved` — Plain text with correlation IDs. JSON deferred unless log aggregation tooling requires it. |
| Q3 | For SQLite: single shared connection with WAL vs simple connection pool? | Agent | `[x] Resolved` — per-call connection with WAL is sufficient for current access pattern |
| Q4 | What correlation ID format to use (UUID, request-scoped, job-scoped)? | Agent | `[ ] Open` |

---

## 10. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-14 | Task 4 (silent exception replacement) prioritized before logging infrastructure | Need to know what we're logging before defining format — replacement reveals log patterns | Logging format first, then replacement |
| 2026-05-14 | Workstreams 4–9 are independent — no cross-blocking | Each addresses disjoint subsystems (db, websocket, sqlite, frontend, build) | Sequential ordering |
| 2026-05-14 | `_CM` uses `asyncio.Lock` with snapshot-broadcast pattern | Narrow lock duration, no contention across `await w.send_text()` | Global lock around everything |
| 2026-05-14 | `get_sql_connection()` per-call wrapper, not connection pool | Current access pattern (30+ independent calls) doesn't need pooling; WAL suffices for concurrent reads | Thread-local connections, single shared connection |
| 2026-05-14 | Frontend errors displayed inline (not toasts/modals) | Matches existing `profileErr` pattern in ProfileView, minimal component restructuring | Toast notifications, alert() |
| 2026-05-14 | Bundle targets expanded to `["appimage", "deb"]` | `package:linux:all` script already produces both; config should match the intended deployment model | AppImage-only, deb-only |
| 2026-05-14 | `_safe_call()` logs as WARNING for fire-and-forget vector ops | Fire-and-forget is degraded but non-terminal. ERROR reserved for terminal failures. | ERROR |
| 2026-05-14 | Structured logging uses enriched plain-text, not JSON | JSON deferred unless log aggregation tooling requires it. Current format includes timestamp/level/name/message. | JSON format |
| 2026-05-14 | Task 4 (except:pass) marked Done — zero bare except blocks remaining | git grep confirms zero except:pass in production code. 23 observability tests verify replacements. | — |
| 2026-05-14 | Task 9 (Structured Logging) marked Done | CorrelationContext with contextvars, CorrelationFilter, ContextFormatter, RotatingFileHandler, middleware, background entrypoints. 18 tests. 298 backend tests pass. | — |

---

_Last updated: 2026-05-14 — Agent_
