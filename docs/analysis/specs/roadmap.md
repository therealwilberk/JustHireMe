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
| Current phase | `Phase A — Config Architecture & Validation Foundation` |
| Phase started | `2026-05-13` |
| Last updated | `2026-05-13` |
| Overall status | `[~] In progress` |

---

## Phase Overview

| # | Phase | Type | Mode | Status | Blocks | Feature Spec |
|---|-------|------|------|--------|--------|--------------|
| A | Config Architecture & Validation Foundation | `Infra` | `TBD` | `[~] Active` | `B, C` | `features/phase-a-config-architecture.md` |
| B | Security Remediation & Migration Paths | `Infra` | `TBD` | `[ ] Pending` | `D+` | `[ ] Not created` |
| C | Reliability, Observability & Concurrency | `Infra` | `TBD` | `[ ] Pending` | `D+` | `[ ] Not created` |
| D | Locale & Scraping Model | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |
| E | PDF Quality | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |
| F | UI Clarity | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |
| G | End-User Customization | `Feature` | `TBD` | `[ ] Pending` | `none` | `[ ] Not created` |

---

## Phase Details

---

### Phase A — Config Architecture & Validation Foundation

**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `TBD`
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
- [ ] All 150+ hardcoded values extracted into typed config objects
- [ ] Config resolution hierarchy works: CLI override → env var → XDG → fallback
- [ ] Config validates at startup — malformed file or missing value fails fast with clear message
- [ ] No scattered `os.getenv()` calls added; all env access through config layer
- [ ] Full backend test suite passes (validates config extraction didn't break anything)
- [ ] Config modules organized by domain, not monolithic
- [ ] Authority boundaries documented: dev constants in Python, operator config in env, user config in data dir, ephemeral in DB

**Feature spec:** `features/phase-a-config-architecture.md` — `[~] Draft`

**Status:** `[~] Active`

---

### Phase B — Security Remediation & Migration Paths

**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `TBD`
**Blocks:** `Phase D+`
**Blocked by:** `Phase A`

**Goal:** API keys resolved from env vars only, no secrets in URLs or stdout, with a graceful deprecation path for existing SQLite-stored credentials.

**Scope:**
- C1: Env-var-only auth — API keys no longer stored in SQLite settings table
- C2: Auth token to stderr, not stdout
- C3/C4: Apify/Hunter API keys moved from URL query params to headers
- Migration path: startup checks for legacy SQLite keys, logs WARN-level deprecation with migration instructions, reads old values as fallback (read-only — never writes back)
- Removal milestone defined in roadmap

**Out of scope for this phase:**
- OS keychain integration (deferred)
- Non-security hardcoded values (Phase A)
- Error handling or concurrency fixes (Phase C)

**Dependencies:** Phase A (needs config layer for env resolution)

**Validation:**
- [ ] Zero API keys stored in SQLite settings table
- [ ] All keys resolved from env vars through config layer
- [ ] Legacy SQLite keys trigger WARN-level deprecation with migration instructions
- [ ] Fallback reads old keys but never writes them back to SQLite
- [ ] Apify/Hunter tokens not present in URL query params
- [ ] Auth token not present in stdout

**Feature spec:** `features/phase-b-security-migration.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase C — Reliability, Observability & Concurrency

**Type:** `Infra` (horizontal — exempt from vertical-slice rule)
**Mode:** `TBD`
**Blocks:** `Phase D+`
**Blocked by:** `Phase A`

**Goal:** Silent failures become visible, concurrent operations are safe, and the application emits structured logs with correlation context.

**Scope:**
- Replace 50+ `except: pass` with logged warnings across all production code
- Structured logging: format, levels, required context fields, destination (stderr + optional file)
- Frontend error handling fixes (SettingsModal, ProfileView silent save failures)
- WebSocket broadcast async-safety (`_CM` class — coroutine-safe mutation)
- SQLite WAL mode
- Build config fixes (`createUpdaterArtifacts`, platform-specific bundle targets)

**Out of scope for this phase:**
- Monolith splitting (deferred)
- New feature work (Phase D+)

**Dependencies:** Phase A (config layer needed for constants extracted from error paths)

**Validation:**
- [ ] Zero `except: pass` remaining in production code
- [ ] Structured logging with correlation context on all error paths
- [ ] SettingsModal save failure shows user-facing error
- [ ] ProfileView save failure shows user-facing error
- [ ] WebSocket `_CM` class is async-safe — no concurrent mutation
- [ ] SQLite uses WAL journaling mode
- [ ] Updater artifacts generate on build
- [ ] Bundle targets are platform-specific

**Feature spec:** `features/phase-c-reliability-observability.md` — `[ ] Not created`

**Status:** `[ ] Pending`

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

### Phase E — End-User Customization

**Goal:** Non-developer users can customize behavior without editing code.

**Scope:**
- User-facing config files in data dir
- Config UI in SettingsModal for common options
- Ghost mode interval, score thresholds, source toggles exposed without env vars

**Feature spec:** `specs/features/phase-e-customization.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

## Deferred / Backlog

| Item | Notes | Why deferred |
|------|-------|--------------|
| OS keychain integration | Encrypt API keys at rest | Needs system-level integration (libsecret), not blocking Phase A config extraction |
| Monolith splitting (main.py, db/client.py) | Route-level extraction | Too risky without test coverage — revisit after Phase A |
| Frontend component tests | Full React UI test suite | Upstream problem — fork focuses on backend correctness |
| Upstream merge tracking | Watch vasu-devs/JustHireMe for changes | Cadence TBD |

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-13 | Initial population after grill session | Phase structure from codebase audit + user decisions |
| 2026-05-13 | Phase 4 (Hyprland-specific) removed from roadmap | Too narrow, cancelled per audit review |

---

_Last updated: [DATE] — [AUTHOR]_
