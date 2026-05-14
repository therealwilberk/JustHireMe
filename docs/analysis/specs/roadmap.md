# Roadmap

> **Living document.** Update phase status as work progresses.
> Agent: use this file to understand sequencing and scope. Never work ahead of the current active phase
> without explicit instruction. Each phase becomes a feature spec before implementation begins.

---

## Roadmap Philosophy

- Phases are **sequential by default** — complete and validate one before starting the next
- Each phase maps to one or more feature specs in `specs/features/`
- A phase is **done** when its validation checklist passes, not when code is written
- Scope changes must be reflected here before the agent acts on them
- **Feature phases use vertical slices** — each phase must cross all relevant layers (data → logic → interface) and produce something observable and testable at the end. Horizontal phases ("do all the DB work") are a smell — split or restructure them.
- **Infrastructure phases are exempt** from the vertical slice rule — migrations, config, dependency upgrades, and chores are horizontal by nature and that's fine. Label them clearly.

---

## Project Status

| Field | Value |
|-------|-------|
| Current phase | `Phase C — Reliability, Observability & Concurrency` |
| Phase started | `2026-05-14` |
| Last updated | `2026-05-14` |
| Overall status | `[~] Active` |

---

## Agent Instructions

See [`AGENTS.md`](../../../AGENTS.md) for config architecture usage, branch rules, and test commands.

---

## Phase Overview

| # | Phase | Type | Mode | Status | Blocks | Feature Spec |
|---|-------|------|------|--------|--------|--------------|
| A | Config Architecture & Validation Foundation | `Infra` | `TBD` | `[~] Active` | `B, C` | `features/phase-a-config-architecture.md` |
| B | Security Remediation & Migration Paths | `Infra` | `TBD` | `[x] Complete` | `D+` | `features/phase-b-security-migration.md` |
| C | Reliability, Observability & Concurrency | `Infra` | `TBD` | `[~] Active` | `D+` | `features/phase-c-reliability-observability.md` |
| D | Locale & Scraping Model | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |
| E | PDF Quality | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |
| F | UI Clarity | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |
| G | End-User Customization | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |

---

## Phase Details

---

### Phase A — Config Architecture & Validation Foundation

**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `AFK` (all tasks deterministic per autonomy boundary analysis)
**Blocks:** `Phase B, Phase C`
**Blocked by:** `none`

**Goal:** A typed, validated config layer with clear authority boundaries that replaces all 150+ hardcoded values — providing the foundation every subsequent phase builds on.

**Vertical slice check** _(Feature phases only):_
- N/A (Infra phase)

**Scope:**
- Config infrastructure: extract 150+ hardcoded values into typed Pydantic schemas organized by domain boundary (`backend/config/scoring.py`, `backend/config/llm.py`, `backend/config/scraping.py`, etc.)
- Config resolution hierarchy: CLI flag → env var → XDG path → local fallback
- Centralized settings accessor — no scattered `os.getenv()` calls
- Config validation at startup — malformed config fails fast with clear error
- CI: run full test suite on every push (needed to validate config extraction doesn't break anything)

**Out of scope for this phase:**
- Security remediation (API keys, URL tokens, stdout leaks — Phase B)
- Error handling overhaul (except:pass → logged warnings — Phase C)
- Concurrency fixes (WebSocket race — Phase C)
- Frontend error handling fixes (SettingsModal, ProfileView — Phase C)
- Build config fixes (updater, bundle targets — Phase C)
- OS keychain integration (deferred — not on current roadmap)
- SQLite WAL mode (Phase C)
- Monolith splitting (deferred)
- All feature work (locale, PDF, UI, customization — Phase D+)

**Dependencies:** None

**Validation:**
- [x] All 150+ hardcoded values extracted into typed config objects
- [x] Config resolution hierarchy works: CLI override → env var → XDG → fallback
- [x] Config validates at startup — malformed file or missing value fails fast with clear message
- [x] No scattered `os.getenv()` calls added; all env access through config layer
- [x] Full backend test suite passes (validates config extraction didn't break anything) — 128 tests
- [x] Config modules organized by domain, not monolithic
- [x] Authority boundaries documented: dev constants in Python, operator config in env, user config in data dir, ephemeral in DB

**Feature spec:** `features/phase-a-config-architecture.md` — `[x] Done`

**Status:** `[x] Complete`

---

### Phase B — Security Remediation & Migration Paths

**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `TBD`
**Blocks:** `Phase D+`
**Blocked by:** `Phase A`

**Goal:** API keys resolved from env vars only, no secrets in URLs, with a graceful deprecation path for existing SQLite-stored credentials. (C2 — token to stderr — deferred; see scope note.)

**Scope:**
- C1: Env-var-only auth — API keys no longer stored in SQLite settings table
- C2: Auth token to stderr, not stdout (deferred — blocked by Tauri sidecar protocol at `src-tauri/src/lib.rs:301`; token stays on stdout)
- C3/C4: Apify/Hunter API keys moved from URL query params to headers
- Migration path: startup checks for legacy SQLite keys, logs WARN-level deprecation with migration instructions, reads old values as fallback (read-only — never writes back)
- Removal milestone defined in roadmap

**Out of scope for this phase:**
- OS keychain integration (deferred)
- Non-security hardcoded values (Phase A)
- Error handling or concurrency fixes (Phase C)

**Dependencies:** Phase A (needs config layer for env resolution)

**Validation:**
- [x] Zero API keys stored in SQLite settings table
- [x] All keys resolved from env vars through config layer
- [x] Legacy SQLite keys trigger WARN-level deprecation with migration instructions
- [x] Fallback reads old keys but never writes them back to SQLite
- [x] Apify/Hunter tokens not present in URL query params
- [ ] Auth token not present in stdout (deferred — see scope note)

**Feature spec:** `features/phase-b-security-migration.md` — `[x] Created`

**Status:** `[x] Complete`

---

### Phase C — Reliability, Observability & Concurrency

**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `TBD`
**Blocks:** `Phase D+`
**Blocked by:** `Phase A`

**Goal:** Silent failures become visible, concurrent operations are safe, and the application emits structured logs with correlation context.

**Scope:**
- [x] Replace 50+ `except: pass` with logged warnings across all production code
- [x] Structured logging: format, levels, correlation IDs via contextvars, contextual fields, optional file handler
- [x] Frontend error handling fixes + tests (SettingsModal, ProfileView silent save failures)
- [x] WebSocket broadcast async-safety (`_CM` class — coroutine-safe mutation)
- [x] SQLite WAL mode
- [x] Build config fixes (`createUpdaterArtifacts`, platform-specific bundle targets)

**Out of scope for this phase:**
- Monolith splitting (deferred)
- New feature work (Phase D+)

**Dependencies:** Phase A (config layer needed for constants extracted from error paths)

**Validation:**

**Task 4 — Replace Silent Exception Suppression:**
- [x] Every `except: pass` in production code replaced with logged warning, structured error, or explicit handling
- [x] Each replacement carries identifiers (request ID, job ID, lead ID, node name, subsystem) where available
- [x] Recoverable errors emit structured log (warning/error with context) and continue via fallback
- [x] Terminal errors log once and stop in a controlled way
- [x] Tracebacks preserved in exception logs (not reduced to strings)
- [x] Logging configured centrally — no ad hoc configuration in random modules
- [x] Logs carry consistent fields across all error paths

**Task 5+ (remaining Phase C scope):**
- [x] Structured logging with correlation context on all error paths (infra done: centralized `get_logger()`, consistent format; correlation IDs via contextvars, middleware, optional file handler)
- [x] SettingsModal save failure shows user-facing error
- [x] ProfileView save failure shows user-facing error
- [x] WebSocket `_CM` class is async-safe — no concurrent mutation
- [x] SQLite uses WAL journaling mode
- [x] Updater artifacts generate on build
- [x] Bundle targets are platform-specific

**Phase C overall:**
- [x] Zero `except: pass` remaining in production code (verified: `git grep 'except.*:.*pass' backend/ | grep -v test` → no output)
- [x] All validation items above pass

**Feature spec:** `features/phase-c-reliability-observability.md` — `[x] Created`

**Status:** `[x] Complete`

---

### Phase D — Locale & Scraping Model

**Goal:** User can add their own locale's job sources and understand the scraping architecture.

**Scope:**
- Document scraping model: how sources are defined, queried, and processed
- Config-driven source definitions (sources.yaml)
- Example: add one new locale's job boards

**Out of scope for this phase:**
- Full multi-locale support — just the plumbing for one new locale
- UI overhauls

**Feature spec:** `features/phase-d-locale-scraping.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase E — PDF Quality

**Goal:** Resume and cover letter PDF output matches user expectations for layout, fonts, and formatting.

**Scope:**
- Debug PDF generation pipeline in `generator.py`
- Fix font rendering, scaling, margins
- Add user-configurable templates

**Out of scope for this phase:**
- Multi-language PDF support
- Real-time PDF preview

**Feature spec:** `features/phase-e-pdf-quality.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase F — UI Clarity

**Goal:** Tab labels, navigation, and user-facing terminology are unambiguous.

**Scope:**
- Audit all tab/button labels across 8 views
- Rename unclear labels, add tooltips where helpful
- Fix inconsistent terminology

**Feature spec:** `features/phase-f-ui-clarity.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase G — End-User Customization

**Goal:** Non-developer users can customize behavior without editing code.

**Scope:**
- User-facing config files in data dir
- Config UI in SettingsModal for common options
- Ghost mode interval, score thresholds, source toggles exposed without env vars

**Feature spec:** `features/phase-g-customization.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase H — End-User Customization

**Goal:** Non-developer users can customize behavior without editing code.

**Scope:**
- User-facing config files in data dir
- Config UI in SettingsModal for common options
- Ghost mode interval, score thresholds, source toggles exposed without env vars

**Feature spec:** `specs/features/phase-h-customization.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

## Deferred / Backlog

| Item | Notes | Why deferred |
|------|-------|--------------|
| OS keychain integration | Encrypt API keys at rest | Needs system-level integration (libsecret), not blocking Phase A config extraction |
| Monolith splitting (main.py, db/client.py) | Route-level extraction | Too risky without test coverage — revisit after Phase A |
| Frontend component tests | Full React UI test suite | Upstream problem — fork focuses on backend correctness |
| Upstream merge tracking | Watch vasu-devs/JustHireMe for changes | Cadence TBD |
| Replace `main.py:37` hardcoded `_LOCAL_ORIGIN_RE` with `settings.app.cors.local_origin_regex` | Phase B (Security) — CORS tightening | Credential/scope hygiene |
| Verify `.env.example` contains all env vars declared in config schemas | Phase B (Security) — onboarding | Missing vars cause silent auth failures |
| Consolidate `db/client.py:get_setting()` SQLite table vs Pydantic config boundary | Phase C (Reliability) — data model | Dual config paths cause inconsistent state |
| Manual test: app startup with no config files, empty config dir, config removal fallback | Phase C (Reliability) — startup | Edge cases for headless deployment |

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-14 | Phase B completed, Phase C activated, feature spec created | Silent exception suppression → structured error reporting, logging standardization |
| 2026-05-14 | Updated test count to 204 | Tests expanded with Phase B coverage |
| 2026-05-14 | Phase C tasks 4-8, 11 done; Task 9 core infra done | 280 backend + 33 frontend tests passing |
| 2026-05-14 | Phase C complete — Task 9 (Structured Logging) done | 298 backend + 33 frontend tests passing |
| 2026-05-13 | Phase B activated, feature spec created | Security migration: unified secret resolver, URL→headers, token→stderr, deprecation warnings |
| 2026-05-13 | Completed Phase A implementation | Config architecture: schemas, resolver, validation gate, CI, docs. 128 tests pass. |
| 2026-05-13 | Initial population after grill session | Phase structure from codebase audit + user decisions |
| 2026-05-13 | Phase 4 (Hyprland-specific) removed from roadmap | Too narrow, cancelled per audit review |

---

_Last updated: [DATE] — [AUTHOR]_
