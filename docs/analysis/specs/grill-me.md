# Skill — Grill Me

> **When to invoke:** At the start of Mode B (constitution exists, no feature spec yet).
> Run this before writing a single line of the feature spec.
> Do not skip it — uninformed specs produce rework.
> The conversation output from this session IS the raw material for the feature spec.

---

## Purpose

Reach a shared understanding of the feature before committing anything to a spec.

The goal is not to produce a document. The goal is alignment — you and the user on the same wavelength about what is being built, why, for whom, and under what constraints. The feature spec gets written *from* that alignment, not instead of it.

---

## Instructions

### Step 1 — Orient yourself

Before asking anything, do the following silently:

1. Read `specs/mission.md` — understand project purpose and non-goals
2. Read `specs/tech-stack.md` — know the constraints before asking about implementation
3. Read `specs/roadmap.md` — identify which phase this feature belongs to
4. If brownfield or fork: read `specs/audit-report.md` — know what the codebase already does
5. If `specs/context.md` exists: read it — use established project vocabulary throughout. Do not introduce synonyms for terms already defined there.
6. Explore the codebase surface area relevant to this feature — files, modules, existing patterns. Answer what you can from code; only ask what the code cannot tell you.

### Step 2 — Interrogate

Interview the user relentlessly about every aspect of this feature until you reach a shared understanding. Walk down each branch of the decision tree, resolving dependencies between decisions one by one.

**Rules:**
- Ask **one question at a time**. Wait for the answer before continuing.
- For every question, provide **your recommended answer** based on what you've read. The user reviews and corrects — this is faster than answering a blank form.
- If a question can be answered by exploring the codebase, explore it instead of asking.
- If a question is already answered in the constitution files, do not ask it — use the answer.
- Prioritise questions in this order:
  1. Scope and boundaries — what's in, what's explicitly out
  2. Architectural decisions — what this touches, how it fits existing patterns
  3. Constraints — security, data handling, env config, performance
  4. Validation — how we know it's done
  5. Preferences — only if no reasonable default exists

**Question format:**
```
[Question]

My recommendation: [your recommended answer and brief reasoning]
```

### Step 3 — Identify the slice type

Before ending the session, confirm with the user:

- Is this a **feature** (must be a vertical slice — crosses data, logic, and interface layers)?
- Is this **infra/chore** (horizontal is fine — migrations, config, dependency work)?

If it's a feature, verify that the scope you've aligned on actually crosses all layers. If it doesn't, flag it and propose restructuring before the spec is written.

### Step 4 — Determine AFK vs HITL

For each major task you can already see coming out of this conversation, propose whether it's:
- `[AFK]` — self-contained, testable, agent can complete without user present
- `[HITL]` — requires user judgment during execution

Surface any surprises. If a task that looks AFK has a hidden decision point, flag it now.

### Step 5 — Produce the session summary

When the interrogation is complete, output a structured summary. This becomes the input to the feature spec — do not write the spec yet, present the summary for approval first.

```
## Grill Session Summary — [Feature Name]

**Feature goal:** [one sentence, user's perspective]

**Slice type:** Feature (vertical) / Infra (horizontal ok) / Chore

**Layers touched:**
- [ ] Data
- [ ] Logic / service
- [ ] Interface (API / CLI / UI)

**Key decisions made:**
1. [Decision] — [rationale]
2. [Decision] — [rationale]

**Explicit out-of-scope:**
- [item]
- [item]

**Anticipated tasks:**
- [AFK] [task description]
- [HITL] [task description — decision needed: X]

**Constraints surfaced:**
- [any new constraints not already in tech-stack.md]

**Open questions (unresolved):**
- [question] — [why it couldn't be resolved in this session]

**Context terms to record** (if specs/context.md exists or should be created):
- [term]: [definition]
```

Present this summary. Wait for approval or corrections. Only after approval: write the feature spec.

---

## Context Vocabulary (if `specs/context.md` exists)

During the session, actively maintain shared language:

- If the user uses a term that conflicts with `specs/context.md`, flag it immediately: *"Your context file defines X as Y, but you seem to mean Z — which is it?"*
- If the user uses a vague or overloaded term, propose a precise one: *"You said 'user' — do you mean an authenticated account holder or a guest session? Those are different things."*
- If a new term crystallises during the session, note it in the summary under **Context terms to record**. Do not write to `specs/context.md` during the grill session — update it after the summary is approved.

---

## When to Stop

Stop the interrogation when:
- All scope boundaries are clear
- All architectural decisions affecting this feature are resolved
- You know how to validate that the feature is done
- No open questions remain that would block writing the spec

If you have more than 3 unresolved questions after a thorough session, the feature is probably too large or the constitution is incomplete. Flag this before writing the spec.

---

## What This Is Not

- This is not a requirements-gathering form. It is a conversation.
- This is not a planning session. No tasks are committed until the spec is approved.
- This is not a code review. Do not propose implementations during the grill.
- This is not optional. Do not skip it to save time — misalignment costs more.

---

_Part of the SDD template system — `specs/agent-primer.md` Section 1, Mode B_
