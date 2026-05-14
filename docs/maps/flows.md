# Codebase Flows — JustHireMe

> 16 documented flows synthesized from 18 unit maps in `docs/maps/`.
> Each flow traces entry → participants → exit points and flags known issues.

---

## 1. Scan Flow

**Trigger:** `POST /api/v1/scan`
**Purpose:** Full pipeline: discover job leads from all configured targets, score them, save them.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/scan.py:scan()` | Calls `scanner.scan_manager.start_scan()` |
| 2 | State machine | `services/scanner.py:ScanManager.start_scan()` | Acquires lock, spawns `_run_scan_task()` |
| 3 | Scan pipeline | `services/scanner.py:_run_scan()` | Resolves targets, runs X scan, free-source scan, query gen, scout, LLM eval |
| 4a | X signal scan | `services/scout.py:_run_x_signal_scan()` | Dispatches `agents.x_scout.run()` with resolved queries |
| 4b | Free-source scan | `services/scout.py:_run_free_source_scan()` | Dispatches `agents.free_scout.run()` with profile-tailored targets |
| 4c | Query generator | `agents/query_gen.py:generate()` | LLM generates `site:` search queries from profile |
| 5 | Scout runner | `agents/scout.py:run()` | Orchestrates scraping across targets (RSS, HN, APIs, Playwright crawl), LLM extraction, dedup, quality gate, save |
| 6 | Quality gate | `agents/quality_gate.py:evaluate_lead_quality()` | Deterministic freshness/seniority/red-flag check per lead |
| 7 | LLM evaluation | `agents/evaluator.py:score()` | Scores each lead 0-100 against candidate profile; LLM-led or deterministic |
| 8 | DB persistence | `db/client:save_lead()`, `update_lead_score()` | SQLite INSERT/UPDATE; LanceDB index; Kuzu graph entities |
| 9 | Broadcast | `core/ws_manager.py:_CM.broadcast()` | Sends `{type, job_id, score, status, event}` to all WS clients |

### Exit points

- **Success:** Leads saved to DB; `scan-done` WS event broadcast; scan_manager stops
- **Error:** Lock conflict → `HTTPException(409)`; per-source errors collected in `LAST_ERRORS`; individual lead failures logged
- **Cancellation:** `POST /api/v1/scan/stop` → `scan_manager.stop_scan()` sets stop event, task exits at next yield point

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | `_MAX_AGE_DAYS = 7` freshness window | `scout.py:20` |
| 🔵 HARDCODED | ATS API URLs (Greenhouse, Lever, Ashby, Workable) | `free_scout.py:260-344` |
| 🔵 HARDCODED | HN Algolia API URLs + 35-day search window | `scout.py:870-892` |
| 🔵 HARDCODED | X API base URL + default queries | `x_scout.py:19,23-27` |
| 🔵 HARDCODED | Seniority term taxonomies | `scout.py:35-64` |
| 🔵 HARDCODED | Quality gate red-flag / seniority lists | `quality_gate.py:22-59` |
| 🔵 HARDCODED | Google URL template `tbs=qdr:w` | `scout.py` |
| 🔵 HARDCODED | Multiple `timeout=30` in HTTP clients | `free_scout.py`, `scout.py` |
| 🟣 COUPLED | `free_scout.py` imports 5 private functions from `scout.py` | `free_scout.py:26` |
| 🟣 COUPLED | `x_scout.py` lazy-imports `scout.classify_job_seniority` | `x_scout.py:345` |
| 🟡 SUSPECT | Duplicate date parsers (`scout.py` vs `quality_gate.py`) | Both files |
| 🟡 SUSPECT | `scanner.py:_run_scan()` duplicates `_job_eval_document` inline | `scanner.py:340-346` |
| 🟡 SUSPECT | `kind_filter` param overwritten to `"job"` unconditionally | `scout.py:47,109` |

---

## 2. Ghost Mode Flow

**Trigger:** APScheduler tick (configured interval, default 6h)
**Purpose:** Automated background scan-evaluate-generate-apply cycle with zero user interaction.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | Scheduler start | `main.py:lifespan` | `_sched.add_job(_ghost_tick, "interval", hours=6)` |
| 2 | Tick function | `services/ghost.py:_ghost_tick()` | Try-acquire `scan_manager._ghost_lock`, run `GhostService.run()` |
| 3 | Phase 1: Preflight | `GhostService._phase_preflight()` | Check ghost enabled, resolve targets, has X token, free sources enabled |
| 4 | Phase 2: X scan | `GhostService._phase_x_scan()` | Calls `services/scout._run_x_signal_scan()` |
| 5 | Phase 3: Free scan | `GhostService._phase_free_scan()` | Calls `services/scout._run_free_source_scan()` |
| 6 | Phase 4: Scout | `GhostService._phase_scout()` | Generates queries via `query_gen.generate()`, runs `scout.run()` |
| 7 | Phase 5: Eval | `GhostService._phase_eval()` | Scores discovered leads via `evaluator.score()`, filters ≥85 |
| 8 | Phase 6: Gen | `GhostService._phase_gen()` | Runs `generator.run_package()` for approved leads |
| 9 | Phase 7: Apply | `GhostService._phase_apply()` | If auto-apply enabled, runs `actuator.run()` via `_fire_blocker` |
| 10 | Broadcast | `core/ws_manager.py:_CM.broadcast()` | Each phase broadcasts progress events |

### Exit points

- **Success:** All 7 phases complete; lock released
- **Skip:** Preflight returns `None` if ghost disabled or no targets → phases skipped
- **Phase failure:** Individual phases catch errors and log; subsequent phases execute independently
- **Lock contention:** If ghost lock held (e.g. manual scan running), tick exits immediately

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | Ghost interval `hours=6` | `main.py:112` — should read `settings.app.ghost_mode.interval_hours` |
| 🟣 COUPLED | `scan_manager._ghost_lock` accessed directly (private attr) | `ghost.py:268` |
| 🟣 COUPLED | `_fire_blocker` imported from `main.py` (circular workaround) | `ghost.py:243` |

---

## 3. Ingest Flow

**Trigger:** `POST /api/v1/ingest`
**Purpose:** Parse candidate profile text/PDF → structured data → Kuzu graph + LanceDB vectors + SQLite snapshot.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/ingest.py:ingest()` | Accepts raw text or PDF upload |
| 2 | Ingest agent | `agents/ingestor.py:ingest()` | Calls `_pdf()` if PDF, then `run()` |
| 3 | Extraction | `agents/ingestor.py:run()` | LLM extraction first (via `call_llm`), fallback to `_parse_local()` |
| 4 | Graph write | `agents/ingestor.py:_graph(p)` | Creates Kuzu nodes (Candidate, Skill, Experience, Project, Education, Certification, Achievement) and relationships |
| 5 | Vector write | `agents/ingestor.py:_vectors(p)` | Embeds skills + projects via `_emb()`, writes to LanceDB |
| 6 | Snapshot refresh | `db/client:refresh_profile_snapshot()` | Re-reads Kuzu graph into SQLite settings snapshot |
| 7 | Broadcast | `core/ws_manager.py:_CM.broadcast()` | Sends ingest-complete event |

### Exit points

- **Success:** Profile written to all 3 stores; WS event broadcast
- **Error:** LLM extraction failure → fallback to local parser; PDF read failure → error response; `refresh_profile_snapshot` called even on partial success

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | SentenceTransformer model `"all-MiniLM-L6-v2"` | `ingestor.py:32` |
| 🟡 SUSPECT | Thread-safety race on `_st` in `_emb()` | `ingestor.py:23-45` |
| 🟡 SUSPECT | Kuzu connections not explicitly closed | `ingestor.py:66-67` |
| 🟣 COUPLED | `_emb()` imported by `db/client.py` and `agents/semantic.py` | Reverse dependency |

---

## 4. Application Fire Flow

**Trigger:** `POST /api/v1/fire/{job_id}`
**Purpose:** Submit a tailored application for a lead via browser automation.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/actions.py:fire()` | Checks blockers via `_fire_blocker()`, schedules `_actuate()` in background |
| 2 | Fire blocker | `services/generator.py:_fire_blocker()` | Validates lead exists, not applied, has URL, assets exist |
| 3 | Actuation | `services/generator.py:_actuate()` | Fetches `get_lead_for_fire()`, calls `agents.actuator.run()` |
| 4 | Browser automation | `agents/actuator.py:run()` | Launches Playwright via `launch_chromium()`, fills DOM fields, falls back to vision-based fill, finds submit button, optionally submits |
| 5 | DB update | `db/client:mark_applied()` | Sets lead status to `"applied"`, records event |
| 6 | Broadcast | `core/ws_manager.py:_CM.broadcast()` | Sends fire-complete event |

### Exit points

- **Success:** Lead marked `"applied"`, WS event broadcast
- **Blocker failure:** `_fire_blocker` returns error tuple → route returns error response, no actuation
- **Browser error:** Actuator throws → caught in BackgroundTasks, logged, WS error broadcast
- **Preview mode:** `preview_apply()` runs actuator with `dry_run=True`, no submission, no DB write

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | `_DOM_MAP` selectors (18 CSS pairs) | `actuator.py:144-162` |
| 🔵 HARDCODED | `_FILL_DELAY = 500`, submit selectors | `actuator.py:164,346-353` |
| 🔵 HARDCODED | Provider base URLs (Groq, NVIDIA, Ollama) | `actuator.py:268-273` |
| 🟣 COUPLED | `asyncio.run()` in `actuator.run()` may conflict with running loop | `actuator.py:454` |
| 🟡 SUSPECT | Cover letter silently truncated to 1500 chars in vision context | `actuator.py:330` |

---

## 5. Settings Flow

**Trigger:** `GET /api/v1/settings` | `POST /api/v1/settings`
**Purpose:** Read/write all user configuration values, validate API keys, trigger ghost mode scheduling.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route (GET) | `routes/settings.py:get_cfg()` | Reads all settings via `get_settings()`, masks sensitive keys via `_sensitive()` |
| 2 | HTTP route (POST) | `routes/settings.py:save_cfg()` | Merges with existing (preserving masked values), calls `save_settings()`, probes key deprecation, restarts ghost scheduler if `ghost_mode=true` |
| 3 | Key validation | `routes/settings.py:validate_settings()` | Probes each configured provider via `_probe_provider_key()` |
| 4 | Provider probe | `services/provider_probe.py:_probe_provider_key()` | Sends cheapest-possible request to each provider, returns `{status, latency_ms}` |
| 5 | DB persistence | `db/client:get_settings()` / `save_settings()` | SQLite key-value store (all values stored as `str`) |

### Exit points

- **Success (GET):** `dict` with masked secrets returned
- **Success (POST):** `{"ok": true}`, settings saved, ghost mode started if enabled
- **Validation error:** Bad key → `_probe_provider_key` returns error status; log deprecation for SQLite-stored secrets

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | Provider list in `validate_settings` | `settings.py:50` — duplicates `llm.py` |
| 🔵 HARDCODED | Anthropic model `"claude-haiku-4-5-20251001"` in probe | `provider_probe.py:46` |
| 🔵 HARDCODED | Probe timeout `5.0s` | `provider_probe.py:35` |
| ⚪ INCOMPLETE | Ghost interval `hours=6` hardcoded, not from config | `settings.py:95` |
| 🟣 COUPLED | 6 imports of private (`_`) names from services | `settings.py:12-14` |
| 🟣 COUPLED | Settings CRUD in SQLite duplicates Pydantic config layer | `backend-db map` |

---

## 6. WebSocket Flow

**Trigger:** `ws://<host>/ws?token=<api_token>`
**Purpose:** Real-time event streaming from backend agents to frontend, plus uptime heartbeat.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | WS route | `routes/ws.py:ws_endpoint()` | Calls `_require_ws_token()`, accepts connection |
| 2 | Auth guard | `routes/ws.py:_require_ws_token()` | Checks query param or Bearer header against `_API_TOKEN` |
| 3 | Connection manager | `core/ws_manager.py:_CM.add()` | Registers WebSocket in thread-safe set |
| 4 | Heartbeat loop | `routes/ws.py:ws_endpoint()` | Sends uptime/timestamp JSON every 2s |
| 5 | Agent broadcast | `core/ws_manager.py:_CM.broadcast()` | Called by all agents: sends JSON to all connected clients, dead connections removed |
| 6 | Event persistence | `core/ws_manager.py:_CM.broadcast()` | Calls `db/client:record_event()` via `asyncio.to_thread` |
| 7 | Disconnect | `routes/ws.py:ws_endpoint()` | `cm.remove()` on disconnect or error |

### Exit points

- **Normal:** Client disconnects; `cm.remove()` called in `finally` block
- **Auth failure:** WebSocket closed with 4001 reason
- **Heartbeat timeout:** Client disconnected by server on receive timeout

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | Heartbeat interval 2.0s | `ws.py:49` |
| 🟣 COUPLED | `_CM.broadcast()` lazy-imports `db.client.record_event` | `ws_manager.py:72` |
| 🟡 SUSPECT | Post-startup sidecar stdout silently dropped | `tauri:lib.rs:355-371` |

---

## 7. Reevaluation Flow

**Trigger:** `POST /api/v1/leads/reevaluate`
**Purpose:** Re-score all existing discovered leads against the current profile.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/scan.py:reevaluate_jobs()` | Calls `scanner.scan_manager.start_reevaluate()` |
| 2 | State machine | `services/scanner.py:ScanManager.start_reevaluate()` | Acquires lock, spawns `_run_reevaluate_jobs_task()` |
| 3 | Reevaluation loop | `services/scanner.py:_run_reevaluate_jobs()` | Iterates `get_job_leads_for_evaluation()`, preserves terminal statuses via `_should_preserve_job_status()` |
| 4 | Scoring | `agents/evaluator.py:score()` | Scores each lead 0-100 |
| 5 | DB update | `db/client:update_lead_score()` | Updates score, reason, match_points, gaps |
| 6 | Broadcast | `core/ws_manager.py:_CM.broadcast()` | Per-lead score update events + `reevaluate-done` at end |

### Exit points

- **Success:** All leads re-scored; `reevaluate-done` WS event
- **Stop:** `POST /api/v1/leads/reevaluate/stop` → sets stop event, loop exits at next iteration check
- **Lock conflict:** Double start → `HTTPException(409)`

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | Score threshold `76` for "matched"/"tailoring" | `db/client:378,380` |
| 🔵 HARDCODED | Status lock set baked in | `scanner.py` `_REEVALUATION_STATUS_LOCKS` |
| 🟡 SUSPECT | `_should_preserve_job_status` logic duplicates inline in `_run_scan` | `scanner.py` |

---

## 8. Help/Chat Flow

**Trigger:** `POST /api/v1/help/chat`
**Purpose:** Answer user questions about JustHireMe usage — deterministic or LLM-powered.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/misc.py:help_chat()` | Receives `HelpChatBody` with question + history |
| 2 | Route collision | `routes/scan.py:help_chat()` | **Duplicate route** — scan.py shadows misc.py's handler due to registration order |
| 3 | Help agent | `agents/help_agent.py:answer()` | Classifies topic via `_topic()`, either returns `_fallback()` or calls LLM via `call_raw()` |
| 4 | Fallback | `agents/help_agent.py:_fallback()` | Deterministic answer for providers/sources/customize/workflow/install topics |
| 5 | LLM path | `agents/help_agent.py:answer()` | Calls `call_raw()` with focused knowledge context via `_focused_knowledge()` |
| 6 | Response | Returns `{"answer": str}` | |

### Exit points

- **Success:** Answer string returned (deterministic or LLM-generated)
- **LLM failure:** Falls back to deterministic `_fallback()` for the classified topic
- **History limit:** Last 8 messages, 1000 chars each passed to LLM

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🟣 COUPLED | Duplicate `help_chat` route (scan.py shadows misc.py) | `misc.py:132` + `scan.py:112` |
| 🟠 STALE | `_USER_GUIDE` India market section baked in | `help_agent.py:75,209` |
| 🟠 STALE | `_PROVIDER_GUIDE` model names will go stale | `help_agent.py:177-194` |
| 🔵 HARDCODED | Model names in `_fallback` (grok-4, kimi-k2-turbo-preview, etc.) | `help_agent.py:362-370` |

---

## 9. Job Targets CRUD Flow

**Trigger:** `GET|PUT|DELETE /api/v1/settings/job-targets`
**Purpose:** Manage user-configured job board URLs and blocked marker keywords.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route (GET) | `routes/settings.py:get_job_targets_endpoint()` | Returns current targets + blocked markers |
| 2 | HTTP route (PUT) | `routes/settings.py:update_job_targets()` | Validates via `validate_job_targets()` + `validate_blocked_markers()`, saves via `save_job_targets()` |
| 3 | HTTP route (DELETE) | `routes/settings.py:clear_job_targets()` | Saves empty lists via `save_job_targets()` |
| 4 | Validation | `services/job_targets.py:validate_job_targets()` | Checks format (URL, `site:`, `github:`, `hn:`, `reddit:`, named sources), limits 100 entries, 500 chars each |
| 5 | Persistence | `services/job_targets.py:save_job_targets()` | JSON-serializes and stores via `db.client:save_settings()` |

### Exit points

- **Success:** Targets saved/returned/cleared
- **Validation error:** Bad format → list of error strings returned; `HTTPException(422)` per entry
- **Empty state:** No targets configured → empty list (scan uses defaults)

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | Validation limits (100 entries, 500 chars) | `job_targets.py:213-225` |
| 🟢 CLEAN | Well-scoped, tested via `test_regressions.py` | `job_targets.py` |

---

## 10. Health Check Flow

**Trigger:** `GET /health`
**Purpose:** Lightweight health check — the only endpoint exempt from bearer token auth.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/misc.py:health()` | No auth middleware applied (exempted in `main.py:162`) |
| 2 | Browser probe | `checks chromium_executable()` | Calls `browser_runtime.chromium_executable()` for binary path |
| 3 | DB probe | `checks get_settings()` | Reads one row from SQLite settings table |
| 4 | Connection probe | `checks get_sql_connection()` | Opens SQLite connection |
| 5 | Provider info | `_configured_api_providers()` | Lists providers with configured keys |
| 6 | Response | Returns `HealthResponse` | Includes uptime, timestamp, log level, dependency status dict |

### Exit points

- **Success:** Full health response; DB/browser/providers status reflected in payload
- **Degraded:** DB fail → `get_settings` fails inside; the catch in `health()` includes failure in response
- **Auth exemption:** Token middleware skips `/health` path

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🟢 CLEAN | Well-scoped, single-responsibility | `routes/misc.py:385` |
| 🟡 SUSPECT | `HTTPException` and `JSONResponse` unused imports in `misc.py` | `misc.py:9-10` |

---

## 11. MCP Flow

**Trigger:** stdin JSON-RPC 2.0 (stdio server)
**Purpose:** Expose JustHireMe scoring/quality/lead-intel tools to external AI assistants via Model Context Protocol.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | stdin read loop | `mcp_server.py:main()` | Reads JSON-RPC requests line by line from stdin |
| 2 | Dispatch | `mcp_server.py:_handle()` | Routes to initialize, tools/list, or tools/call |
| 3 | Tool: score_job_fit | `mcp_server.py:_score_job_fit()` | Delegates to `agents.evaluator.score()` |
| 4 | Tool: evaluate_lead_quality | `mcp_server.py:_evaluate_lead()` | Delegates to `agents.quality_gate.evaluate_lead_quality()` |
| 5 | Tool: extract_lead_intel | `mcp_server.py:_extract_lead_intel()` | Delegates to 6 `agents.lead_intel.*` functions |
| 6 | Response | `stdout` write | JSON-RPC response with `{jsonrpc, id, result}` or `{jsonrpc, id, error}` |

### Exit points

- **Success:** Tool result wrapped in MCP content response
- **Protocol error:** Unknown method → MCP protocol error (-32601); malformed request → parse error
- **Tool error:** Missing args/wrong types → tool-level error with `isError: true`

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | `min_quality=60`, `target_level="beginner"` defaults | `mcp_server.py:65-66` |
| 🟣 COUPLED | `TOOLS` / `TOOL_DEFINITIONS` manual sync (easy to drift) | `mcp_server.py:88-136` |
| 🟡 SUSPECT | No stdin read size limit — OOM risk on large payload | `mcp_server.py:173` |

---

## 12. Profile CRUD Flow

**Trigger:** `GET /api/v1/profile` | `PUT /api/v1/profile/candidate` | `POST /api/v1/profile/skill` | etc.
**Purpose:** Read/edit candidate identity graph — skills, experience, projects, education, certifications, achievements.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/profile.py:*_endpoint()` | Validates request body against Pydantic schema |
| 2 | Profile read | `db/client:get_profile()` | Tries Kuzu graph first → falls back to SQLite snapshot → empty |
| 3 | Skill CRUD | `db/client:add_skill()` / `update_skill()` / `delete_skill()` | Kuzu node CREATE/MERGE/SET/DETACH DELETE + LanceDB vector add/delete + SQLite snapshot refresh |
| 4 | Experience CRUD | `db/client:add_experience()` / `update_experience()` / `delete_experience()` | Kuzu nodes + relationships + snapshot refresh |
| 5 | Project CRUD | `db/client:add_project()` / `update_project()` / `delete_project()` | Kuzu nodes + relationships + LanceDB vector + snapshot refresh |
| 6 | Candidate edit | `db/client:update_candidate()` | Kuzu candidate node UPSERT + snapshot refresh |

### Exit points

- **Success:** Profile data returned (GET) or entity written (PUT/POST/DELETE)
- **Not found:** `get_profile()` returns empty profile with default fields
- **Error:** Validation error → 422; DB error → 500

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🟣 COUPLED | Kuzu CRUD functions create 2-3 new `Connection(db)` per call | `db/client` |
| 🟣 COUPLED | 3-DB pattern in single functions (Kuzu + LanceDB + SQLite) | `db/client` |
| 🟡 SUSPECT | `update_skill()`, `delete_skill()`, `update_experience()`, `delete_experience()`, `update_project()`, `delete_project()` — no production callers found | `db/client` |
| 🔵 HARDCODED | All Kuzu table names, property names, relationship types | `db/client` |
| 🟢 CLEAN | `get_profile()` fallback chain: graph → snapshot → empty | `db/client:1282` |

---

## 13. Lead CRUD Flow

**Trigger:** `GET /api/v1/leads` | `PUT /api/v1/leads/{id}/status` | `PUT /api/v1/leads/{id}/feedback` | `DELETE /api/v1/leads/{id}`
**Purpose:** List, update status/feedback, delete job leads.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route (GET) | `routes/leads.py:leads()` | Queries `get_all_leads()`, annotates via `_annotate_job_lead()`, filters by seniority |
| 2 | HTTP route (PUT status) | `routes/leads.py:update_status()` | Validates status via `StatusBody`, calls `update_lead_status()`, broadcasts |
| 3 | HTTP route (PUT feedback) | `routes/leads.py:update_feedback()` | Calls `save_lead_feedback()`, broadcasts |
| 4 | HTTP route (DELETE) | `routes/leads.py:delete_lead_endpoint()` | Calls `delete_lead()` |
| 5 | Manual lead create | `routes/leads.py:create_manual_lead()` | Calls `manual_lead_from_text()` → `save_lead()` → `rank_lead_by_feedback()` → broadcast |
| 6 | DB layer | `db/client:*` | SQLite CRUD with event logging |
| 7 | Broadcast | `core/ws_manager.py:_CM.broadcast()` | Status/feedback/deletion events |

### Exit points

- **Success:** Lead list, status update, or deletion confirmed
- **Not found:** 404 when `get_lead_by_id()` fails
- **Validation error:** Invalid status or feedback string → 422

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | Seniority level strings duplicated | `leads.py:38,91-94` |
| 🔵 HARDCODED | Feedback-to-status mappings baked in | `db/client:1029-1037` |
| 🔵 HARDCODED | `"job"` kind filter | `leads.py:285` |
| 🟡 SUSPECT | `save_lead` call with 20+ kwargs | `leads.py:288-314` |

---

## 14. Export Flow

**Trigger:** `GET /api/v1/leads/export.csv`
**Purpose:** Export all leads as a CSV file for external use.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/leads.py:export_leads_csv()` | Calls `get_all_leads()`, formats as CSV |
| 2 | DB read | `db/client:get_all_leads()` | Returns all leads ordered by created_at DESC |
| 3 | Response | `StreamingResponse` | `text/csv` content-type with attachment filename |

### Exit points

- **Success:** CSV streamed to client
- **Error:** DB read failure → 500

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🟢 CLEAN | Simple passthrough, no business logic in route | `routes/leads.py:265` |

---

## 15. Graph Stats Flow

**Trigger:** `GET /api/v1/graph`
**Purpose:** Retrieve aggregate Kuzu graph entity counts for dashboard visualization.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/misc.py:graph_stats()` | Calls `graph_counts()` |
| 2 | Kuzu query | `db/client:graph_counts()` | Runs 5 MATCH/RETURN count queries on Kuzu node tables |
| 3 | Response | `dict` | Returns `{candidate: N, skill: N, project: N, experience: N, joblead: N}` |

### Exit points

- **Success:** Counts returned; zeroes for empty graph
- **Error:** Kuzu unavailable → `conn.execute()` fails → error propagates; frontend shows zeroes

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🔵 HARDCODED | 5 node table names baked in | `db/client:graph_counts()` |
| 🟢 CLEAN | Simple query, no side effects | `routes/misc.py:399` |

---

## 16. Follow-up Flow

**Trigger:** `GET /api/v1/followups/due?limit=25`
**Purpose:** Retrieve leads with past-due follow-up dates.

### Step-by-step

| # | Participant | File:Function | Action |
|---|-------------|---------------|--------|
| 1 | HTTP route | `routes/leads.py:due_followups()` | Calls `get_due_followups(limit)` |
| 2 | DB query | `db/client:get_due_followups()` | Queries SQLite for leads where `followup_due <= now`, ordered by due date |
| 3 | Response | `list[dict]` | Lead dicts with followup metadata |

### Exit points

- **Success:** List of due leads (max `limit`)
- **Empty:** Empty list when no leads are past due

### Known flags

| Flag | Item | Source |
|------|------|--------|
| 🟢 CLEAN | Simple query, no business logic | `routes/leads.py:321` |
| 🟢 CLEAN | Default limit 25, parameterized | `routes/leads.py:321` |

---

## Cross-flow notes

### Shared infrastructure

All flows (except MCP and health) share these infrastructure modules:

| Module | Used by | Purpose |
|--------|---------|---------|
| `db/client` | All flows | SQLite + Kuzu + LanceDB data access |
| `core/ws_manager` | Flows 1-9, 12-13 | Real-time event broadcasting |
| `logger` / `log_context` | All flows | Structured logging with correlation IDs |
| `config` | All flows | Typed settings, secret resolution |
| `core/config_constants` | Flows 1-10, 12-16 | `_log`, `_sched`, `_API_TOKEN` singletons |

### Async boundaries

Flows that involve long-running work (scan, ghost, reevaluate, fire) use `asyncio.to_thread()` to offload CPU-bound/blocking agent code. The WebSocket broadcast loop runs in the main async event loop. The MCP server is fully synchronous (stdin/stdout).
