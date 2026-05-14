> **Original draft.** Modularized version split into `orchestrator-prompt.md` + `subagent-template.md`.

# Prompt — Full Codebase Map (Subagent Archaeology)
> Complete structural analysis of the entire JustHireMe Linux fork.
> No code changes. One output `.md` per logical unit.
> Subagents work in parallel. Orchestrator synthesizes.

---

## What this produces

A set of structured `.md` map files covering every part of the codebase.
These become the source of truth for future refactor, documentation,
and the interactive HTML explorer you'll build later.

**Output location:** `docs/maps/`

---

## Flag spectrum

Every function, class, file, config value, and dependency gets flagged.
A single item can carry multiple flags.

| Flag | Label | Meaning |
|------|-------|---------|
| 🔴 | `DEAD` | Confirmed unreachable / unused / superseded. Safe to delete. |
| 🟠 | `STALE` | Was functional, now outdated — wrong path, wrong API, wrong assumption. Needs update not deletion. |
| 🟡 | `SUSPECT` | Unclear if still needed. Used somewhere but purpose is ambiguous or logic seems broken. Needs human decision. |
| 🔵 | `HARDCODED` | Value or path that should be config/env but is baked in. |
| 🟣 | `COUPLED` | Tightly bound to another module — circular risk, implicit dependency, no clean interface boundary. |
| ⚪ | `INCOMPLETE` | Stub, TODO, partial implementation, placeholder. |
| 🟢 | `CLEAN` | Functional, well-scoped, no issues noted. |

**Every flag must include a one-line reason.**
Example: `🔵 HARDCODED — port 8000 baked in, should read from settings`

---

## Step 1 — Orchestrator: full codebase inventory

Before spawning any subagents, read the top-level directory structure.
Produce a complete file tree. Identify every file by path.
Group files into logical units (defined below).
Assign one subagent per unit.
Do not begin subagent work until the inventory is complete.
Output the inventory and unit assignments before proceeding.

---

## Logical units and their assigned map files

Each subagent is responsible for one unit and produces one `.md` file.

| Unit | Subagent | Output file |
|------|----------|-------------|
| Tauri shell | SA-01 | `docs/maps/tauri.md` |
| Backend — core | SA-02 | `docs/maps/backend-core.md` |
| Backend — routes | SA-03 | `docs/maps/backend-routes.md` |
| Backend — services | SA-04 | `docs/maps/backend-services.md` |
| Backend — agents | SA-05 | `docs/maps/backend-agents.md` |
| Backend — db | SA-06 | `docs/maps/backend-db.md` |
| Backend — schemas | SA-07 | `docs/maps/backend-schemas.md` |
| Backend — config & secrets | SA-08 | `docs/maps/backend-config.md` |
| Backend — tests | SA-09 | `docs/maps/backend-tests.md` |
| Frontend — components | SA-10 | `docs/maps/frontend-components.md` |
| Frontend — hooks & state | SA-11 | `docs/maps/frontend-hooks.md` |
| Frontend — lib & utils | SA-12 | `docs/maps/frontend-lib.md` |
| Frontend — types | SA-13 | `docs/maps/frontend-types.md` |
| Frontend — tests | SA-14 | `docs/maps/frontend-tests.md` |
| Build & CI | SA-15 | `docs/maps/build-ci.md` |
| Root config & scripts | SA-16 | `docs/maps/root-config.md` |
| Flows (orchestrator only) | orchestrator | `docs/maps/flows.md` |
| Master index (orchestrator only) | orchestrator | `docs/maps/INDEX.md` |

If a unit does not exist in this codebase, the subagent notes it as
absent and produces a minimal file saying so. Do not skip the file.

---

## Step 2 — Subagent instructions

Every subagent follows this exact template for their assigned unit.
Deviation from the template breaks the later HTML build — follow it exactly.

---

### SUBAGENT TEMPLATE

```
# Map: [Unit Name]
**File:** `docs/maps/[filename].md`
**Assigned to:** SA-[N]
**Codebase path(s):** [list every directory or file in scope]
**Generated:** [date]

---

## 1. Unit summary
One paragraph. What is this unit? What is its role in the overall app?
What does it own? What does it depend on? What depends on it?

---

## 2. File inventory
List every file in this unit's scope.

| File | Lines | Purpose (one line) | Overall flag |
|------|-------|--------------------|--------------|
| `path/to/file.py` | N | what it does | 🟢 / 🟠 / 🔴 etc |

---

## 3. Detailed file breakdowns
For each file in the inventory, produce a full breakdown.

### `path/to/file.py`

**Purpose:** One paragraph. What does this file do? Is it still needed?
Does it do what its name implies?

**Imports:**
| Import | Type | Used | Flag |
|--------|------|------|------|
| `from x import y` | stdlib/3rd-party/local | yes/no | 🟢/🔴 etc |

**Constants & module-level state:**
| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|

**Classes:**
For each class:

#### `ClassName`
- **Inherits from:** X or None
- **Purpose:** one sentence — what it models or manages
- **Still needed:** yes / no / unclear
- **Flag(s):** with reason

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `__init__` | ... | None | setup | 🟢 |

**Functions:**
For each function (including private `_` prefixed):

#### `function_name(params) -> return_type`
- **Purpose:** what it does and why it exists
- **Called by:** list callers (or "unknown — check cross-refs")
- **Calls:** list callees
- **Side effects:** DB write / WS emit / file I/O / process exit / none
- **Hardcodes:** list any baked-in values
- **Flag(s):** with reason

**Exports (what other modules import from this file):**
| Export | Imported by |
|--------|-------------|

---

## 4. Flags summary
All flagged items in this unit, consolidated.

| Flag | Item | Location | Reason |
|------|------|----------|--------|
| 🔴 DEAD | `old_function` | `file.py:42` | Never called anywhere in codebase |
| 🔵 HARDCODED | `"localhost:8000"` | `config.py:17` | Should read from env |

---

## 5. Dependencies
What this unit needs from other units, and what other units need from it.

**Inbound (other units depend on this):**
- `backend-routes` imports `cm` from `core/ws_manager.py`

**Outbound (this unit depends on others):**
- `backend-db` — all DB operations go through `db/client.py`

**External (third-party libs used):**
| Library | Used for | Version pinned | Flag |
|---------|----------|----------------|------|

---

## 6. First principles assessment
For each file or major component, answer:

1. **Does this need to exist?**
   Yes / No / Partially — with one sentence of reasoning.

2. **Does it do what it claims?**
   Yes / No / Partially — flag drift between name/docs and actual behavior.

3. **Is it the right place for this logic?**
   Yes / No — note if logic belongs in a different layer.

4. **What would break if this was deleted?**
   List concrete dependents or "nothing confirmed."

---

## 7. Flows identified (if any)
If this unit is a participant in one or more recognizable data/control flows,
list them here. The orchestrator will consolidate these into `flows.md`.

Format:
- **Flow name:** short name
- **This unit's role:** what it does in the flow
- **Entry point in this unit:** function or route
- **Exit point:** where control passes next
```

---

## Step 3 — Flows map (orchestrator, after all subagents complete)

After all subagent `.md` files are written, the orchestrator reads every
Section 7 from every file and synthesizes `docs/maps/flows.md`.

**`docs/maps/flows.md` structure:**

```
# Application Flows

## Flow inventory
List of all identified flows with a one-line description each.

---

## [Flow Name] (e.g. "Scan Flow")

### Overview
One paragraph. What triggers this flow, what it does end to end,
what the user/system sees as a result.

### Participants
| Unit | Role |
|------|------|
| `routes/scan.py` | HTTP trigger — receives POST /api/v1/scan |
| `services/scanner.py` | Orchestrates scan task lifecycle |
| `agents/scout.py` | Performs job board scraping |
| `db/client.py` | Persists discovered leads |
| `core/ws_manager.py` | Broadcasts progress to frontend |

### Step-by-step
1. User triggers POST `/api/v1/scan`
2. `scan()` route handler checks if scan already running (ScanManager)
3. ...continue until flow terminates

### Entry point
File + function where the flow begins.

### Exit points
All ways the flow can end (success, error, cancellation).

### Known issues
Any flags (🔴🟠🟡⚪) that affect this flow.
```

Identify at minimum these flows (add others found during analysis):
- Scan flow (discovery → scout → evaluate → persist → broadcast)
- Ghost mode flow (scheduled tick → multi-phase automation)
- Ingest flow (resume/LinkedIn/GitHub/portfolio → profile)
- Application fire flow (generate assets → actuate → submit)
- Settings flow (save → validate → probe provider keys)
- WebSocket flow (connect → auth → heartbeat → broadcast → disconnect)
- Reevaluation flow (rescore existing leads)
- Help/chat flow (user query → agent → response)

---

## Step 4 — Master index (orchestrator, last)

After `flows.md` is written, produce `docs/maps/INDEX.md`.

```
# Codebase Map — Master Index
**Generated:** [date]
**Total files mapped:** N
**Total flags:** N (🔴 N | 🟠 N | 🟡 N | 🔵 N | 🟣 N | ⚪ N | 🟢 N)

## Map files
| File | Unit | Files covered | Flag summary |
|------|------|---------------|--------------|

## Flag summary (all flags across entire codebase)
Sorted by severity: 🔴 first, then 🟠, 🟡, 🔵, 🟣, ⚪

| Flag | Item | File | Line | Reason |
|------|------|------|------|--------|

## Dead code candidates
All 🔴 DEAD items in one place, ready for deletion review.

## Hardcode registry
All 🔵 HARDCODED items — location, current value, recommended replacement.

## Coupling risks
All 🟣 COUPLED items — what's coupled, why it's a risk.

## Incomplete work
All ⚪ INCOMPLETE items — stubs, TODOs, partial implementations.

## Flow index
| Flow | Entry point | Key participants |
|------|-------------|-----------------|
```

---

## Rules

**Read before writing.** Every subagent reads its entire assigned scope
before writing a single line of output.

**No code changes.** This is analysis only. Zero writes to source files.

**No assumptions.** If a function's purpose is unclear, say so and mark
🟡 SUSPECT. Do not invent intent.

**Every file gets a breakdown.** No file in scope is skipped, even if
it's empty, even if it's a single-line `__init__.py`.

**Flag everything.** Every function, class, constant, and import gets
at least one flag. 🟢 CLEAN is a valid flag — it still needs to be assigned.

**Cross-reference.** When a subagent identifies something as 🔴 DEAD,
it must check whether it's imported or called anywhere in its scope
before assigning that flag. Dead means confirmed dead, not just
"not called from within this file."

**Smart zone rule.** Each subagent is one session. If a unit is very
large (>500 lines total), the subagent proposes a breakdown and waits
for confirmation before proceeding.

**Output goes to `docs/maps/`.** All files written there.
Orchestrator creates the directory if it doesn't exist.

**Orchestrator waits.** Do not begin `flows.md` or `INDEX.md` until
all subagent `.md` files are confirmed written.
