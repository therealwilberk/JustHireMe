# `main.py` Structure Report

**File:** `backend/main.py`
**Lines:** 2162
**Generated:** 2026-05-14

---

## 1. Imports

| Import | Type | Used in file |
|--------|------|-------------|
| `import asyncio` | stdlib | yes — `asyncio.Lock`, `asyncio.to_thread`, `asyncio.Event`, `asyncio.Task`, `asyncio.wait_for`, `asyncio.create_task`, `asyncio.gather` |
| `import csv` | stdlib | yes — `export_leads_csv` |
| `import io` | stdlib | yes — `export_leads_csv` |
| `import json` | stdlib | yes — `_CM.broadcast`, `ws_endpoint` |
| `import os` | stdlib | yes — `os.environ.get`, `os.listdir`, `os.path.join`, `os.path.isfile`, `os.path.dirname`, `os.unlink` |
| `import re` | stdlib | yes — `_terms_for_discovery`, `_versioned_assets` |
| `import secrets` | stdlib | yes — `_API_TOKEN = secrets.token_hex(32)` |
| `import shutil` | stdlib | yes — `ingest` (file upload to temp) |
| `import socket` | stdlib | yes — `_free_port()` |
| `import sys` | stdlib | yes — `sys.exit(1)`, `sys.stdout.write`, `sys.stdout.flush` |
| `import tempfile` | stdlib | yes — `ingest` (temp PDF) |
| `import time` | stdlib | yes — `_UP`, `health`, `ws_endpoint` |
| `from contextlib import asynccontextmanager` | stdlib | yes — `lifespan` |
| `from datetime import datetime, timezone` | stdlib | yes — `health`, `ws_endpoint` |
| `from typing import Literal` | stdlib | yes — `LeadStatus` type alias |
| `from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect, status` | 3rd-party | yes — all used across routes |
| `from fastapi.middleware.cors import CORSMiddleware` | 3rd-party | yes — CORS setup |
| `from fastapi.responses import JSONResponse, StreamingResponse` | 3rd-party | yes — `require_http_token`, `export_leads_csv`, `get_lead_pdf` |
| `from fastapi.security import HTTPBearer` | 3rd-party | yes — `_bearer` |
| `from apscheduler.schedulers.asyncio import AsyncIOScheduler` | 3rd-party | yes — `_sched` |
| `from pydantic import BaseModel, ConfigDict, Field, model_validator` | 3rd-party | yes — all Pydantic models |
| `from logger import get_logger` | local | yes — `_log` |
| `from config import settings` | local | yes — across 20+ locations |
| `from log_context import new_context, set_context, reset_context` | local | yes — middleware + background functions |

**Pattern:** Every route handler and most background functions use **lazy imports** inside the function body. This is the dominant pattern — ~30+ distinct `from db.client import ...` statements and ~10+ `from agents.*` imports scattered across function bodies. This avoids circular imports at module load time but makes the dependency graph invisible to static analysis.

---

## 2. Constants & Global Config

| Name | Type | Default | Used By |
|------|------|---------|---------|
| `_UP` | float | `time.monotonic()` | `health`, `ws_endpoint` |
| `_sched` | AsyncIOScheduler | `AsyncIOScheduler()` | `lifespan`, `save_cfg` |
| `_API_TOKEN` | str | `secrets.token_hex(32)` | `_require_ws_token`, `require_http_token`, `__main__` |
| `_LOCAL_ORIGIN_RE` | str | regex | `app.add_middleware(CORSMiddleware)` |
| `_bearer` | HTTPBearer | `HTTPBearer(auto_error=False)` | `require_http_token` |
| `_log` | Logger | `get_logger(__name__)` | everywhere |
| `cm` | `_CM` instance | `_CM()` | 25+ broadcast calls plus add/remove |
| `DEFAULT_JOB_TARGETS` | list[str] | 20 entries | `_job_targets` |
| `INDIA_JOB_TARGETS` | list[str] | 13 entries | `_job_targets` |
| `_BLOCKED_JOB_TARGET_MARKERS` | tuple[str] | 10 markers | `_job_targets` |
| `_scan_stop` | asyncio.Event | cleared | `scan`, `stop_scan`, `_run_scan` |
| `_scan_task` | asyncio.Task \| None | None | `scan`, `_run_scan_task` |
| `_reevaluate_stop` | asyncio.Event | cleared | `reevaluate_jobs`, `stop_reevaluate_jobs`, `_run_reevaluate_jobs` |
| `_reevaluate_task` | asyncio.Task \| None | None | `reevaluate_jobs`, `_run_reevaluate_jobs_task` |
| `_ghost_lock` | asyncio.Lock | unlocked | scan/reevaluate task wrappers + `_ghost_tick` |
| `_REEVALUATION_STATUS_LOCKS` | set[str] | 6 statuses | `_should_preserve_job_status` |

**Global mutable state (flags — these complicate refactor):**
- `cm` — module-level singleton holding live WebSocket connections; mutated by `add`, `remove`, `broadcast`; directly called from 25+ places across the file
- `_scan_task`, `_reevaluate_task` — mutable task references, reassigned by routes and cleared in task finalizers
- `_scan_stop`, `_reevaluate_stop` — mutable events, set/cleared across routes and background functions
- `_ghost_lock` — acquired/released across ghost, scan, and reevaluate paths
- `_sched` — APScheduler instance, mutated by `lifespan` and `save_cfg`
- `DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS` — mutable lists (should be tuples)

---

## 3. Class Map

### `StrictBody` (line 91)
- **Inherits from:** `BaseModel`
- **Purpose:** Base Pydantic model that rejects extra fields (`extra="forbid"`)
- **Instance vars:** none (inherits from BaseModel)
- **Subclasses (10):** `StatusBody`, `FeedbackBody`, `FollowupBody`, `ManualLeadBody`, `HelpMessage`, `HelpChatBody`, `TemplateBody`, `CandidateBody`, `SkillBody`, `ExperienceBody`, `ProjectBody`

### `SettingsBody` (line 159)
- **Inherits from:** `BaseModel` (directly — not StrictBody, since it uses `extra="allow"`)
- **Purpose:** Settings body that allows arbitrary extra keys with validation
- **Methods:**
  - `_validate_extra_settings(self)` — `@model_validator(mode="after")`, validates key format and value types

### `_CM` (line 178)
- **Inherits from:** none (plain class)
- **Purpose:** Async-safe WebSocket connection manager with broadcast and dead-connection cleanup
- **Instance vars:** `self._ws: list[WebSocket]`, `self._lock: asyncio.Lock`
- **Methods:**
  | Method | Line | Params | Returns | Calls | Side Effects |
  |--------|------|--------|---------|-------|--------------|
  | `__init__` | 179 | self | None | — | creates lock |
  | `add` | 183 | `ws: WebSocket` | None | `self._lock` | mutates `self._ws` |
  | `remove` | 187 | `ws: WebSocket` | None | `self._lock` | mutates `self._ws` |
  | `broadcast` | 191 | `msg: dict` | None | `self._lock`, `record_event`, `ws.send_text` | DB write + WS send + dead cleanup |

### Pydantic models defined inline for ingest endpoints (lines 1623-1684):
- `GithubIngestBody` (line 1623) — extends StrictBody
- `PortfolioIngestBody` (line 1629) — extends StrictBody
- `ProfileSkill` (line 1637) — extends BaseModel
- `ProfileExperience` (line 1642) — extends BaseModel
- `ProfileProject` (line 1649) — extends BaseModel
- `ProfileEntry` (line 1656) — extends BaseModel
- `ProfileIdentity` (line 1660) — extends BaseModel
- `ProfileCandidate` (line 1669) — extends BaseModel
- `ProfileImportBody` (line 1674) — extends BaseModel
- `FormReadBody` (line 1948) — extends StrictBody

---

## 4. Function Map

### Startup & Utility (lines 30-81)

| Function | Line | Params | Returns | Purpose | Calls | Side Effects |
|----------|------|--------|---------|---------|-------|--------------|
| `_free_port` | 30 | none | int | Bind ephemeral port | `socket` | port reserved until GC |
| `_validate_config_on_startup` | 43 | none | — | Validate config, exit on failure | `validate_all`, `_log.critical`, `sys.exit(1)` | can exit process |
| `_log_startup_secret_diagnostics` | 57 | none | None | Log which secrets are env-configured | `resolve_secret`, `_log.debug` | none |
| `_require_ws_token` | 72 | `ws: WebSocket` | bool (async) | Guard WS connections | `ws.query_params`, `ws.headers`, `ws.close` | closes WS on failure |

### Job Target Helpers (lines 257-418)

| Function | Line | Purpose |
|----------|------|---------|
| `_split_configured_targets` | 257 | Parse raw config text to lines |
| `_dedupe_targets` | 270 | Case-insensitive dedup |
| `_job_market_focus` | 281 | Normalize to "india" or "global" |
| `_is_hn_target` | 286 | Check if HN-related |
| `_job_targets` | 291 | Build filtered/deduplicated job target list (4 concerns in one) |
| `_desired_position` | 321 | Extract desired position from config |
| `_profile_for_discovery` | 329 | Merge profile + desired role |
| `_terms_for_discovery` | 343 | Extract N deduped search terms |
| `_profile_free_source_targets` | 365 | Generate GH/HN/Reddit queries |
| `_profile_x_queries` | 375 | Generate X search queries |
| `_has_x_token` | 385 | Check X API token availability |
| `_int_cfg` | 395 | Parse + clamp int from config |
| `_truthy` | 403 | Truthy string check |
| `_free_sources_enabled` | 407 | Check free sources flag |
| `_broadcast_x_source_errors` | 411 | Broadcast X errors to WS |

### Background scan functions (lines 420-507)

| Function | Line | Purpose | Lines |
|----------|------|---------|-------|
| `_run_x_signal_scan` | 420 | Run X scout in thread, broadcast results | 48 |
| `_run_free_source_scan` | 471 | Run free scout in thread, broadcast results | 37 |

### Ghost mode (lines 519-685)

| Function | Line | Purpose | Lines |
|----------|------|---------|-------|
| `_should_preserve_job_status` | 519 | Check if status should survive reeval | 2 |
| `_job_eval_document` | 523 | Format lead for evaluator | 9 |
| `_ghost_tick` | 533 | Acquire lock → delegate → release | 12 |
| `_ghost_tick_impl` | 546 | Full ghost cycle (6 phases) | **139** ⚠️ |

### Lifespan & middleware (lines 688-743)

| Function | Line | Purpose |
|----------|------|---------|
| `lifespan` | 689 | FastAPI lifespan — config validation, scheduler start/stop |
| `correlation_context_middleware` | 716 | Correlation ID per request |
| `require_http_token` | 732 | Bearer token auth for non-health, non-OPTIONS |

### Route helpers (lines 796-818, 854-873)

| Function | Line | Purpose |
|----------|------|---------|
| `_configured_api_providers` | 796 | Filter settings for API key names |
| `_annotate_job_lead` | 807 | Annotate lead with seniority level |
| `_versioned_assets` | 854 | Scan dir for versioned PDFs |

### Background task runners (lines 1286-1451)

| Function | Line | Purpose | Lines |
|----------|------|---------|-------|
| `_run_scan_task` | 1286 | Wrapper: acquire lock → run scan → release | 16 |
| `_run_reevaluate_jobs_task` | 1303 | Wrapper: acquire lock → run reeval → release | 16 |
| `_run_reevaluate_jobs` | 1320 | Iterate + score all job leads | 56 ⚠️ |
| `_run_scan` | 1377 | Full scan pipeline: X + free + scout + eval | 75 ⚠️ |

### Utility functions (lines 1454-1477, 1491-1542, 1918-1934, 2034-2124)

| Function | Line | Purpose | Lines |
|----------|------|---------|-------|
| `_sensitive` | 1454 | Return set of sensitive config keys | 5 |
| `_log_sensitive_deprecation` | 1461 | Warn on secrets in SQLite | 17 |
| `_probe_provider_key` | 1491 | Probe LLM API key (6-branch if/elif) | 52 ⚠️ |
| `_asset_ready` | 1918 | Check file exists | 2 |
| `_fire_blocker` | 1922 | Validate fire preconditions | 13 |
| `_generate_one` | 2034 | Full generation pipeline for one lead | **63** ⚠️ |
| `_actuate` | 2099 | Browser + submit application | 26 |

---

## 5. Route Map

| Method | Path | Handler | Body/Params | Notes |
|--------|------|---------|-------------|-------|
| GET | `/health` | `health` | none | DB/browser/API key probes |
| GET | `/api/v1/leads` | `leads` | `beginner_only`, `seniority` | Filters by seniority |
| GET | `/api/v1/leads/export.csv` | `export_leads_csv` | none | CSV stream |
| GET | `/api/v1/leads/{job_id}/versions` | `get_lead_versions` | path: job_id | Versioned PDFs |
| GET | `/api/v1/leads/{job_id}` | `get_lead` | path: job_id | Single lead |
| DELETE | `/api/v1/leads/{job_id}` | `delete_lead_endpoint` | path: job_id | Delete lead |
| PUT | `/api/v1/leads/{job_id}/status` | `update_status` | path + StatusBody | Update status |
| PUT | `/api/v1/leads/{job_id}/feedback` | `update_feedback` | path + FeedbackBody | Save feedback |
| PUT | `/api/v1/leads/{job_id}/followup` | `update_followup` | path + FollowupBody | Followup interval |
| POST | `/api/v1/leads/manual` | `create_manual_lead` | ManualLeadBody | Manual lead entry |
| GET | `/api/v1/followups/due` | `due_followups` | `limit` | Due followups |
| POST | `/api/v1/leads/{job_id}/generate` | `generate_for_lead` | path: job_id | Delegate to _generate_one |
| POST | `/api/v1/leads/{job_id}/pipeline/run` | `run_pipeline` | path: job_id + BackgroundTasks | Graph pipeline |
| GET | `/api/v1/leads/{job_id}/pdf` | `get_lead_pdf` | path: job_id, `kind`, `version` | Serve PDF |
| GET | `/api/v1/template` | `get_template` | none | Resume template |
| POST | `/api/v1/template` | `save_template` | TemplateBody | Save template |
| GET | `/api/v1/events` | `get_events_endpoint` | `limit`, `job_id` | System events |
| GET | `/api/v1/graph` | `graph_stats` | none | Graph counts |
| GET | `/api/v1/profile` | `get_profile_endpoint` | none | Candidate profile |
| PUT | `/api/v1/profile/candidate` | `update_candidate_endpoint` | CandidateBody | Name/summary |
| POST | `/api/v1/profile/skill` | `add_skill_endpoint` | SkillBody | Add skill |
| PUT | `/api/v1/profile/skill/{sid}` | `update_skill_endpoint` | path + SkillBody | Update skill |
| DELETE | `/api/v1/profile/skill/{sid}` | `delete_skill_endpoint` | path | Delete skill |
| POST | `/api/v1/profile/experience` | `add_experience_endpoint` | ExperienceBody | Add experience |
| PUT | `/api/v1/profile/experience/{eid}` | `update_experience_endpoint` | path + ExperienceBody | Update experience |
| DELETE | `/api/v1/profile/experience/{eid}` | `delete_experience_endpoint` | path | Delete experience |
| POST | `/api/v1/profile/project` | `add_project_endpoint` | ProjectBody | Add project |
| PUT | `/api/v1/profile/project/{pid}` | `update_project_endpoint` | path + ProjectBody | Update project |
| DELETE | `/api/v1/profile/project/{pid}` | `delete_project_endpoint` | path | Delete project |
| POST | `/api/v1/scan` | `scan` | none | Start scan task |
| POST | `/api/v1/scan/stop` | `stop_scan` | none | Stop scan |
| POST | `/api/v1/leads/reevaluate` | `reevaluate_jobs` | none | Start reeval task |
| POST | `/api/v1/leads/reevaluate/stop` | `stop_reevaluate_jobs` | none | Stop reeval |
| POST | `/api/v1/leads/cleanup` | `cleanup_leads` | `dry_run`, `limit` | Clean bad data |
| POST | `/api/v1/free-sources/scan` | `free_sources_scan` | none | Direct free scan |
| POST | `/api/v1/help/chat` | `help_chat` | HelpChatBody | Help agent |
| POST | `/api/v1/settings` | `save_cfg` | SettingsBody | Save settings |
| GET | `/api/v1/settings` | `get_cfg` | none | Masked settings |
| GET | `/api/v1/settings/validate` | `validate_settings` | none | Probe all provider keys |
| POST | `/api/v1/ingest` | `ingest` | `raw` (Form) + `file` (UploadFile) | Resume ingestion |
| POST | `/api/v1/ingest/linkedin` | `ingest_linkedin` | file: UploadFile | LinkedIn export |
| POST | `/api/v1/ingest/github` | `ingest_github_endpoint` | GithubIngestBody | GitHub profile |
| POST | `/api/v1/ingest/profile` | `import_profile_json` | ProfileImportBody | Full profile import |
| GET | `/api/v1/ingest/profile/template` | `get_profile_template` | none | Schema example |
| POST | `/api/v1/ingest/portfolio` | `ingest_portfolio_endpoint` | PortfolioIngestBody | Portfolio URL |
| POST | `/api/v1/fire/{job_id}` | `fire` | path + BackgroundTasks | Fire application |
| POST | `/api/v1/leads/{job_id}/form/read` | `read_lead_form` | path + FormReadBody | Read form fields |
| GET | `/api/v1/identity` | `get_identity` | none | Identity fields |
| POST | `/api/v1/selectors/refresh` | `refresh_selectors` | none | Refresh form selectors |
| POST | `/api/v1/leads/{job_id}/apply/preview` | `preview_apply` | path | Dry-run apply |
| WS | `/ws` | `ws_endpoint` | — | WebSocket with heartbeat |

**Total: 50 routes** (49 HTTP + 1 WebSocket)

---

## 6. Exception Handling Audit

| Location | Caught | Handling | Risk |
|----------|--------|----------|------|
| `_validate_config_on_startup:44` | bare `Exception` | `_log.critical` + `sys.exit(1)` | OK — startup fatal |
| `_CM.broadcast:196` | bare `Exception` | `_log.warning`, continues | OK — fire-and-forget |
| `_int_cfg:397` | bare `Exception` | defaults to configured default | **LOW** — silences all conversion errors |
| `health:764` | bare `Exception` | sets db_status="error" | OK — graceful degradation |
| `_versioned_assets:862` | bare `Exception` | returns `[]` | **LOW** — silences all FS errors |
| `_ghost_tick_impl:590,614,649,679` | bare `Exception` | broadcasts error, continues | **MEDIUM** — 4 broad catches, no distinction between transient/fatal |
| `_run_scan_task:1295` | bare `Exception` | logs + broadcasts | OK — task wrapper |
| `_run_reevaluate_jobs_task:1312` | bare `Exception` | logs + broadcasts | OK — task wrapper |
| `_run_reevaluate_jobs:1363` | bare `Exception` | increments failed counter | OK — continues loop |
| `_run_scan:1448` | bare `Exception` | broadcasts error, continues | OK — continues loop |
| `_probe_provider_key:1540` | bare `Exception` | sets "unreachable" | OK — probe failure expected |
| `ingest_linkedin:`1708,1714,1720,1726,1732,1738 | bare `Exception` | logs/appends to errors | OK — per-item |
| `_generate_one:2093` | bare `Exception` | raises HTTPException(500) | OK — fatal for this request |
| `ws_endpoint:2150` | bare `Exception` | `_log.warning` | OK — WS exceptions expected |

**Silent failures (bare `except:pass`):** **NONE FOUND** ✅

**Pattern:** All but one broad catch are logged or broadcast. No silent swallowing.

---

## 7. Dependency Graph

### External dependencies
- `db.client` — called from ~35 route/function bodies (lazy imports)
- `agents.*` — `scout`, `evaluator`, `generator`, `actuator`, `query_gen`, `x_scout`, `free_scout`, `lead_intel`, `help_agent`, `ingestor`, `linkedin_parser`, `github_ingestor`, `portfolio_ingestor`, `contact_lookup`, `selectors`, `browser_runtime`, `quality_gate` — scattered across handlers
- `config` / `config.secrets` — loaded lazily in many functions (though also at module top level)
- `graph` — `PipelineState`, `eval_graph` — only in `run_pipeline`
- `logger` — used at module level
- `log_context` — used in middleware + background functions

### Internal dependency web
- `_job_targets` → `_job_market_focus` → `_split_configured_targets` → `_is_hn_target` → `_dedupe_targets`
- `_profile_for_discovery` → `_desired_position`
- `_terms_for_discovery` → `_profile_free_source_targets` → `_profile_x_queries`
- `_run_x_signal_scan` → `_has_x_token` → `_int_cfg` → `_truthy` → `_profile_x_queries` → `_broadcast_x_source_errors`
- `_run_free_source_scan` → `_free_sources_enabled` → `_truthy` → `_int_cfg` → `_profile_free_source_targets`
- `_ghost_tick_impl` → `_run_x_signal_scan` → `_run_free_source_scan` → `_job_targets` → `_has_x_token` → `_ghost_tick`
- `_run_scan` → `_run_x_signal_scan` → `_run_free_source_scan` → `_job_targets` → `_profile_for_discovery`
- `_run_scan_task` → `_run_scan`
- `_run_reevaluate_jobs_task` → `_run_reevaluate_jobs`
- `run_pipeline` → via `BackgroundTasks` → inner `_run`
- `fire` → via `BackgroundTasks` → `_actuate` → `_fire_blocker` → `_asset_ready`
- `generate_for_lead` → `_generate_one`
- `cm` → called from 25+ locations across the file

### Global state access
- `cm` (WebSocket manager) — read/written in 25+ locations
- `_sched` (scheduler) — read/written in `lifespan` + `save_cfg`
- `_scan_task` / `_reevaluate_task` — read/written in route handlers + task wrappers
- `_scan_stop` / `_reevaluate_stop` — set/read across 4+ locations

### Circular dependencies
- None detected within `main.py`. The lazy import pattern exists specifically to avoid circular imports between `main.py`, `db/client.py`, and `agents/*`.

---

## 8. Refactor Risk Assessment

### High Risk
1. **`cm` global WebSocket manager** — used from 25+ locations across routes, background tasks, and middleware. Any refactor to make this injectable requires touching every broadcast call site.
2. **`_ghost_tick_impl` (139 lines, lines 546-685)** — six distinct phases (X scan, free scan, scout, eval, gen, apply) in one function. Deeply nested (3-level loops with try/except). Highest cyclomatic complexity in the file.
3. **`_scan_task` / `_reevaluate_task` / `_scan_stop` / `_reevaluate_stop` / `_ghost_lock`** — five correlated global variables whose state transitions span routes and background tasks. A concurrent state machine hidden in module-level globals.
4. **`_sched` global scheduler** — mutated in `lifespan` (startup) and `save_cfg` (runtime when ghost_mode enabled). Adding/removing jobs from arbitrary routes.

### Medium Risk
5. **`_run_scan` (75 lines)** — does 5 things: pre-scans (X + free), query gen, board scout, evaluation loop. Tightly coupled to job targets config, profile, and stop events.
6. **`_run_reevaluate_jobs` (56 lines)** — single evaluation loop with broadcast. Moderate complexity.
7. **`_generate_one` (63 lines)** — mixes asset generation, raw SQL, contact lookup, and WebSocket broadcast. Contains inline `f"UPDATE leads SET {sets} WHERE job_id=?"` SQL string building.
8. **`_probe_provider_key` (52 lines)** — 6-branch if/elif chain with near-identical HTTP probe logic per provider.
9. **`_job_targets` (27 lines)** — parses, filters by blocked marketplaces, applies market-focus filtering, and falls back to defaults. Four concerns in one function.
10. **Lazy imports obscure the dependency graph** — every route handler and background function imports locally. Makes it impossible to see the full dependency footprint of the file without reading every function body.

### Low Risk
11. **`_versioned_assets`** — isolated utility function reading filesystem
12. **`_annotate_job_lead`** — pure lead transformation
13. **`_fire_blocker` / `_asset_ready`** — pure validation functions
14. **Job target helper functions** (`_split_configured_targets`, `_dedupe_targets`, `_truthy`, `_int_cfg`) — pure, stateless
15. **`_sensitive` / `_log_sensitive_deprecation`** — isolated config helpers
16. **New functions** (`_broadcast_x_source_errors`, `_should_preserve_job_status`, `_job_eval_document`, `_configured_api_providers`) — small, focused

---

## 9. Suggested Module Boundaries

Based on analysis, these are natural split points. Observations only — not a refactor plan.

### Suggested modules:

| Module | Contains | Rationale |
|--------|----------|-----------|
| `routes/leads.py` | GET/PUT/DELETE `/api/v1/leads/*`, export, versions, manual, followups | 12 lead-related routes |
| `routes/profile.py` | GET `/api/v1/profile`, PUT candidate, CRUD skills/experience/projects, identity | 11 profile routes |
| `routes/settings.py` | GET/POST `/api/v1/settings`, GET `/api/v1/settings/validate` | Settings management |
| `routes/ingest.py` | POST `/api/v1/ingest`, `/ingest/linkedin`, `/ingest/github`, `/ingest/profile`, `/ingest/portfolio`, template | 6 ingest endpoints |
| `routes/scan.py` | POST `/api/v1/scan`, `/scan/stop`, `/leads/reevaluate`, `/leads/reevaluate/stop`, `/leads/cleanup`, `/free-sources/scan` | Scan lifecycle |
| `routes/actions.py` | POST `/api/v1/fire/{job_id}`, `/leads/{job_id}/generate`, `/leads/{job_id}/pipeline/run`, `/leads/{job_id}/form/read`, `/leads/{job_id}/apply/preview`, `/leads/{job_id}/pdf` | Lead actions |
| `routes/misc.py` | `/health`, `/events`, `/graph`, `/template`, `/help/chat`, `/selectors/refresh` | 7 standalone routes |
| `services/ghost.py` | `_ghost_tick`, `_ghost_tick_impl`, `_should_preserve_job_status`, `_job_eval_document`, `_fire_blocker`, `_asset_ready` | Ghost mode orchestration |
| `services/scanner.py` | `_run_scan`, `_run_reevaluate_jobs`, `_run_scan_task`, `_run_reevaluate_jobs_task` | Background task runners |
| `services/scout.py` | `_run_x_signal_scan`, `_run_free_source_scan`, `_broadcast_x_source_errors`, `_has_x_token`, `_free_sources_enabled` | X + free source scanning |
| `services/scheduler.py` | `_sched`, `lifespan` scheduler setup | APScheduler lifecycle |
| `services/generator.py` | `_generate_one`, `_actuate` | Asset generation + submission |
| `services/job_targets.py` | `_job_targets`, `DEFAULT_JOB_TARGETS`, `INDIA_JOB_TARGETS`, `_BLOCKED_JOB_TARGET_MARKERS`, all helper functions | Job board target config |
| `services/profile_helpers.py` | `_profile_for_discovery`, `_profile_free_source_targets`, `_profile_x_queries`, `_terms_for_discovery` | Profile-driven query generation |
| `services/provider_probe.py` | `_probe_provider_key`, `validate_settings` nested logic | LLM provider key probing |
| `core/config_constants.py` | `_UP`, `_API_TOKEN`, `_LOCAL_ORIGIN_RE`, `_bearer` | App-wide constants |
| `core/ws_manager.py` | `_CM` class + `cm` singleton | WebSocket connection manager (extracted from main.py) |
| `core/exceptions.py` | Custom exception classes (none currently exist) | Centralized error types |

### What must stay in `main.py`:
- FastAPI app instantiation (`app = FastAPI(...)`)
- Lifespan setup (config validation + scheduler start)
- Middleware registration (CORS, correlation context, auth)
- Router inclusion (import + `app.include_router(...)`)
- CLI entrypoint (`if __name__ == "__main__"`)
- The `_require_ws_token` guard (used only by WS endpoint)
- The WS endpoint itself (`ws_endpoint`) — could move to `routes/ws.py`

---

## 10. Open Questions for Refactor

1. **Global `cm` manager**: Should become an injected dependency, or is a module-level singleton acceptable for WebSocket connections in a single-process app? If injected, all 25+ call sites and test setup change.

2. **`_scan_task` / `_reevaluate_task` global state**: Five correlated globals (`_scan_task`, `_scan_stop`, `_reevaluate_task`, `_reevaluate_stop`, `_ghost_lock`) implement a hidden state machine. Should this become a proper `ScanManager` class with methods like `start_scan()`, `stop_scan()`, `is_scanning()`?

3. **`_ghost_tick_impl` decomposition**: Should ghost mode phases become separate modules (e.g., `ghost/scout.py`, `ghost/eval.py`, `ghost/gen.py`, `ghost/apply.py`)? Or is a single `ghost.py` with smaller functions sufficient?

4. **`_run_scan` and `_run_reevaluate_jobs`**: Near-duplicate task wrapper pattern (`_run_*_task` → acquire lock → run → catch → release). Should become a shared `_run_with_ghost_lock` wrapper.

5. **`ingest_linkedin` and `import_profile_json`**: Near-identical try/except repetition 6-8 times per function. Should accept a list of (extractor, persister, field_name) tuples to DRY?

6. **`_int_cfg` broad `except:`**: Line 397 catches all exceptions silently. Is `TypeError` from `.get(key, "")` safe to ignore, or should only `(ValueError, TypeError)` be caught? The current behavior masks misconfigured but present keys.

7. **`DEFAULT_JOB_TARGETS` / `INDIA_JOB_TARGETS` mutability**: Should become `tuple[str, ...]` to prevent accidental mutation, or are they intentionally mutable?

8. **Pydantic model placement**: Models are scattered across the file (lines 91-169 for request bodies, lines 1623-1684 for ingest bodies). Should they move to a separate `schemas/` module, or is the `StrictBody` base + inline approach intentional?

9. **`require_http_token` dead code**: Line 736 `if request.url.path != "/health"` is unreachable because `/health` already returns at line 734. Intentional defensive guard or should be removed?

10. **Response models**: Zero routes use `response_model=`. This means no OpenAPI response schemas, no auto-validation, no docs. Is this acceptable or should refactor add them?
