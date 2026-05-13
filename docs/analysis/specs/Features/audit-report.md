# Audit Report — [PROJECT NAME]

> Generated at the start of the project for brownfield or forked codebases.
> Updated progressively as new areas of the codebase are touched during feature work.
> Agent: read this file in full before proposing any architecture, writing any spec,
> or making any code change. Treat findings here as constraints unless explicitly overridden.
>
> **Paired skill:** `specs/skills/improve-codebase-architecture.md`
> Run that skill after the initial audit to produce the detailed architecture analysis
> that populates Sections 5, 8, 9, 10, and 12 of this report. Do not fill those sections
> manually — run the skill and use its structured output.

---

## Meta

| Field | Value |
|-------|-------|
| Project | |
| Audit type | `Fork` / `Brownfield` |
| Upstream repo (forks) | |
| Upstream last commit | |
| Audit date | [DATE] |
| Audited by | Agent + [USER] |
| Last updated | [DATE] — [reason for update] |

---

## 1. Executive Summary

<!-- 5–10 sentences. What is this codebase? What shape is it in?
     What are the most important things to know before touching it?
     Write this last — after all sections below are complete. -->

_[Summary here]_

**Overall health:** `Good` / `Fair` / `Poor` / `Critical`

---

## 2. Project Overview

### Purpose
<!-- What does this project do? Who uses it? -->

### Origin (forks only)
<!-- Why was this forked? What does the upstream project do that we're building on?
     What is the upstream's activity level, license, and community size? -->

- **License:** _[e.g. MIT, GPL — note any constraints this places on our fork]_
- **Upstream activity:** _[e.g. "Active — last commit 3 days ago" / "Dormant — last commit 14 months ago"]_
- **Community size:** _[Stars, contributors, open issues]_
- **Fork rationale:** _[Why fork instead of extend or replace?]_

### Divergence plan (forks only)
<!-- What do we keep from upstream? What do we replace? How do we handle upstream updates? -->

| Area | Upstream behaviour | Our approach |
|------|--------------------|--------------|
| _[e.g. Auth]_ | | `Keep` / `Replace` / `Extend` / `Strip` |
| _[e.g. UI layer]_ | | |
| _[e.g. DB schema]_ | | |

---

## 3. Architecture Overview

### Directory structure

```
[PROJECT_ROOT]/
├── [dir]/    — [what lives here]
├── [dir]/    — [what lives here]
└── ...
```

### Architecture pattern
<!-- Monolith, layered, MVC, event-driven, etc. What pattern does the code follow?
     Is it consistent throughout, or mixed? -->

### Entry points
<!-- Where does execution begin? List all meaningful entry points. -->

| Entry point | File | Purpose |
|-------------|------|---------|
| _[e.g. HTTP server]_ | | |
| _[e.g. CLI]_ | | |
| _[e.g. Worker / cron]_ | | |

### Data flow
<!-- How does data move through the system? Describe the main request/response or
     processing pipeline at a high level. A short prose description is fine. -->

---

## 4. Tech Stack (as found)

<!-- Document what is actually in the codebase, not what the README claims. -->

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | | | |
| Runtime | | | |
| Framework | | | |
| Database | | | |
| ORM / query layer | | | |
| Auth | | | |
| Logging | | | |
| Testing | | | |
| Build / bundler | | | |
| Other significant deps | | | |

### Dependency health
<!-- Flag any outdated, unmaintained, or conflicting dependencies. -->

| Package | Issue | Severity | Recommendation |
|---------|-------|----------|----------------|
| | _[e.g. Last release 3 years ago, 47 open CVEs]_ | `High` / `Medium` / `Low` | |

---

## 5. Code Quality Assessment

> **This section is populated by `specs/skills/improve-codebase-architecture.md`.**
> Run that skill and paste its output here. The subsections below are the required structure.

### Module Classification Summary

<!-- Output from improve-codebase-architecture.md Step 3 & 9 -->

| Module | Classification | Size (LOC) | Key issue |
|--------|----------------|------------|-----------|
| | `Deep` / `Shallow` / `God` / `Tangled` / `Dead` / `Stable` | | |

**Overall architecture health:** `Good` / `Fair` / `Poor` / `Critical`
**Biggest risk:** _[single sentence]_

### Deepening Candidates

<!-- Output from improve-codebase-architecture.md Step 4
     Paste candidate blocks here. Each block covers: modules involved, why they belong together,
     current problems, proposed interface, effort, risk, recommended phase. -->

_[No candidates identified / See blocks below]_

### God Objects

<!-- Output from improve-codebase-architecture.md Step 5
     Paste god object blocks here. Each block covers: size, imports, proposed split,
     split sequence, effort, risk, recommended phase. -->

_[None identified / See blocks below]_

### Consistency

<!-- Remaining manual observations not covered by the skill -->

| Area | Observation | Impact |
|------|-------------|--------|
| Naming conventions | | |
| File/module structure | | |
| Error handling style | | |
| Logging approach | | |
| Test coverage | | |

### Hardcodes & Config

<!-- Document any hardcoded values found — secrets, URLs, ports, credentials. -->

| Location (file:line) | Hardcoded value | Risk | Action required |
|----------------------|-----------------|------|-----------------|
| | | `High` / `Medium` / `Low` | |

> Any hardcode that is a secret (key, password, token) is **Critical** — flag immediately.

### Error Handling & Logging Coverage

<!-- Output from improve-codebase-architecture.md Step 8 -->

| Module | Error handling | Logging | Issues found | Priority |
|--------|----------------|---------|--------------|----------|
| | `Good` / `Partial` / `None` | `Good` / `Partial` / `None` | | `High` / `Medium` / `Low` |

---

## 6. Security Observations

<!-- Note anything that raises a security concern.
     Not a full security audit — flag what's visible from the code. -->

| Observation | Location | Severity | Notes |
|-------------|----------|----------|-------|
| | | `Critical` / `High` / `Medium` / `Low` | |

---

## 7. Test Coverage

| Area | Coverage status | Notes |
|------|----------------|-------|
| Unit tests | `None` / `Partial` / `Good` | |
| Integration tests | | |
| E2E tests | | |
| Test framework | | |

**Overall:** _[e.g. "Tests exist only for the utility layer. No integration or E2E coverage. Framework is Jest but config is incomplete."]_

### Test Blind Spots

<!-- Output from improve-codebase-architecture.md Step 6
     For each blind spot: area, coverage status, why it matters, what prevents testing,
     what architectural change is needed first, recommended test type, recommended phase. -->

_[None identified / See blocks below]_

---

## 8. Vocabulary & Naming Consistency

<!-- Output from improve-codebase-architecture.md Step 7
     Documents terminology drift — same concept named differently across files,
     or same word meaning different things in different contexts.
     If specs/context.md exists, cross-reference every term against codebase usage. -->

| Term / inconsistency | Files affected | Impact | Proposed canonical term | Scope |
|----------------------|----------------|--------|------------------------|-------|
| | | | | `Isolated` / `Wide` / `Pervasive` |

**Context.md alignment:** `Consistent` / `Partial drift` / `Significant drift` / `No context.md exists`

---

## 8. Known Issues & Technical Debt

<!-- Document problems that exist in the codebase now, before we touch it.
     This protects us from inheriting blame and gives us a prioritized fix list. -->

| # | Issue | Location | Severity | Owned by this project? |
|---|-------|----------|----------|------------------------|
| D1 | | | `High` / `Medium` / `Low` | `Yes` / `No — upstream` |
| D2 | | | | |

---

## 9. Constraints Imposed on Spec Work

<!-- What did the audit reveal that must be reflected in the constitution and feature specs?
     These are not optional — they are facts about the codebase that constrain our decisions. -->

- _[e.g. "Framework version is too old to support X — upgrade is a prerequisite for Phase 2"]_
- _[e.g. "Database schema has no migration system — one must be established before any schema changes"]_
- _[e.g. "Hardcoded API keys found in config.js — must be moved to env vars before any deployment"]_

---

## 10. Recommended Pre-Work

<!-- Populated from improve-codebase-architecture.md Section 9 — Recommended Action Priority.
     Items ranked Priority 1–3 from that skill's output belong here.
     Items ranked 4+ go to the roadmap backlog.
     Each item must have effort and risk estimates — unestimated items don't get scheduled. -->

| Priority | Task | Type | Reason | Effort | Risk | Phase |
|----------|------|------|--------|--------|------|-------|
| 1 | | `Deepening` / `Split` / `Test` / `Rename` / `Error handling` / `Config` | | `Small` / `Medium` / `Large` | `Low` / `Medium` / `High` | `Pre-work` / `Phase N` |
| 2 | | | | | | |
| 3 | | | | | | |

---

## 11. Architecture Analysis Runs

<!-- Each time specs/skills/improve-codebase-architecture.md is run, log it here.
     Append — do not overwrite earlier runs. Architecture snapshots over time are valuable. -->

| Date | Trigger | Modules scanned | Health rating | Key finding | Full output location |
|------|---------|-----------------|---------------|-------------|----------------------|
| | `Initial audit` / `Pre-phase N` / `Post-sprint` | | `Good` / `Fair` / `Poor` / `Critical` | | `Sections 5, 7, 8, 10 updated` |

---

## 12. Progressive Update Log

<!-- As feature work progresses and new areas of the codebase are touched,
     update this log. Do not edit earlier sections retroactively —
     append here with date and context. -->

| Date | Phase / Feature | Area touched | New findings |
|------|----------------|--------------|--------------|
| | | | |

---

_Last updated: [DATE] — [AUTHOR]_
