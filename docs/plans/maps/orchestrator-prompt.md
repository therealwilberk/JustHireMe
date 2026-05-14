# Orchestrator — Full Codebase Map

> Coordinates parallel subagent analysis of the entire JustHireMe codebase.
> No code changes. Output: `docs/maps/*.md` for later interactive HTML build.

---

## What this produces

One `.md` per codebase unit, each with a full flag-based breakdown (every function, class, constant, import assessed). The orchestrator then synthesizes cross-unit flows and a master index.

**Output location:** `docs/maps/` (created if missing)

---

## Step 1 — Setup

```bash
mkdir -p docs/maps
```

---

## Step 2 — Unit assignments

18 units, scoped for balanced subagent workload. Tiny files merged. Giant files (`db/client.py`, agents/) split.

| Unit | Scope | Files | ~Lines |
|------|-------|-------|--------|
| `tauri` | src-tauri/ src, config, capabilities | `lib.rs`, `main.rs`, `tauri.conf.json` | ~480 |
| `backend-main` | Backend entry & shared | `main.py`, `llm.py`, `mcp_server.py`, `logger.py`, `log_context.py` | ~1,100 |
| `backend-foundations` | Core utilities, schemas, models | `core/` (3), `schemas/` (3), `models/` (2) | ~150 |
| `backend-config` | Pydantic config layer | `config/` (10 files) | ~600 |
| `backend-routes` | FastAPI route handlers | `routes/` (8 files) | ~1,660 |
| `backend-services` | Business logic services | `services/` (7 files) | ~900 |
| `backend-db` | Single giant: all 3 DB CRUD | `db/client.py` | 1,628 |
| `backend-scrapers` | Job discovery agents | `scout.py`, `free_scout.py`, `x_scout.py`, `quality_gate.py`, `query_gen.py` | ~2,500 |
| `backend-evaluators` | Scoring & ranking agents | `evaluator.py`, `scoring_engine.py`, `feedback_ranker.py`, `semantic.py`, `lead_intel.py` | ~2,200 |
| `backend-generators` | Output generation agents | `generator.py`, `ingestor.py` | ~1,780 |
| `backend-integrations` | External integrations agents | `actuator.py`, `contact_lookup.py`, `help_agent.py`, `selectors.py`, `browser_runtime.py`, `github_ingestor.py`, `linkedin_parser.py`, `portfolio_ingestor.py` | ~1,900 |
| `backend-tests` | Full backend test suite | `tests/` (18 test files + helpers) | ~3,500 |
| `frontend-core` | Root React files & types | `App.tsx`, `main.tsx`, `types.ts`, `SettingsModal.tsx`, `index.css` | ~550 |
| `frontend-components` | Reusable UI components | `components/` (11 files) | ~1,200 |
| `frontend-views` | Workspace view pages | `views/` (8 files + test files) | ~2,100 |
| `frontend-hooks` | Custom React hooks | `hooks/` (5 files) | ~400 |
| `frontend-settings` | Settings panels | `settings/` (5 files) | ~600 |
| `build-ci` | Build, CI/CD, deps, scripts | `.github/workflows/`, `pyproject.toml`, `package.json`, `scripts/` | ~800 |

---

## Step 3 — Spawn subagents

For each unit, spawn a subagent with:

1. The unit's scope (list of files)
2. The subagent template (`docs/plans/maps/subagent-template.md`)
3. Output path: `docs/maps/{unit-name}.md`

The subagent reads every file in its scope, then produces the map file using the template.

**Do not proceed to Step 4 until all 18 map files exist in `docs/maps/`.**

Pro tip: batch into waves. First wave: the 4 agent units (scrapers, evaluators, generators, integrations — they're the largest). Second wave: everything else.

---

## Step 4 — Verification

Before synthesizing flows and index, verify:

1. All 18 files exist in `docs/maps/`
2. For each 🔴 DEAD flag, check that the item isn't imported by ANOTHER unit's scope (cross-unit dead check). A function unused in `db/client.py` but imported by `routes/leads.py` is NOT dead — it's SUSPECT from db's perspective but CLEAN globally.
3. Resolve any contradictions between units (e.g., Unit A flags something as DEAD that Unit B depends on).
4. Flag any missing files or units with zero flags (possible incomplete analysis).

---

## Step 5 — Synthesize `docs/maps/flows.md`

Read Section 7 (Flows identified) from every completed map. Identify at minimum these flows:

| Flow | Trigger | Key participants |
|------|---------|-----------------|
| Scan | POST /api/v1/scan | routes/scan, services/scanner, agents/scout, agents/evaluator, db/client, core/ws_manager |
| Ghost mode | APScheduler tick | services/ghost, services/scanner, agents/scout, agents/evaluator, db/client |
| Ingest | POST /api/v1/ingest | routes/ingest, agents/ingestor, db/client |
| Application fire | POST /api/v1/fire | routes/actions, agents/generator, agents/actuator, db/client |
| Settings | GET/POST /api/v1/settings | routes/settings, services/provider_probe, db/client |
| WebSocket | Connection to /ws | routes/ws, core/ws_manager, all agent broadcasts |
| Reevaluation | POST /api/v1/reevaluate | routes/scan/internal, services/scanner, agents/evaluator |
| Help/chat | POST /api/v1/help | routes/misc, agents/help_agent, llm |

For each flow document:
- **Entry point** (file + function)
- **Step-by-step** sequence through participants
- **Exit points** (success, error, cancellation)
- **Known flags** that affect this flow (any 🔴🟠🟡⚪ in its participants)

---

## Step 6 — Synthesize `docs/maps/INDEX.md`

Master index consolidating all flags across all units:

```
# Codebase Map — Master Index
**Total files mapped:** N
**Total flags:** N (🔴 N | 🟠 N | 🟡 N | 🔵 N | 🟣 N | ⚪ N | 🟢 N)

## Map files
| File | Unit | Files covered | Top flags |

## Flag summary (all flags across all units)
| Priority | Flag | Item | File:Line | Reason |

## Priority groupings
- **P0 (blocking):** all 🔴 DEAD
- **P1 (high impact):** all 🟣 COUPLED + 🔵 HARDCODED + ⚪ INCOMPLETE
- **P2 (medium):** all 🟠 STALE + 🟡 SUSPECT
- **P3 (monitor):** all 🟢 CLEAN (no action needed)

## Flow index
| Flow | Entry | Key participants |
```

---

## Rules

- **No code changes.** Analysis only. Zero writes to `.py`, `.tsx`, `.rs`, config files.
- **Read before writing.** Every subagent reads its entire scope before a single line of output.
- **No assumptions.** If purpose is unclear, say so and mark 🟡 SUSPECT.
- **Every file gets a breakdown.** No file skipped, even `__init__.py`.
- **Flag everything.** Every function, class, constant, import gets at least 🟢 CLEAN.
- **Cross-reference before DEAD.** Confirm dead beyond your unit before assigning 🔴.

---

## Flag taxonomy

| Flag | Label | Meaning | Priority |
|------|-------|---------|----------|
| 🔴 | DEAD | Confirmed unreachable / unused / superseded. Safe to delete. | P0 |
| 🟠 | STALE | Was functional, now outdated — wrong path, wrong API, wrong assumption. | P2 |
| 🟡 | SUSPECT | Unclear if still needed. Used somewhere but purpose ambiguous. Needs human. | P2 |
| 🔵 | HARDCODED | Value or path that should be config/env but is baked in. | P1 |
| 🟣 | COUPLED | Tightly bound to another module — circular risk, no clean interface. | P1 |
| ⚪ | INCOMPLETE | Stub, TODO, partial implementation, placeholder. | P1 |
| 🟢 | CLEAN | Functional, well-scoped, no issues noted. | P3 |

Every flag must include a one-line reason. Example: `🔵 HARDCODED — port 8000 baked in, should read from settings`

---

## Output checklist

Before declaring done:
- [ ] All 18 map files in `docs/maps/`
- [ ] `docs/maps/flows.md` — all 8 flows documented
- [ ] `docs/maps/INDEX.md` — master index with cross-unit flags
- [ ] No source files modified
- [ ] Cross-unit DEAD resolution completed
