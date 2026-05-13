# Agent Primer

> This file is the first thing you read at the start of every session.
> It defines how you operate in this project — your reading order, decision rules,
> question protocol, and coding constraints.
> If anything in this file conflicts with a user instruction given in the session,
> flag the conflict before proceeding. Do not silently override either.

---

## 1. Session Startup Protocol

At the start of every session, first determine which mode you are in:

---

### Mode A — Constitution does not exist yet

**Trigger:** `specs/mission.md`, `specs/tech-stack.md`, or `specs/roadmap.md` are missing or empty.

This session's goal is to *create* the constitution, not to build features. Follow this sequence:

1. **Research first.** Before asking anything or writing any file, use the research prompt in **Section 1.1** below. Do not skip this — uninformed specs create rework.
2. **If brownfield or fork:** Audit the codebase before writing anything. Read all files, map structure, dependencies, patterns, and issues. Output goes to `specs/audit-report.md` (template in `specs/`). The audit informs everything that follows.
3. **Interview the user.** Using what you've learned from research and/or the audit, ask grouped questions (see Section 2) to fill gaps you cannot resolve yourself. Cover: mission, target users, tech preferences, known constraints, and rough phases.
4. **Draft the three constitution files** in sequence: `mission.md` → `tech-stack.md` → `roadmap.md`. Present each for review before moving to the next.
5. **Commit the constitution** on a `docs/constitution-init` branch once all three are approved.

---

### Mode B — Constitution exists, active feature spec does not

**Trigger:** Constitution files are present. No feature spec exists for the current roadmap phase.

1. **Read `specs/mission.md`**
2. **Read `specs/tech-stack.md`**
3. **Read `specs/roadmap.md`** — identify the current active phase
4. **If brownfield or fork:** Read `specs/audit-report.md`
5. **Research the feature** if it involves unfamiliar libraries, APIs, or patterns (see Section 1.1)
6. **Draft the feature spec** via interview (see feature spec template). Get approval before writing code.
7. **Create a branch** following the git protocol in Section 4 before any code is written.

---

### Mode C — Constitution exists, feature spec exists

**Trigger:** All constitution files present. Active feature spec present in `specs/features/`.

1. **Read `specs/mission.md`**
2. **Read `specs/tech-stack.md`**
3. **Read `specs/roadmap.md`**
4. **If brownfield or fork:** Read `specs/audit-report.md`
5. **Read the active feature spec**
6. **Assess gaps** — apply question protocol (Section 2) for anything unresolved
7. **Confirm you are on the correct branch** — if not, stop and create one before proceeding

---

### 1.1 — Research Prompt

Use this when entering Mode A, or when a feature involves unfamiliar territory:

```
Before I write any specs or code for this project, I need to research the following:

Project/feature: [NAME]
Type: [new / fork / brownfield feature]
Key unknowns: [list what needs research — upstream project, tech stack options, domain conventions, known pitfalls, relevant packages]

Research tasks:
1. Understand the domain and any existing solutions or conventions
2. If fork: review the upstream project — purpose, architecture, activity, license, known issues
3. Evaluate relevant libraries or frameworks — maturity, maintenance status, tradeoffs
4. Identify common failure modes or pitfalls for this type of project
5. Surface any constraints that should inform the constitution (e.g. licensing, compatibility, performance)

Output a research summary before proceeding. Format:
- What this project/feature is and does
- Key architectural or design decisions typical for this domain
- Recommended stack or approach with brief rationale
- Risks and things to watch out for
- Open questions that only the user can answer
```

---

## 2. Question Protocol

### When to ask
Ask only when something is **genuinely unknown and consequential** — meaning:
- It is not answered in any of the files above
- Getting it wrong would require rework, cause a conflict, or violate a constraint
- You cannot make a safe, reversible assumption

Do not ask about:
- Things already in the constitution or feature spec
- Minor implementation details you can decide yourself (variable names, file structure within a module)
- Things you can infer with high confidence from the codebase

### How to ask
**Group all questions into a single block.** Never ask one question, wait for an answer, then ask another.

Format every question block like this:

```
Before I proceed, I need to clarify a few things:

1. [QUESTION] — [why this matters / what depends on the answer]
2. [QUESTION] — [why this matters / what depends on the answer]
3. [QUESTION] — [why this matters / what depends on the answer]
```

### Question priority
If you have more than 5 questions, something is wrong — either the specs are incomplete or you're asking about things you should decide yourself. In that case, flag that the specs need updating rather than dumping a long list of questions.

Prioritize questions in this order:
1. Architectural decisions (affect multiple files or future phases)
2. Constraint clarifications (security, env config, data handling)
3. Scope boundaries (what's in vs out for this feature)
4. Preference questions (only if no reasonable default exists)

---

## 3. Coding Rules

These apply to every line of code you write or modify. No exceptions, no shortcuts.

### No hardcodes
- No magic strings, numbers, or paths embedded in logic
- All configuration goes through environment variables or a dedicated config module
- If a value might ever change or differ between environments, it is not hardcoded

### Error handling
- Every error is caught, logged with context, and handled explicitly
- No silent failures — swallowing exceptions is a bug, not a choice
- Distinguish between operational errors (expected, recoverable) and programmer errors (crashes, bugs)
- User-facing messages never expose internal stack traces or raw error objects
- Async operations: handle all rejection paths explicitly

### Logging
- Use the project's designated logging library (see `tech-stack.md`)
- Use structured logs: timestamp, level, message, relevant context
- Log at boundaries: entry/exit of complex operations, all error paths, external calls
- Levels: `DEBUG` for development detail, `INFO` for normal flow, `WARN` for recoverable issues, `ERROR` for failures
- Never leave `console.log`, `print()`, or equivalent debug output in committed code

### Code quality
- One responsibility per function — if you need "and" to describe what it does, split it
- All new functions have explicit return types (TypeScript) or type hints (Python)
- No `any` in TypeScript without an inline comment explaining why
- No commented-out code committed — delete it or don't commit it
- Keep functions short enough to read without scrolling

### Environment & secrets
- Secrets and config live in environment variables — never in source code
- `.env.example` must be updated whenever a new variable is introduced
- Application must fail fast at startup if required env vars are missing, with a clear error message naming the missing variable

---

## 4. Git Protocol

### Branch naming
```
feature/[phase-name]-[short-description]
fix/[short-description]
chore/[short-description]
docs/[short-description]
```

### Commit messages
Follow conventional commits format:
```
type(scope): short description

- bullet detail if needed
- another detail
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`

Examples:
```
feat(auth): add JWT validation middleware
fix(db): handle null result on user lookup
docs(specs): update roadmap phase 2 status
```

### Rules
- **You must be on a branch before touching any file in the codebase.** No exceptions — not for one-line fixes, not for "quick" changes, not for anything. If you are on `main` or `master`, stop and create a branch first.
- Commits are small and focused — one logical change per commit
- Never commit directly to `main` or `master`
- Feature specs are committed before implementation begins — on a `docs/` branch if the constitution doesn't exist yet, or the active feature branch if it does
- Validation checklist must pass before a branch is merged
- If you realize mid-session that you forgot to branch, stop immediately, create the branch, and note it

---

## 5. What "Done" Means

A feature is not done when the code is written. It is done when:

- [ ] All items in the feature spec validation checklist pass
- [ ] No hardcoded values introduced
- [ ] Error handling covers all failure paths in the new code
- [ ] Logging added at appropriate boundaries
- [ ] `.env.example` updated if new env vars were added
- [ ] Relevant tests written and passing
- [ ] `specs/roadmap.md` phase status updated
- [ ] Changes committed with clean, conventional commit messages

---

## 6. When You're Unsure

If you encounter something ambiguous — a conflict between files, an architectural pattern that seems inconsistent, a constraint that isn't clear — **stop and flag it** before proceeding.

Format:
```
⚠️ Ambiguity detected

[What I found]
[Why it's a problem]
[Options I see]
[What I recommend]

Should I proceed with the recommendation, or do you want to decide?
```

Do not resolve ambiguity silently. Do not make a judgment call on anything that touches architecture, security, or scope without surfacing it first.

---

_Last updated: [DATE] — [AUTHOR]_
