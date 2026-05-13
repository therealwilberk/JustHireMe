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
| Current phase | `[PHASE_NAME]` |
| Phase started | `[DATE]` |
| Last updated | `[DATE]` |
| Overall status | `[ ] Not started / [ ] In progress / [ ] Paused / [ ] Complete` |

---

## Phase Overview

<!-- High-level summary of all phases. Detail lives in each phase block below.
     Type: Feature (vertical slice) | Infra (horizontal ok) | Chore
     Mode: AFK (agent works solo) | HITL (user present during execution) -->

| # | Phase | Type | Mode | Status | Blocks | Feature Spec |
|---|-------|------|------|--------|--------|--------------|
| 1 | [Name] | `Feature` / `Infra` / `Chore` | `AFK` / `HITL` | `[ ] Pending / [~] Active / [x] Done` | `none` / `#2, #3` | `specs/features/[name].md` |
| 2 | | | | | | |
| 3 | | | | | | |

---

## Phase Details

---

### Phase 1 — [Name]

**Type:** `Feature` / `Infra` / `Chore`
**Mode:** `AFK` / `HITL`
**Blocks:** `none` / `Phase 2, Phase 3`
**Blocked by:** `none` / `Phase X`

**Goal:** _[One sentence: what capability exists at the end of this phase that didn't before?]_

**Vertical slice check** _(Feature phases only):_
- [ ] Touches data layer
- [ ] Touches logic / service layer
- [ ] Touches interface layer (API endpoint, CLI output, or UI)
- [ ] Produces something observable/testable at end of phase

**Scope:**
- _[Specific deliverable 1]_
- _[Specific deliverable 2]_

**Out of scope for this phase:**
- _[What is explicitly deferred]_

**Dependencies:** _[What must be true before this phase can start — e.g. "Database schema finalized", "Auth system in place"]_

**Validation:**
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
