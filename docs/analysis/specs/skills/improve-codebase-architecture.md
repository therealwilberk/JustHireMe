# Skill — Improve Codebase Architecture

> **When to invoke:**
> 1. During Mode A audit on a brownfield or forked project — run this after the initial audit report is drafted to deepen the architectural analysis.
> 2. At the start of any phase that touches a high-debt area flagged in `specs/audit-report.md`.
> 3. Periodically after fast-moving development sprints when architectural drift is likely.
>
> Output from this skill feeds directly into `specs/audit-report.md` Sections 5, 8, 9, and 10.
> Do not propose implementation changes during this skill — analysis and recommendations only.
> All changes it recommends become roadmap items or pre-work tasks, not immediate edits.

---

## Purpose

Find architectural problems before they compound. Specifically:

- **Shallow modules** — too many small files with tangled dependencies, hard to test, hard for the agent to navigate
- **God objects / monoliths** — single files doing too many things, impossible to change safely
- **Coupling without cohesion** — modules that change together but aren't logically grouped
- **Test blind spots** — areas with no feedback loop, where agent changes are flying blind
- **Naming and vocabulary drift** — inconsistent terminology across the codebase that forces the agent to guess what things mean
- **Hidden hardcodes and config debt** — values that should be configurable but aren't
- **Error handling deserts** — large areas where failures are silent or unstructured

The goal is a codebase that is **navigable, testable, and safe to delegate to an agent**. Bad architecture is not just a human problem — it directly limits the quality of agent output. If the codebase is hard for you to reason about, it is worse for the agent.

---

## Instructions

### Step 1 — Orient

Read the following before doing anything else:

1. `specs/audit-report.md` or `../../../codebase-audit.md` — understand what's already been flagged. Do not re-report findings already documented. Extend them.
2. `specs/tech-stack.md` — know the intended architecture and patterns before evaluating whether the code follows them
3. `specs/mission.md` — understand what this codebase is supposed to do. This frames which modules are core and which are peripheral.
4. `specs/context.md` if present — use established vocabulary throughout. Do not introduce synonyms for defined terms.

### Step 2 — Map the module graph

Walk the entire codebase. For every file or module, record:

- What it exports / exposes (its interface)
- What it imports / depends on (its dependencies)
- Approximate size (lines of code)
- Single-word characterization of its responsibility

Build a mental (or explicit) dependency graph. You are looking for:

- **Fan-out** — modules that import from many others (high coupling, fragile)
- **Fan-in** — modules imported by many others (high impact if changed, must be stable)
- **Cycles** — A imports B imports A (always a design smell)
- **Size outliers** — files significantly larger than the median (god object candidates)
- **Orphans** — files imported by nothing (dead code candidates)

### Step 3 — Classify every module

For each module, assign one classification:

| Classification | Definition |
|----------------|------------|
| `Deep` | Small, stable interface. Rich internal logic. Easy to test from the outside. This is the target. |
| `Shallow` | Large interface relative to internal logic. Often a pass-through or thin wrapper. Creates noise. |
| `God` | Does too many things. Too large. Too many dependents. Change is risky without full context. |
| `Tangled` | Correct responsibility but tightly coupled to unrelated modules. Hard to test in isolation. |
| `Dead` | Not imported by anything. Candidate for deletion. Confirm before acting. |
| `Stable` | Rarely changes. Many dependents. Must be treated as a public API — changes here ripple everywhere. |

### Step 4 — Identify deepening candidates

A deepening candidate is a cluster of `Shallow` or `Tangled` modules that:

1. Are conceptually related (they belong to the same domain concern)
2. Could be consolidated behind a single, clean interface
3. Would become independently testable as a unit after consolidation

For each candidate cluster, document:

```
### Candidate: [Name]

**Modules involved:**
- `[file path]` — [current classification] — [current responsibility]
- `[file path]` — [current classification] — [current responsibility]

**Why they belong together:**
[1–2 sentences on shared domain concern]

**Current problems:**
- [e.g. "auth.js and session.js both manage token state — split responsibility causes sync bugs"]
- [e.g. "No test boundary exists — testing user login requires mocking 4 separate modules"]

**Proposed deep module:**
- Interface: [what the consolidated module exposes — keep this small]
- Internals: [what moves inside and becomes hidden]
- Test boundary: [what a test for this module looks like from the outside]

**Effort estimate:** `Small` (< 1 day) / `Medium` (1–3 days) / `Large` (3+ days)
**Risk:** `Low` (isolated) / `Medium` (some dependents) / `High` (many dependents, or touches auth/data/payments)
**Recommended phase:** [which roadmap phase this should happen in, or "Pre-work"]
```

### Step 5 — Identify god objects

For every file exceeding ~300 lines (or the project median × 3, whichever is lower), apply this analysis:

```
### God Object: [filename]

**Size:** [lines of code]
**Imports:** [count and list key ones]
**Imported by:** [count and list key ones]

**Responsibilities identified:**
1. [Distinct responsibility]
2. [Distinct responsibility]
3. [Distinct responsibility — if more than 3, this is severe]

**Proposed split:**
- `[new module name]` — [responsibility] — [estimated size]
- `[new module name]` — [responsibility] — [estimated size]

**Split sequence** (order matters — do not split in parallel):
1. [First extract X because it has no dependencies on the rest]
2. [Then extract Y]
3. [Remaining core stabilizes]

**Effort estimate:** `Medium` / `Large`
**Risk:** `Medium` / `High`
**Recommended phase:** [roadmap phase or "Pre-work"]
```

### Step 6 — Identify test blind spots

For every area of the codebase with no tests or inadequate tests, document:

```
### Test Blind Spot: [area/module name]

**Coverage status:** `None` / `Partial — unit only` / `Partial — no integration`
**Why it matters:** [what breaks silently if this area has bugs]
**Why it's hard to test now:** [e.g. "No dependency injection — DB calls baked in", "God object — no clean boundary", "Side effects on import"]
**What needs to change before it's testable:** [the architectural prerequisite]
**Recommended test type:** `Unit` / `Integration` / `E2E` / `Contract`
**Recommended phase:** [roadmap phase or "Pre-work"]
```

### Step 7 — Audit naming and vocabulary

Walk the codebase looking for terminology inconsistency. Specifically:

- Same concept named differently in different files (e.g. `user` vs `account` vs `member`)
- Same word meaning different things in different contexts
- Domain terms that don't match what the spec files call things
- Abbreviations that are not self-evident and not documented

Document findings:

```
### Vocabulary Issue: [term or inconsistency]

**Where it appears:**
- `[file]`: uses "[term A]"
- `[file]`: uses "[term B]" — same concept

**Impact:** [how this confuses the agent or causes bugs]
**Proposed canonical term:** [what it should be called everywhere]
**Scope of rename:** `Isolated` / `Wide` / `Pervasive`
```

If `specs/context.md` exists, check every term in it against the codebase. Flag any term that is defined in `context.md` but used inconsistently in code.

### Step 8 — Audit error handling and logging coverage

Walk every module and check:

**Error handling:**
- Are all external calls (DB, API, file I/O, network) wrapped in try/catch or equivalent?
- Are errors propagated with context, or re-thrown bare?
- Are there any `except: pass`, `.catch(() => {})`, or equivalent silent swallows?
- Do async functions have rejection handlers?

**Logging:**
- Is there a consistent logging library in use, or is it mixed with `console.log` / `print()`?
- Are error paths logged at ERROR level?
- Are significant state changes logged at INFO level?
- Is sensitive data (passwords, tokens, PII) ever logged?

Document per-module findings in a table:

| Module | Error handling | Logging | Issues found | Priority |
|--------|----------------|---------|--------------|----------|
| `[file]` | `Good` / `Partial` / `None` | `Good` / `Partial` / `None` | [description] | `High` / `Medium` / `Low` |

### Step 9 — Produce the architecture report

Output a structured report in this format. This report is appended to or used to update `specs/audit-report.md`.

```
## Architecture Analysis — [DATE]

### Summary

**Modules scanned:** [count]
**Overall architecture health:** `Good` / `Fair` / `Poor` / `Critical`
**Biggest risk:** [single sentence — the one thing most likely to cause pain]

### Module Classifications

| Module | Classification | Size (LOC) | Key issue |
|--------|----------------|------------|-----------|
| `[file]` | `Deep` / `Shallow` / `God` / `Tangled` / `Dead` / `Stable` | | |

### Deepening Candidates

[Candidate blocks from Step 4]

### God Objects

[God object blocks from Step 5]

### Test Blind Spots

[Blind spot blocks from Step 6]

### Vocabulary Issues

[Vocabulary blocks from Step 7]

### Error Handling & Logging Coverage

[Table from Step 8]

### Recommended Action Priority

| Priority | Action | Type | Effort | Risk | Phase |
|----------|--------|------|--------|------|-------|
| 1 | | `Deepening` / `Split` / `Test` / `Rename` / `Error handling` | | | |
| 2 | | | | | |
| 3 | | | | | |

> Items ranked Priority 1–3 should become pre-work tasks in `specs/audit-report.md` Section 10
> before any feature development begins. Items ranked 4+ become roadmap backlog entries.
```

---

## Rules

- **Analysis only during this skill.** No code changes, no file edits (except `specs/`), no refactoring. Recommendations only.
- **Do not re-document what's already in `specs/audit-report.md`.** Reference existing findings, extend them.
- **Do not propose changes that contradict `specs/tech-stack.md`** without flagging the conflict explicitly.
- **Effort and risk estimates are required for every recommendation.** Unestimated items don't get scheduled.
- **If a god object or deeply tangled module is found in a critical path** (auth, payments, data integrity), flag it as `🔴 Critical` regardless of estimated effort.
- **Dead code must be confirmed before deletion is recommended.** Dynamic imports, reflection, and string-based lookups can make code appear unused when it isn't.

---

## When to Stop

Stop when you have:
- Classified every module
- Identified all deepening candidates above threshold (> 2 modules, Medium+ effort)
- Documented all god objects (> 300 LOC or 3× median)
- Mapped all test blind spots in core logic paths
- Flagged all vocabulary inconsistencies that would confuse the agent
- Completed the error handling and logging table

If the codebase is very large (100+ files), prioritize: entry points → core domain logic → data layer → utilities. Document scope limitations clearly in the report header.

---

_Part of the SDD template system — pairs with `specs/audit-report.md`_
_Run during Mode A (brownfield/fork) or at the start of high-debt phases_
