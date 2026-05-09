# Audit Report — [PROJECT NAME]

> Generated at the start of the project for brownfield or forked codebases.
> Updated progressively as new areas of the codebase are touched during feature work.
> Agent: read this file in full before proposing any architecture, writing any spec,
> or making any code change. Treat findings here as constraints unless explicitly overridden.

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

### Consistency
<!-- Is the codebase written in a consistent style? Mixed patterns? Multiple authors visible? -->

| Area | Observation | Impact |
|------|-------------|--------|
| Naming conventions | | |
| File/module structure | | |
| Error handling style | | |
| Logging approach | | |
| Test coverage | | |

### Hardcodes & config
<!-- Document any hardcoded values found — secrets, URLs, ports, credentials. -->

| Location (file:line) | Hardcoded value | Risk | Action required |
|----------------------|-----------------|------|-----------------|
| | | `High` / `Medium` / `Low` | |

> Any hardcode that is a secret (key, password, token) is **Critical** — flag immediately.

### Error handling gaps
<!-- Where does the code fail silently, swallow exceptions, or lack handling? -->

| Location | Issue | Risk |
|----------|-------|------|
| | _[e.g. "No try/catch around DB calls in user.service.ts"]_ | |

### Logging gaps
<!-- Where is logging absent or using raw console/print? -->

| Location | Issue |
|----------|-------|
| | |

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

<!-- Before feature development begins, what needs to be cleaned up or resolved?
     List in priority order. Each item should become a task or a chore branch. -->

| Priority | Task | Reason | Estimated effort |
|----------|------|--------|-----------------|
| 1 | | | `Small` / `Medium` / `Large` |
| 2 | | | |

---

## 11. Progressive Update Log

<!-- As feature work progresses and new areas of the codebase are touched,
     update this log. Do not edit earlier sections retroactively —
     append here with date and context. -->

| Date | Phase / Feature | Area touched | New findings |
|------|----------------|--------------|--------------|
| | | | |

---

_Last updated: [DATE] — [AUTHOR]_
