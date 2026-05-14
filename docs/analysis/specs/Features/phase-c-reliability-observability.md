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
| Mode | `TBD` |
| Status | `[~] In Progress` |
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

- [ ] **Task 4 — Replace Silent Exception Suppression With Structured Error Reporting**: Replace every `except: pass` with logged warnings or structured errors carrying identifiers (request ID, job ID, lead ID, node name, subsystem). Standardize logging entry points.
- [ ] **Task 5 — Structured Logging Infrastructure**: Centralized logging configuration, consistent format/levels/fields, file handler, correlation context propagation.
- [ ] **Task 6 — WebSocket `_CM` Async-Safety**: Add `asyncio.Lock` to `_CM` class, safe mutation semantics for `add`/`remove`/`broadcast`.
- [ ] **Task 7 — SQLite WAL Mode & Connection Management**: Set `PRAGMA journal_mode=WAL` on all connections, add connection pooling or reuse, set busy timeout.
- [ ] **Task 8 — Frontend Error Handling**: `SettingsModal` save failure shows user-facing error. `ProfileView` delete/save failures show user-facing error. No silent promise rejections.
- [ ] **Task 9 — Build Configuration Fixes**: Enable `createUpdaterArtifacts`, verify platform-specific bundle targets.

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

---

## 5. Implementation Plan

### Workstream 4 — Replace Silent Exception Suppression

**Core principle:** Read each suppressed exception in context before changing it. Not every suppressed exception should become a fatal error. Some paths degrade gracefully — but graceful degradation still needs a log entry, severity level, and enough context to explain what happened.

- [ ] **Task 4.1:** `backend/db/client.py` (21 instances) — classify each suppressed exception:
  - Fire-and-forget vector store ops (`_add_skill_vec`, `_add_project_vec`, `_delete_vec_rows`): log WARNING with operation name and candidate/entity ID, continue
  - Profile snapshot save/refresh: log WARNING with profile ID, continue
  - "Already exists" handlers (`add_education`, `add_certification`, `add_achievement`): log INFO with entity name, continue
  - Candidate relation queries: log WARNING with candidate ID, continue
  - Column migration (already-exists): log DEBUG, continue
  - Consolidate into a `_safe_call(label: str, fn, **context)` helper to reduce boilerplate

- [ ] **Task 4.2:** `backend/main.py` (7 instances) — classify each suppressed exception:
  - `broadcast()` agent event recording: log WARNING with agent event type, continue
  - Post-ingestion snapshot refresh: log WARNING with lead ID, continue
  - Skill import/bulk ingest/GitHub ingestor: log WARNING with ingest source, continue
  - Skill add from identity form: log WARNING, continue
  - WebSocket ping timeout / disconnect: these are already appropriate as `pass` — document intent with comment

- [ ] **Task 4.3:** `backend/agents/` (12 instances) — classify each suppressed exception:
  - Page screenshot failures (`portfolio_ingestor.py`, `actuator.py`): log WARNING with URL, continue
  - Ingestor upsert/relation/vector fallbacks: log WARNING with entity type, continue
  - JSON cache parse failures (`selectors.py`): log DEBUG with cache key, continue
  - Actuator unmatched labels / form fill / submit button: log WARNING with step context, continue
  - Scoring engine budget parsing (`ValueError`): log WARNING with raw value, default to 0
  - Quality gate date parsing: log DEBUG with raw date string, continue

### Workstream 5 — Standardize Logging Infrastructure

- [ ] **Task 5.1:** Audit all `print()` / `_log = logging.getLogger(...)` / ad hoc `basicConfig` calls in production code. Centralize through `backend/logger.py`.
- [ ] **Task 5.2:** Add structured fields to log format: correlation ID (request/job/lead), subsystem name, exception traceback preservation.
- [ ] **Task 5.3:** Add optional file handler to logging config (controlled by env var or config).
- [ ] **Task 5.4:** Write tests for logging behavior: log level resolution, format consistency, exception context preservation, `config/logging.py` env var override.

### Workstream 6 — WebSocket Async-Safety

- [ ] **Task 6.1:** Add `asyncio.Lock` to `_CM.__init__()`, guard `add()` and `remove()` with lock.
- [ ] **Task 6.2:** Refactor `broadcast()` to snapshot `_ws` under lock, then send outside lock — prevents holding lock across `await w.send_text()`.
- [ ] **Task 6.3:** Write tests for `_CM` concurrent `add`/`remove`/`broadcast` under asyncio.

### Workstream 7 — SQLite WAL Mode

- [ ] **Task 7.1:** Add `PRAGMA journal_mode=WAL` to initial SQLite connection setup in `backend/db/client.py:_init_sql()`.
- [ ] **Task 7.2:** Add `PRAGMA busy_timeout=5000` for concurrent access resilience.
- [ ] **Task 7.3:** Add `PRAGMA foreign_keys=ON` for referential integrity.
- [ ] **Task 7.4:** Write tests that verify pragmas are set on new connections.

### Workstream 8 — Frontend Error Handling

- [ ] **Task 8.1:** `src/SettingsModal.tsx` — add `catch` block to save handler that sets error state and shows user-facing message. Add error state variable.
- [ ] **Task 8.2:** `src/views/ProfileView.tsx` — add `catch` block and user-facing error display for `deleteItem`, `saveEdit`, and `saveCandidate` handlers.

### Workstream 9 — Build Config

- [ ] **Task 9.1:** `src-tauri/tauri.conf.json` — set `createUpdaterArtifacts` to `true`.
- [ ] **Task 9.2:** Verify `bundle.targets` includes platform-specific values for Linux/Windows/macOS.

**Blocking relationships:**
- All workstreams are independent (no cross-blocking)
- Within Workstream 4: each file's changes are independent — can be parallelized
- Tasks 4.1–4.3 blocked by Task 5.1 (need centralized logger before replacing exceptions)
- Tasks 8.1–8.2 blocked by nothing (frontend changes independent of backend)
- Tasks 9.1–9.2 blocked by nothing (JSON config change)

---

## 6. Error Handling Map

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

## 7. Call Site Map — `except: pass` Instances

### `backend/db/client.py` (21 instances)

| Line | Context | Action |
|------|---------|--------|
| 217 | Column migration — "column already exists" | Log DEBUG, continue |
| 222 | Column migration — "column already exists" | Log DEBUG, continue |
| 1196 | `_save_profile_snapshot()` | Log WARNING with profile_id |
| 1286 | `refresh_profile_snapshot()` | Log WARNING with profile_id |
| 1307 | `add_skill()` candidate link query | Log WARNING with candidate_id+skill |
| 1312 | `add_skill()` vector store add | Log WARNING with skill_name |
| 1326 | `update_skill()` vector store add | Log WARNING with skill_name |
| 1372 | `add_experience()` candidate relation | Log WARNING with candidate_id |
| 1433 | `add_project()` candidate relation | Log WARNING with candidate_id |
| 1438 | `add_project()` vector store add | Log WARNING with project_name |
| 1457 | `update_project()` vector store add | Log WARNING with project_name |
| 1480 | `add_education()` "already exists" | Log INFO, continue |
| 1492 | `add_education()` candidate relation | Log WARNING with candidate_id |
| 1507 | `add_certification()` "already exists" | Log INFO, continue |
| 1519 | `add_certification()` candidate relation | Log WARNING with candidate_id |
| 1534 | `add_achievement()` "already exists" | Log INFO, continue |
| 1546 | `add_achievement()` candidate relation | Log WARNING with candidate_id |
| 1577 | `update_candidate()` create candidate | Log WARNING with candidate_id |
| 1594 | `_delete_vec_rows()` | Log WARNING with entity_id |
| 1609 | `_add_skill_vec()` | Log WARNING with skill_name |
| 1625 | `_add_project_vec()` | Log WARNING with project_name |

### `backend/main.py` (7 instances)

| Line | Context | Action |
|------|---------|--------|
| 192 | `broadcast()` agent event recording | Log WARNING with event type |
| 1566 | Post-ingestion snapshot refresh | Log WARNING with lead_id |
| 1670 | Skill import (bulk ingest) | Log WARNING with ingest source |
| 1723 | Skill import (GitHub ingestor) | Log WARNING with username |
| 1790 | Skill add from identity form | Log WARNING |
| 2102 | WebSocket ping timeout | OK — document with comment |
| 2104 | WebSocket disconnect | OK — document with comment |

### `backend/agents/` (12 instances)

| File | Line | Context | Action |
|------|------|---------|--------|
| `portfolio_ingestor.py` | 66 | Page screenshot | Log WARNING with URL |
| `ingestor.py` | 81 | Upsert update fallback | Log WARNING with entity type |
| `ingestor.py` | 92 | Graph relation creation | Log WARNING |
| `ingestor.py` | 106 | Vector store delete | Log WARNING |
| `selectors.py` | 34 | JSON cache parse | Log DEBUG with cache key |
| `selectors.py` | 51 | JSON cache parse | Log DEBUG with cache key |
| `actuator.py` | 113 | Unmatched labels processing | Log WARNING |
| `actuator.py` | 119 | Page screenshot | Log WARNING with URL |
| `actuator.py` | 193 | Form field fill | Log WARNING with step |
| `actuator.py` | 358 | Submit button lookup | Log WARNING |
| `scoring_engine.py` | 628 | Budget amount parsing (ValueError) | Log WARNING with raw value, default 0 |
| `quality_gate.py` | 98 | Date parsing | Log DEBUG with raw date string |

---

## 8. Validation Checklist

### Task 4 — Silent Exception Suppression

- [ ] Every `except: pass` in production code replaced with logged warning/error carrying identifiers
- [ ] `backend/db/client.py`: all 21 instances classified and replaced (no bare `pass`)
- [ ] `backend/main.py`: all 7 instances classified and replaced (or documented)
- [ ] `backend/agents/`: all 12 instances classified and replaced (no bare `pass`)
- [ ] Recoverable errors log and continue — no behavior change for happy paths
- [ ] Terminal errors log once and stop in controlled way
- [ ] Tracebacks preserved via `exc_info=True` or `logger.exception()`
- [ ] Logging entry points centralized — no new ad hoc logger configuration

### Task 5 — Logging Infrastructure

- [ ] All `print()` calls in production code replaced with logger
- [ ] Log format includes: timestamp, level, logger name, message, correlation IDs
- [ ] Optional file handler configurable via env var/config
- [ ] Tests verify log level resolution, format consistency, exception context

### Task 6 — WebSocket Async-Safety

- [ ] `asyncio.Lock` guards `_CM.add()` and `_CM.remove()`
- [ ] `broadcast()` snapshots list under lock, sends outside lock
- [ ] Tests verify concurrent add/remove/broadcast under asyncio

### Task 7 — SQLite WAL Mode

- [ ] `PRAGMA journal_mode=WAL` set on initial connection
- [ ] `PRAGMA busy_timeout=5000` set for contention resilience
- [ ] Tests verify pragmas are set

### Task 8 — Frontend Error Handling

- [ ] SettingsModal save failure shows user-facing error (not silent)
- [ ] ProfileView delete failure shows user-facing error
- [ ] ProfileView saveEdit shows user-facing error on failure
- [ ] ProfileView saveCandidate shows user-facing error on failure
- [ ] No unhandled promise rejections in save/delete handlers

### Task 9 — Build Config

- [ ] `createUpdaterArtifacts` set to `true`
- [ ] Bundle targets include platform-specific values
- [ ] App builds successfully after config changes

### Code quality gates

- [ ] Zero `except: pass` remaining in production code (verify with `git grep 'except.*:.*pass' backend/ | grep -v test`)
- [ ] All changed files have explicit type hints
- [ ] Zero new `print()` calls in production code
- [ ] Branch is clean — no unrelated changes
- [ ] Full test suite passes (204 tests)

---

## 9. Open Questions

| # | Question | Raised by | Status |
|---|----------|-----------|--------|
| Q1 | Should the `_safe_call()` helper in `db/client.py` log as WARNING or ERROR for fire-and-forget vector ops? | Agent | `[ ] Open` |
| Q2 | Should structured logging use JSON format or enriched plain-text with correlation IDs? | Agent | `[ ] Open` |
| Q3 | For SQLite: single shared connection with WAL vs simple connection pool? | Agent | `[ ] Open` |
| Q4 | What correlation ID format to use (UUID, request-scoped, job-scoped)? | Agent | `[ ] Open` |

---

## 10. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-14 | Task 4 (silent exception replacement) prioritized before logging infrastructure workstream | Need to know what we're logging before we define the format — replacement reveals log patterns | Logging format first, then replacement |
| 2026-05-14 | Workstreams 4-9 are independent — no cross-blocking | Each addresses a disjoint subsystem (db, websocket, sqlite, frontend, build) | Sequential ordering |

---

_Last updated: 2026-05-14 — Agent_
