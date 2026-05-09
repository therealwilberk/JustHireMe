# Tech Stack

> **Living document.** When a technology decision changes, update this file AND note the reason.
> Agent: treat this file as the source of truth for all tooling, language, and architecture decisions.
> Never introduce a new dependency or deviate from patterns defined here without explicit instruction.

---

## Language(s)

<!-- List all languages in use. Mark primary. -->

| Language | Version (pin this) | Role |
|----------|--------------------|------|
|          |                    | e.g. Backend logic |
|          |                    | e.g. Scripting / tooling |

---

## Runtime & Environment

<!-- Node, Python, Bun, JVM, etc. Pin versions. -->

| Runtime | Version | Notes |
|---------|---------|-------|
|         |         |       |

---

## Framework(s)

<!-- List all frameworks. Explain why each was chosen if non-obvious. -->

| Framework | Version | Layer | Reason for choice |
|-----------|---------|-------|-------------------|
|           |         |       |                   |

---

## Database

<!-- Include ORM or query layer if applicable. -->

| Component | Choice | Notes |
|-----------|--------|-------|
| Database engine |  | e.g. SQLite for local-first, Postgres for production |
| ORM / query layer |  | |
| Migration tool |  | |

---

## Key Libraries & Dependencies

<!-- Only list dependencies that have architectural significance.
     Do not list every npm package — only ones that constrain design decisions. -->

| Package | Version (pinned) | Purpose | Notes |
|---------|------------------|---------|-------|
|         |                  |         |       |

> **Rule:** All dependencies must have pinned versions in lockfiles.
> No floating `^` or `~` versions for production dependencies without documented justification.

---

## Architecture Pattern

<!-- Describe the high-level structure. Be explicit. -->

_[e.g. "Monolithic Node.js server with a React SPA frontend. No microservices. Single deployment unit."]_

### Directory Structure (top-level)

```
[PROJECT_ROOT]/
├── specs/          # SDD documents (constitution, feature specs, audit)
├── src/            # Application source
├── tests/          # All tests (unit, integration)
├── scripts/        # Dev/ops tooling
└── ...
```

---

## Code Quality Standards

<!-- These are enforced rules, not suggestions. Agent must follow all of these. -->

### General
- [ ] No hardcoded values — all config via environment variables or a dedicated config module
- [ ] No `console.log` / `print` left in production code — use structured logging only
- [ ] Every function has a single, clear responsibility
- [ ] No silent failures — all errors must be caught, logged, and handled explicitly

### Logging
- **Library:** `[e.g. pino, winston, loguru]`
- **Format:** `[e.g. JSON structured logs with timestamp, level, message, context]`
- **Levels in use:** `DEBUG | INFO | WARN | ERROR`
- **Rule:** Log at boundaries (function entry/exit for complex ops, all error paths). Never swallow exceptions silently.

### Error Handling
- All async operations must handle rejection explicitly — no unhandled promise rejections
- Errors must propagate with context, not be swallowed (`throw new Error('context: ' + originalError.message)`)
- User-facing errors must never expose internal stack traces
- Distinguish between operational errors (expected, recoverable) and programmer errors (bugs)

### TypeScript (if applicable)
- Strict mode: `"strict": true` in `tsconfig.json` — non-negotiable
- No `any` without explicit comment justification
- All exported functions must have explicit return types

### Python (if applicable)
- Type hints required on all function signatures
- Use `logging` module — never bare `print()` in non-script code
- `mypy` or `pyright` for static type checking

---

## Testing Strategy

<!-- Define what gets tested and how. -->

| Test Type | Tool | Scope | When it runs |
|-----------|------|-------|--------------|
| Unit      |      |       | On every commit |
| Integration |    |       | On PR / before merge |
| Manual    | Checklist (see feature specs) | Happy path + edge cases | Pre-release |

> **Rule:** New features require corresponding tests before they are considered complete.
> Automated tests are preferred. For complex features with many moving parts, automated tests are mandatory.

---

## API Design (if applicable)

- **Style:** `[e.g. REST, GraphQL, RPC]`
- **Versioning:** `[e.g. /api/v1/...]`
- **Auth:** `[e.g. JWT, API key, session]`
- **Error responses:** All errors return structured JSON: `{ "error": { "code": "...", "message": "..." } }`

---

## Environment & Configuration

- All secrets via environment variables — never committed to version control
- `.env.example` must be kept up to date with all required variables (no values, just keys + descriptions)
- Config validation at startup — app must fail fast with a clear error if required env vars are missing

---

## Infrastructure & Deployment

| Concern | Approach | Notes |
|---------|----------|-------|
| Hosting |          |       |
| CI/CD   |          |       |
| Containerization |  |     |
| Secrets management | |    |

---

## Decisions Log

<!-- Record significant technical decisions here as they are made.
     Format: DATE — DECISION — REASON — ALTERNATIVES CONSIDERED -->

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
|      |          |        |                         |

---

_Last updated: [DATE] — [AUTHOR]_
