# Feature Spec — [FEATURE NAME]

> This file is written BEFORE any code is written for this feature.
> It is the source of truth for scope, requirements, and validation.
> Agent: do not begin implementation until this file is approved by the user.
> Any change to scope mid-implementation must be reflected here first.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | |
| Roadmap phase | e.g. `Phase 2` |
| Branch | `feature/[phase]-[short-description]` |
| Status | `[ ] Draft / [ ] Approved / [ ] In Progress / [ ] Done` |
| Depends on | e.g. `Phase 1 complete`, `auth system`, `none` |
| Created | [DATE] |
| Last updated | [DATE] |

---

## 1. Goal

<!-- One sentence. What capability exists after this feature that didn't before?
     Write it from the user's perspective, not the implementation's. -->

_[e.g. "Users can log in with email and password and receive a JWT for subsequent requests."]_

---

## 2. Background & Context

<!-- Why is this feature being built now? What problem does it solve?
     Reference the mission or roadmap phase if relevant.
     Keep to 3–5 sentences. -->

_[Context here]_

---

## 3. Scope

### In scope
<!-- Be specific. Vague scope creates vague code. -->

- [ ] _[Specific deliverable or behaviour]_
- [ ] _[Specific deliverable or behaviour]_

### Out of scope
<!-- Explicitly state what this feature does NOT cover.
     This prevents the agent from gold-plating or drifting. -->

- _[e.g. "Password reset is not part of this feature."]_
- _[e.g. "OAuth login is deferred to Phase 4."]_

---

## 4. Requirements

<!-- These are the rules the implementation must follow.
     Not HOW to implement — WHAT must be true when done.
     Split into functional (what it does) and non-functional (how it behaves). -->

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | | `Must` / `Should` / `Nice to have` |
| F2 | | |
| F3 | | |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | No hardcoded values | All config via env vars or config module |
| NF2 | All errors caught and logged with context | No silent failures |
| NF3 | Structured logging at all boundaries | Use project logging library |
| NF4 | | |

> NF1–NF3 are inherited from `tech-stack.md` and apply to every feature.
> Add feature-specific non-functional requirements from NF4 onward.

---

## 5. Implementation Plan

<!-- The sequence of work. Written at a task level — specific enough to act on,
     not so granular it micromanages implementation details.
     Each task should map to roughly one commit. -->

- [ ] **Task 1:** _[e.g. "Create database schema for users table with migration"]_
- [ ] **Task 2:** _[e.g. "Implement password hashing utility — use bcrypt, no custom crypto"]_
- [ ] **Task 3:** _[e.g. "Build POST /auth/login endpoint — validate input, query db, return JWT"]_
- [ ] **Task 4:** _[e.g. "Add JWT validation middleware for protected routes"]_
- [ ] **Task 5:** _[e.g. "Write unit tests for hashing utility and login handler"]_
- [ ] **Task 6:** _[e.g. "Update .env.example with JWT_SECRET and TOKEN_EXPIRY"]_

> Tasks are sequential unless marked `[parallel]`.
> If a task reveals unexpected complexity, stop and update this plan before continuing.

---

## 6. API / Interface Design

<!-- Only fill this out if the feature introduces or changes an API, CLI command,
     UI surface, or data schema. Skip if not applicable. -->

### Endpoints (if applicable)

```
METHOD /path
Headers: { ... }
Request body: { ... }
Success response: { ... }
Error responses:
  - 400: { "error": { "code": "...", "message": "..." } }
  - 401: ...
  - 500: ...
```

### Data schema (if applicable)

```sql
-- or JSON schema, or TypeScript interface — use whatever fits
```

### CLI interface (if applicable)

```
command [subcommand] [flags]
  --flag-name    description    default: ...
```

---

## 7. Error Handling Map

<!-- For every meaningful failure path in this feature, define the expected behaviour.
     "Meaningful" means: user-facing, data-affecting, or externally-dependent. -->

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| _[e.g. DB connection fails on login]_ | Return 500, log full error with context | Yes — ERROR level | "Something went wrong. Please try again." |
| _[e.g. Invalid credentials]_ | Return 401, log attempt with username (no password) | Yes — WARN level | "Invalid email or password." |
| _[e.g. Malformed request body]_ | Return 400, log at DEBUG | No | "Invalid request." |

---

## 8. Validation Checklist

<!-- This is how we verify the feature is done.
     Every item must pass before the branch is merged.
     Automated tests are preferred. Manual steps are acceptable for simple cases.
     For complex features with many moving parts, automated tests are mandatory. -->

### Automated tests
- [ ] _[e.g. "Unit test: password hashing returns consistent output, rejects empty strings"]_
- [ ] _[e.g. "Unit test: JWT generation and validation round-trip"]_
- [ ] _[e.g. "Integration test: POST /auth/login returns 200 with valid credentials"]_
- [ ] _[e.g. "Integration test: POST /auth/login returns 401 with wrong password"]_

### Manual checks
- [ ] _[e.g. "curl POST /auth/login with valid credentials — confirm JWT returned"]_
- [ ] _[e.g. "curl protected route without token — confirm 401"]_
- [ ] _[e.g. "Check logs — confirm login attempt is logged with email, no password"]_
- [ ] _[e.g. "Remove JWT_SECRET from .env — confirm app fails at startup with clear error"]_

### Code quality gates
- [ ] No hardcoded values in any new or modified file
- [ ] All error paths handled and logged
- [ ] `.env.example` updated if new env vars added
- [ ] No `console.log` / `print()` left in code
- [ ] All new functions have explicit return types / type hints
- [ ] Branch is clean — no unrelated changes

---

## 9. Open Questions

<!-- Unresolved decisions that must be answered before or during implementation.
     Clear these before marking the spec as Approved.
     Move to Decisions Log once resolved. -->

| # | Question | Raised by | Status |
|---|----------|-----------|--------|
| Q1 | | Agent / User | `[ ] Open / [x] Resolved` |

---

## 10. Decisions Log

<!-- Record decisions made during spec or implementation, with rationale.
     Prevents re-litigating the same questions in future sessions. -->

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| | | | |

---

_Last updated: [DATE] — [AUTHOR]_
