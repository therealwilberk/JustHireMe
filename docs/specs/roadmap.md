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

---

## Project Status

| Field | Value |
|-------|-------|
| Current phase | `[PHASE_NAME]` |
| Phase started | `[DATE]` |
| Last updated | `[DATE]` |
| Overall status | `[ ] Not started / [ ] In progress / [ ] Paused / [ ] Complete` |

---

## Phase Overview

<!-- High-level summary of all phases. Detail lives in each phase block below. -->

| # | Phase | Status | Feature Spec |
|---|-------|--------|--------------|
| 1 | [Name] | `[ ] Pending / [~] Active / [x] Done` | `specs/features/[name].md` |
| 2 | | | |
| 3 | | | |

---

## Phase Details

---

### Phase 1 — [Name]

**Goal:** _[One sentence: what capability exists at the end of this phase that didn't before?]_

**Scope:**
- _[Specific deliverable 1]_
- _[Specific deliverable 2]_

**Out of scope for this phase:**
- _[What is explicitly deferred]_

**Dependencies:** _[What must be true before this phase can start — e.g. "Database schema finalized", "Auth system in place"]_

**Validation:** _[How do we know this phase is done? This will be expanded in the feature spec.]_
- [ ] _[Checklist item]_
- [ ] _[Checklist item]_

**Feature spec:** `specs/features/[phase-name].md` — `[ ] Not created / [ ] Draft / [ ] Approved`

**Status:** `[ ] Pending`

---

### Phase 2 — [Name]

**Goal:**

**Scope:**
-

**Out of scope for this phase:**
-

**Dependencies:**

**Validation:**
- [ ]

**Feature spec:** `specs/features/[phase-name].md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase 3 — [Name]

<!-- Duplicate the block above for each additional phase -->

---

## Deferred / Backlog

<!-- Ideas and features that are acknowledged but not scheduled.
     These are not commitments — they are a memory buffer. -->

| Item | Notes | Why deferred |
|------|-------|--------------|
|      |       |              |

---

## Change Log

<!-- Record scope changes and the reason for them. Keeps the roadmap honest. -->

| Date | Change | Reason |
|------|--------|--------|
|      |        |        |

---

_Last updated: [DATE] — [AUTHOR]_
