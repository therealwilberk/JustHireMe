# Subagent Template — Codebase Unit Map

> Use this template for every unit. Do not deviate — output format feeds the orchestrator's flow synthesis and HTML builder.

---

## Unit assignment

Fill this in from what the orchestrator tells you:

```
# Map: [Unit Name]
**File:** `docs/maps/[unit-name].md`
**Codebase path(s):** [list every directory or file in scope]
**Files in scope:** N
**Total lines:** ~N
**Generated:** [date]
```

---

## 1. Unit summary

One paragraph. What is this unit? Its role in the overall app? What it owns, what it depends on, what depends on it.

---

## 2. File inventory

List every file in scope. Do not skip any file.

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `path/to/file.py` | N | what it does | 🟢 / 🟠 / 🔴 etc |

---

## 3. Detailed breakdown

For each file, produce this breakdown:

### `path/to/file.py`

**Purpose:** One paragraph. What does this file do? Is it still needed? Does the name match the content?

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from x import y` | stdlib/3rd-party/local | yes / no | 🟢 — standard / 🔴 — unused import |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `MAX_RETRIES` | int | 3 | `fetch_page()` | 🟢 — reasonable default / 🔵 HARDCODED — should be in config |

**Classes:**

#### `ClassName`
- **Inherits from:** X or None
- **Purpose:** one sentence — what it models or manages
- **Still needed:** yes / no / unclear
- **Flag:** with reason

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `__init__` | ... | None | setup | 🟢 |
| `do_thing` | x: str | bool | checks condition | 🔴 DEAD — never called |

**Functions:**

#### `function_name(params) -> return_type`
- **Purpose:** what it does and why it exists
- **Called by:** list callers (or "unknown within this unit — check cross-refs")
- **Calls:** list callees within this file
- **Side effects:** DB write / WS emit / file I/O / process exit / none
- **Hardcodes:** list any baked-in values
- **Flag:** with reason

**Exports (what other modules import from this file):**

| Export | Known importers |
|--------|----------------|
| `ClassName` | (list or "unknown — cross-ref needed") |

---

## 4. Flags summary

All flagged items consolidated.

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 DEAD | `orphan_function` | `file.py:42` | Never called in this unit — verify cross-unit |
| P1 | 🟣 COUPLED | `shared_mutable_state` | `file.py:88` | Mutated by 3 modules, no lock |
| P1 | 🔵 HARDCODED | `"localhost:8000"` | `file.py:17` | Should read from settings |
| P1 | ⚪ INCOMPLETE | `todo_function` | `file.py:200` | Raises NotImplementedError |
| P2 | 🟠 STALE | `old_api_call` | `file.py:55` | Uses v1 endpoint, API now v2 |
| P2 | 🟡 SUSPECT | `ambiguous_helper` | `file.py:120` | Purpose unclear, only 1 caller, may be dead |
| P3 | 🟢 CLEAN | `well_tested_fn` | `file.py:300` | — |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- List known consumers from other units

**Outbound (this unit depends on others):**
- List units this one calls or imports from

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| fastapi | HTTP server | >=0.136.1 | 🔵 HARDCODED — loose pin |

---

## 6. First principles assessment

For each file, answer concisely:

1. **Does this file need to exist?** Yes / No / Partially — one-line reasoning.
2. **Does it do what it claims?** Yes / No / Partially — flag name-to-behavior drift.
3. **Is it the right place for this logic?** Yes / No — note if logic belongs in a different layer.
4. **What would break if deleted?** List concrete dependents or "nothing confirmed — potential dead code."

---

## Flag rules

| Rule | Detail |
|------|--------|
| 🟢 CLEAN is still a flag | Every item needs assessment, even if nothing is wrong |
| 🟡 SUSPECT for cross-ref uncertainty | If you can't confirm dead beyond your unit, mark SUSPECT not DEAD. Orchestrator does the cross-unit check. |
| One reason per flag | Every flag must include a one-line "why" |
| Read first | Read every file in your scope before writing anything |
| Don't skip files | Even `__init__.py` gets a row in the inventory |
