# Prompt — Map `main.py` (No Code Changes)
> Analysis only. Zero writes. Feed the report into the refactor prompt later.

---

## Instructions for the agent

You are producing a complete structural map of `backend/main.py`.
**Do not change a single line of code. Do not suggest fixes yet.
Your only output is the report described below.**

You may spawn subagents to parallelize section analysis.
If you do, each subagent reads its assigned section independently
and reports back. You then synthesize into one unified report.

---

## Step 1 — Orient
Read `backend/main.py` fully before doing anything else.
Note the total line count.
Identify the top-level structure: are there classes, are there
loose functions, are there sections separated by comments?
Confirm you have read the entire file before proceeding.

---

## Step 2 — Subagent breakdown (if file > 500 lines)
Divide the file into logical sections by line range.
Assign each section to a subagent with this instruction:

```
Read lines [START] to [END] of main.py.
Do not read outside your range.
Produce the following for your section:

1. IMPORTS (if in your range)
   - Every import statement
   - Whether it is stdlib / third-party / local
   - Whether it appears to actually be used in this section

2. CONSTANTS & CONFIG
   - Every module-level variable, constant, env var read
   - Its type, default value, and where it is used

3. CLASSES
   For each class:
   - Name, line number
   - Parent class(es) if any
   - Purpose (one sentence, inferred from code)
   - All methods: name, line number, parameters, return type if annotated
   - Instance variables set in __init__
   - Any class variables

4. FUNCTIONS
   For each function (not inside a class):
   - Name, line number
   - Parameters with types if annotated
   - Return type if annotated
   - Purpose (one sentence, inferred)
   - What it calls (other functions, classes, external libs)
   - What calls it (if determinable from this section)
   - Any side effects (writes to DB, emits events, mutates global state)

5. ROUTES (if FastAPI routes present)
   For each route:
   - Method + path
   - Handler function name
   - Request body / query params
   - Response model if specified
   - Dependencies injected

6. EXCEPTION HANDLING
   - Every try/except block
   - What exception is caught (specific type or bare Exception)
   - What happens in the except: (logged? re-raised? passed silently?)
   - Flag every bare `except: pass` or `except Exception: pass` explicitly

7. GLOBAL STATE
   - Any module-level mutable objects (dicts, lists, instances)
   - Anything that looks like it should be a class but isn't

8. NOTED ISSUES
   - Indentation risks (deeply nested blocks, mixed indent levels)
   - Functions over 50 lines
   - Functions doing more than one thing
   - Anything that will cause problems during refactor
```

---

## Step 3 — Synthesize into the full report

Combine all subagent outputs into one report structured as follows.
Do not include code snippets unless illustrating a specific issue.
This is a reference document, not a tutorial.

---

# `main.py` Structure Report

**File:** `backend/main.py`
**Lines:** N
**Generated:** [date]

---

## 1. Imports
| Import | Type | Used |
|--------|------|------|
| `from fastapi import FastAPI` | third-party | yes |
| ... | | |

Unused imports:
- list any here

---

## 2. Constants & Global Config
| Name | Type | Default | Used By |
|------|------|---------|---------|
| `API_KEY` | str | env var | `auth_middleware`, `validate_key` |
| ... | | | |

Global mutable state (flag these — they complicate refactor):
- list any here

---

## 3. Class Map
For each class:

### `ClassName` (line N)
- **Inherits from:** X or None
- **Purpose:** one sentence
- **Instance vars:** `self.x`, `self.y`
- **Methods:**
  | Method | Line | Params | Returns | Calls | Side Effects |
  |--------|------|--------|---------|-------|--------------|
  | `__init__` | N | ... | None | ... | sets self.x |
  | ... | | | | | |

---

## 4. Function Map
For each standalone function:

### `function_name` (line N)
- **Params:** `x: type`, `y: type`
- **Returns:** `type` or unknown
- **Purpose:** one sentence
- **Calls:** `other_func()`, `SomeClass.method()`
- **Called by:** `route_handler`, `startup_event`
- **Side effects:** writes to DB / emits WS event / mutates global / none

---

## 5. Route Map
| Method | Path | Handler | Body | Params | Response Model |
|--------|------|---------|------|--------|----------------|
| GET | `/leads` | `get_leads` | none | `limit`, `offset` | `LeadList` |
| ... | | | | | |

---

## 6. Exception Handling Audit
| Location | Caught | Handling | Risk |
|----------|--------|----------|------|
| `save_lead()` line N | `Exception` | `pass` | SILENT FAILURE |
| `connect_ws()` line N | `ConnectionError` | logged | ok |
| ... | | | |

Silent failures (bare pass) — full list:
- line N: `function_name` — [what is being swallowed]

---

## 7. Dependency Graph
Which functions/classes depend on which others.
Format as a simple list of relationships:

- `route_handler_x` → calls → `service_function_y`
- `service_function_y` → calls → `db_client.method`
- `WebSocketManager` → used by → `broadcast_route`, `connect_route`
- ...

Circular dependencies (if any):
- list here

---

## 8. Refactor Risk Assessment
Things that will require special care during the split.

### High Risk
- Items that touch global state
- Functions with many callers spread across the file
- Classes with mixed responsibilities

### Medium Risk
- Long functions (>50 lines) — list with line ranges
- Functions doing more than one thing
- Deeply nested blocks

### Low Risk
- Isolated utility functions with no side effects
- Pure data transformation functions

---

## 9. Suggested Module Boundaries
Based on the analysis, these are the natural split points.
Do not treat this as a refactor plan — it is an observation only.

Suggested modules (folders/files):
- `routes/leads.py` — contains: [list handlers]
- `routes/ws.py` — contains: [list handlers]
- `services/quality_gate.py` — contains: [list functions]
- `db/` — already exists, note what should move here
- `core/config.py` — constants and env vars
- `core/exceptions.py` — custom exception classes
- `core/logging.py` — logging setup
- [add others as analysis reveals]

What must stay in `main.py` (FastAPI app init, lifespan, middleware):
- list here

---

## 10. Open Questions for Refactor
Things the analysis couldn't determine — need human decision:
- Is X intentionally global or should it be injected?
- Does Y belong in services or routes?
- Is Z dead code or called from somewhere outside this file?

---

## Step 4 — Final check before submitting report
Before submitting, verify:
- [ ] Every function is accounted for
- [ ] Every class is accounted for
- [ ] Every route is accounted for
- [ ] All bare `except: pass` instances are listed
- [ ] Dependency graph has no obvious gaps
- [ ] No code was changed at any point

Submit the report. Do not proceed to any refactor suggestions
beyond Section 9. The refactor prompt is separate.
