# Codebase Map — Master Index

**Generated:** 2026-05-15
**Total files mapped:** 129
**Total flags:** 323 (🔴 18 | 🔵 105 | 🟣 26 | ⚪ 5 | 🟠 12 | 🟡 85 | 🟢 72)

## Map files

| File | Unit | Files covered | Top flags |
|------|------|---------------|-----------|
| `backend-main.md` | Backend entry & shared | 5 | 🔵 8 URLs/tokens hardcoded in `llm.py`; 🟣 2 monolithic provider chain + MCP sync |
| `backend-db.md` | Data access (SQLite/Kuzu/LanceDB) | 2 | 🔴 5 dead functions; 🟣 3 module-level side effects + circular dep with config |
| `backend-evaluators.md` | Scoring & ranking | 5 | 🔵 17 hardcoded taxonomies/weights/thresholds; 🟣 5 lazy imports across modules |
| `backend-foundations.md` | Core utilities, schemas, models | 8 | 🟡 6 cryptic model names + FormReadBody orphan + validation reinvention |
| `backend-generators.md` | Output generation | 2 | 🔴 `_draft()` dead; 🔵 8 PDF/LLM prompt hardcodes; 🟡 7 thread-safety + sql unused |
| `backend-integrations.md` | External integrations | 9 | 🔵 15 hardcoded selectors/URLs/paths; 🟣 2 actuator state machine; 🟠 3 stale help guides |
| `backend-config.md` | Pydantic config layer | 10 | 🟣 `secrets.py` circular dep with `db.client`; 🟡 7 items (5 unused `Literal` imports) |
| `backend-routes.md` | FastAPI route handlers | 9 | 🔴 2 dead imports in misc.py; 🟣 7 private-name imports from services; 🔵 7 hardcodes |
| `backend-scrapers.md` | Job discovery agents | 5 | 🔴 4 dead code in scout.py; 🔵 16 hardcoded API URLs/limits/taxonomies; 🟡 9 duplications |
| `backend-services.md` | Business logic orchestration | 7 | 🔵 4 query templates/Anthropic model pinned; 🟣 2 circular import + private attr access |
| `backend-tests.md` | Backend test suite | 20 | 🟠 1 monolithic `RegressionTests` class; 🟡 2 suspect functions in api_contracts |
| `build-ci.md` | Build, CI/CD, deps | 7 | 🔵 2 no-upper-bound dep pins; 🟡 2 dead marker + script inconsistency |
| `frontend-components.md` | Reusable UI components | 11 | 🔴 `JobCard` + `StatCard` dead; 🔵 OnboardingWizard provider data hardcoded |
| `frontend-core.md` | Root React files & types | 5 | 🟡 3 (macOS-specific copy, silent error swallow, narrow event typing) |
| `frontend-hooks.md` | Custom React hooks | 5 | 🔵 8 hardcoded intervals/URLs/thresholds; 🟡 5 retry/error handling gaps |
| `frontend-settings.md` | Settings panels | 5 | 🔵 7 provider/source/preset data baked in; 🟠 2 all-string typing + no validation |
| `frontend-views.md` | Workspace view pages | 9 | 🔴 `port` prop dead in ApplyJobView; 🔵 3 magic numbers/DOM patterns; 🟡 7 suspect |
| `tauri.md` | Tauri desktop shell | 5 | 🔴 `notify_high_score_lead` misnamed; 🟠 3 missing permissions/targets; 🔵 3 hardcodes |

## Cross-unit DEAD resolution

Before consolidation, these 11 items were verified across all map files:

| # | Item | Original status | Resolution |
|---|------|----------------|------------|
| 1 | `ContextFormatter` in `logger.py` | 🔴 DEAD (backend-main) | 🟡 SUSPECT — imported and tested by `test_log_context.py`; not dead, just production code doesn't wire it |
| 2 | `JobCard` in `JobCard.tsx` | 🔴 DEAD (frontend-components) | CONFIRMED DEAD — zero imports across codebase; only `PipelineJobCard` imported |
| 3 | `StatCard` in `Topbar.tsx` | 🔴 DEAD (frontend-components) | CONFIRMED DEAD — zero imports; typed `any`, likely leftover |
| 4 | `get_all_freelance_leads` | 🔴 DEAD (backend-db) | CONFIRMED DEAD — not imported by any route/service/agent |
| 5 | `get_discovered_freelance_leads` | 🔴 DEAD (backend-db) | CONFIRMED DEAD — not imported anywhere |
| 6 | `graph_available()` / `graph_error()` | 🔴 DEAD (backend-db) | CONFIRMED DEAD — not imported by any backend module |
| 7 | `_draft()` in `generator.py` | 🔴 DEAD (backend-generators) | CONFIRMED DEAD — superseded by `_draft_package()`, never called |
| 8 | `_ensure_scheme` first def in `scout.py` | 🔴 DEAD (backend-scrapers) | CONFIRMED DEAD — immediately overwritten at line 386 |
| 9 | `_SYSTEM_PROMPT` first def in `evaluator.py` | 🔴 DEAD (backend-evaluators) | CONFIRMED DEAD — immediately overwritten at line 84 |
| 10 | `classify_kind` second branch in `lead_intel.py` | 🔴 DEAD (backend-evaluators) | ⚪ INCOMPLETE — this is a **BUG** (always returns "job", unreachable code), not dead |
| 11 | `HTTPException` / `JSONResponse` in `misc.py` | 🔴 DEAD (backend-routes) | CONFIRMED DEAD — unused imports |
| 12 | `import sys` in `scout.py:4` | 🔴 DEAD (backend-scrapers) | CONFIRMED DEAD — unused import |
| 13 | `import sys` in `actuator.py:5` | 🔴 DEAD (backend-integrations) | CONFIRMED DEAD — unused import |

**Net adjustment:** 🔴 20 → 18 (−2), 🟡 89 → 90 (+1), ⚪ 4 → 5 (+1)

---

## Priority groupings

### P0 — DEAD (safe to delete)

After cross-unit resolution, 18 confirmed-dead items:

| Flag | Item | File:Line | Reason |
|------|------|-----------|--------|
| 🔴 | `graph_available()` | `db/client.py:134` | Defined but never imported or called |
| 🔴 | `graph_error()` | `db/client.py:138` | Defined but never imported or called |
| 🔴 | `get_all_freelance_leads()` | `db/client.py:523` | Never imported outside this file |
| 🔴 | `get_discovered_freelance_leads()` | `db/client.py:1114` | Never imported outside this file |
| 🔴 | `_b` first assignment | `db/client.py:41` | Immediately overwritten on line 84 |
| 🔴 | `_SYSTEM_PROMPT` 1st definition | `evaluator.py:34-82` | Immediately overwritten by 2nd definition |
| 🔴 | `_draft()` | `generator.py:661` | Never called; superseded by `_draft_package()` |
| 🔴 | `import sys` | `actuator.py:5` | Unused import |
| 🔴 | `HTTPException` import | `misc.py:9` | Imported but never used in file |
| 🔴 | `JSONResponse` import | `misc.py:10` | Imported but never used in file |
| 🔴 | `import sys` | `scout.py:4` | Unused import |
| 🔴 | `_ensure_scheme` first def | `scout.py:374` | Immediately redefined at line 386 |
| 🔴 | `_source_cap()` | `scout.py:431` | Never called within the unit |
| 🔴 | `_is_ats_target()` | `scout.py:531` | Defined but never called |
| 🔴 | `JobCard` | `JobCard.tsx:7` | Never imported anywhere; only `PipelineJobCard` is used |
| 🔴 | `StatCard` | `Topbar.tsx:44` | Never imported; typed `any`, likely leftover |
| 🔴 | `port` prop | `ApplyJobView.tsx:7` | Declared in props but never used |
| 🔴 | `notify_high_score_lead` | `lib.rs:47` | "high score" is game terminology, irrelevant to hiring domain |

### P1 — COUPLED + HARDCODED + INCOMPLETE (high impact)

136 items across the codebase. Representative highlights:

| Flag | Item | File:Line | Reason |
|------|------|-----------|--------|
| 🟣 | `Module-level import chain` | `db/client.py:28+131+242` | `from config import settings` creates circular dep (config → db.client → config via secrets.py) |
| 🟣 | `_fire_blocker` circular import | `ghost.py:243` | Imports from `main` to avoid `generator`→`ghost` cycle |
| 🟣 | `free_scout.py` imports `_`-prefixed from `scout.py` | `free_scout.py:26` | Imports 5 private functions creating tight cross-module coupling |
| 🟣 | `help_chat` duplicate route | `misc.py:132` + `scan.py:112` | Both register `POST /api/v1/help/chat`; scan's shadows misc's |
| 🟣 | 6 private-name imports in `settings.py` | `settings.py:12-14` | Imports `_ghost_tick`, `_sensitive`, `_probe_provider_key`, `_log_sensitive_deprecation` |
| 🟣 | `_evaluator_llm_requested` lazy-imports `db.client` | `evaluator.py:193` | Runtime dependency from agent layer to DB layer |
| 🟣 | `_CM.broadcast` lazy-imports `db.client` | `core/ws_manager.py:72` | Runtime dependency in connection manager broadcast path |
| 🟣 | `_semantic_criterion` lazy-imports `semantic.py` | `scoring_engine.py:1037` | Engine imports agent module inside function body |
| 🟣 | `embed_jd` imports `agents.ingestor._emb` | `semantic.py:33` | Imports private `_emb` from another agent module |
| 🟣 | `from db.client import get_setting` | `secrets.py:6` | Config module depends on db.client; creates circular-ish dependency |
| 🔵 | 84-entry `TECH_TAXONOMY` | `scoring_engine.py:87-171` | Full tech taxonomy baked into Python module |
| 🔵 | 17 hardcoded LLM provider URLs/tokens | `llm.py:90-316` | URLs duplicated with config module (`config/llm.py`) |
| 🔵 | Rubric weights in `score_job_lead` | `scoring_engine.py:1073-1089` | Score weights for all 6 criteria baked in |
| 🔵 | All Python dep pins `>=` only | `pyproject.toml:9-28` | No upper bounds on 20 runtime deps — risk of breakage |
| 🔵 | All hook intervals hardcoded | `useWS.ts:6-100`, `useLeads.ts:86` | Sidecar retries (30), reconnect (3s), polling (5s/60s/10s) not configurable |
| 🔵 | `PROVIDERS` / `MODEL_HINTS` baked in | `shared.tsx:54-93` | 17 providers and model lists hardcoded in source |
| 🔵 | ATS API endpoint URLs | `free_scout.py:260-344` | 4 ATS board API URLs baked in (Greenhouse, Lever, Ashby, Workable) |
| 🔵 | `_india_clause` in query gen | `query_gen.py:142` | India-specific location appending baked into general query gen |
| 🔵 | India presets + market focus buttons | `DiscoverySettings.tsx:259-279` | India-specific quick-add buttons and market toggle baked in |
| 🔵 | WebSocket URL structure | `useWS.ts:28` | `ws://127.0.0.1:${p}/ws?token=...` assumes backend routing |
| 🔵 | macOS signing identity | `tauri.conf.json:64` | `"-"` = ad-hoc; not distributable without real cert |
| 🔵 | 2.0s heartbeat timeout | `ws.py:49` | Should be configurable |
| ⚪ | `classify_kind` second branch | `lead_intel.py:143` | **Bug:** always returns "job", non-job leads never classified |
| ⚪ | Duplicate `resume_version` migration | `db/client.py:228,234-238` | Both blocks attempt to add `resume_version` column |
| ⚪ | `refresh_profile_snapshot` called twice in `update_candidate` | `db/client.py:1574,1594` | First call is unnecessary |
| ⚪ | Ghost mode interval hardcoded | `settings.py:95` | `hours=6` should read from `config.app.ghost_mode.interval_hours` |
| ⚪ | `Cfg` all-string typing | `shared.tsx:4` | 77 keys all `string` — numeric and boolean fields not type-safe |

### P2 — STALE + SUSPECT (needs review)

97 items. Representative highlights:

| Flag | Item | File:Line | Reason |
|------|------|-----------|--------|
| 🟠 | `RegressionTests` monolithic class | `test_regressions.py:62` | 435 lines, 35+ unrelated tests — should be split |
| 🟠 | `_PROVIDER_GUIDE` model list | `help_agent.py:177-194` | Model names will go stale as providers release new models |
| 🟠 | India market section in `_USER_GUIDE` | `help_agent.py:75, 209` | India market hardcoded in global help text |
| 🟠 | `.deb` removed from release pipeline | `release.yml:371-374` | Linux release now AppImage-only |
| 🟠 | Backward-compat re-exports | `main.py:183-189` | "Remove after test imports updated" |
| 🟠 | `Cfg` no frontend validation | `shared.tsx:4` | No min/max, required-key, or provider/key consistency validation |
| 🟡 | `ContextFormatter` (test-only) | `logger.py:50` | Only imported by `test_log_context.py`; production code never wires it |
| 🟡 | `_parse_date` duplicate implementations | `scout.py:71` vs `quality_gate.py:77` | Two different date parsers for same purpose |
| 🟡 | `_lead_text` duplicate | `scout.py:153` vs `quality_gate.py:62` | Nearly identical with different field sets |
| 🟡 | `LAST_ERRORS`/`LAST_USAGE` module state | All 3 scout run files | Mutable module-level state accessed via `getattr` — fragile |
| 🟡 | Thread-safety race on `_st` | `ingestor.py:23-45` | Module-level mutable `_st` accessed without lock |
| 🟡 | `enrich()` no callers found | `log_context.py:87` | Defined with clear purpose but no known callers |
| 🟡 | `kind_filter` parameter overwritten | `scout.py:47,109` | Both signal scan functions immediately overwrite to `"job"` |
| 🟡 | `portfolio_ingestor.py` import bypass | `portfolio_ingestor.py:80-81` | Uses private `llm._resolve` instead of public `resolve_config` |
| 🟡 | `pipelineRunning` 3s timeout race | `ApprovalDrawer.tsx:163` | Pipeline may finish before/after hardcoded timeout |
| 🟡 | Silent error swallow | `useDueFollowups.ts:11` | `.catch(() => {})` on followup fetch |
| 🟡 | `pentagonGraph` typed `any[]` | `GraphView.tsx:4` | No type safety on visualization data |
| 🟡 | No `SIGKILL` fallback on Unix | `lib.rs:110-113` | `kill_process_tree` sends only TERM; stubborn children survive |
| 🟡 | Post-startup stdout dropped | `lib.rs:355-371` | After startup, sidecar stdout silently consumed and discarded |

### P3 — CLEAN (no action needed)

Summary: 72 items flagged clean across all maps.

Notable clean modules and functions:
- `log_context.py` — entire module (single-responsibility, well-typed, correct contextvar usage)
- `mcp_server.py` — `_handle` dispatch (clean JSON-RPC 2.0, good error wrapping)
- `get_logger()` factory — once-per-name, env-driven config, filter + file handler
- `contact_lookup.py` — well-factored, config-driven, clean pipeline
- `selectors.py` — clean fallback chain, never raises
- `browser_runtime.py` — well-structured multi-tier discovery
- `github_ingestor.py` — clean async design, typed output
- `linkedin_parser.py` — deterministic, no external deps
- `fakes.py` — clean abstraction with `use_real_sqlite` toggle
- `test_websocket.py` — best-practice deterministic concurrency testing
- `test_graph_failures.py` — excellent structured failure characterization

---

## Flow index

| Flow | Entry point | Key participants |
|------|-------------|------------------|
| **Scan** | `POST /api/v1/scan` → `routes/scan.py:scan()` | `services/scanner.ScanManager` → `agents/scout.run()` | `agents/x_scout.run()` | `agents/free_scout.run()` | `agents/query_gen.generate()` | `agents/evaluator.score()` | `db/client.*` | `core/ws_manager.cm` | 🟣 scan imports `_`-prefixed from services; 🔵 multiple hardcoded API URLs/limits |
| **Ghost mode** | `APScheduler` tick → `_ghost_tick()` | `services/ghost.GhostService` (7 phases) → `services/scout.*` → `services/scanner.scan_manager` | `services/job_targets.*` | `agents/evaluator.score()` | `agents/generator.run_package()` | `db/client.*` | 🟣 `_fire_blocker` circular import; 🟣 `scan_manager._ghost_lock` direct access |
| **Ingest** | `POST /api/v1/ingest` → `routes/ingest.py:ingest()` | `agents/ingestor.ingest()` → `agents/ingestor.run()` | `llm.call_llm()` | `db/client.*` (Kuzu + LanceDB) | `core/ws_manager.cm` | 🟡 thread-safety race on `_st`; 🔵 model name `all-MiniLM-L6-v2` hardcoded |
| **Application fire** | `POST /api/v1/fire/{job_id}` → `routes/actions.py:fire()` | `services/generator._actuate()` → `services/generator._fire_blocker()` | `agents/actuator.run()` | `agents/generator.run_package()` | `agents/contact_lookup.run()` | `db/client.*` | 🟣 `_fire_blocker` imported from `main.py`; 🔵 _DOM_MAP selectors/URLs hardcoded |
| **Settings** | `GET/POST /api/v1/settings` → `routes/settings.py:*` | `services.job_targets.*` | `services.provider_probe.*` | `services.ghost._ghost_tick` | `config.*` | `db/client.*` | 🟣 6 private-name imports; 🔵 provider list inline; ⚪ ghost interval hardcoded |
| **WebSocket** | `ws://.../ws?token=` → `routes/ws.py:ws_endpoint()` | `core/ws_manager._CM` (add/remove/broadcast) | `core.config_constants.*` (token, uptime) | All agent broadcasts via `cm.broadcast()` | 🔵 2.0s heartbeat baked in; 🟡 WS URL structure assumed by frontend hooks |
| **Reevaluation** | `POST /api/v1/leads/reevaluate` → `routes/scan.py:reevaluate_jobs()` | `services/scanner.ScanManager` → `services.scanner._run_reevaluate_jobs()` | `agents/evaluator.score()` | `db/client.*` | `core/ws_manager.cm` | 🟡 `_run_scan` duplicates `_job_eval_document` logic inline |
| **Help/chat** | `POST /api/v1/help/chat` → `routes/misc.py:help_chat()` (shadowed by `scan.py:help_chat()`) | `agents/help_agent.answer()` → `llm.call_raw()` | `llm.resolve_config()` | 🟣 duplicate route (misc + scan register same path); 🟠 _USER_GUIDE India model lists stale |
