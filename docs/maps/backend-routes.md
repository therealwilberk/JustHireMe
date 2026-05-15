# Map: backend-routes
**File:** `docs/maps/backend-routes.md`
**Codebase path(s):** `backend/routes/`
**Files in scope:** 9 (including `__init__.py`)
**Total lines:** ~1,662 (was 1,662; +20 lines config, -7 lines routes; net +13 resolved 2026-05-15)
**Generated:** 2026-05-15

---

## 1. Unit summary

`backend/routes/` is the HTTP API layer of JustHireMe. It owns all REST endpoints and one WebSocket endpoint, organized into 8 router modules (plus an empty `__init__.py`). Each module maps to a logical domain: actions (fire/read/preview), ingest (profile import from 6 sources), leads (CRUD + pipeline), misc (health/events/template/chat), profile (CRUD for candidate sub-entities), scan (lifecycle + reevaluation + free-sources), settings (CRUD + key validation + job-targets), and ws (real-time event streaming). All routers are registered in `backend/main.py:173-180`. Every endpoint except `/health` and `/ws` is guarded by a bearer token middleware (`main.py:162-170`). The unit depends on `db.client` (persistence), `agents.*` (LLM-driven logic), `services.*` (business logic), `core.config_constants` (startup state), and `config` (typed settings).

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `routes/__init__.py` | 0 | Package marker, empty | 🟢 — standard Python package init |
| 2 | `routes/actions.py` | 212 | Fire, PDF, form read, identity, selectors refresh, preview | ✅ RESOLVED — `_SELECTORS_RESET_AT` constant extracted |
| 3 | `routes/ingest.py` | 357 | Profile ingestion from 6 sources (paste, PDF, LinkedIn, GitHub, JSON, portfolio) | ✅ RESOLVED — upload limit wired to config |
| 4 | `routes/leads.py` | 404 | Lead CRUD, pipeline, CSV export, follow-ups | 🟡 SUSPECT — largest file at 404 lines; `_annotate_job_lead` is helper that could live in `services.scout` |
| 5 | `routes/misc.py` | 144 | Health, events, graph stats, template, help chat | ✅ RESOLVED — dead imports removed |
| 6 | `routes/profile.py` | 203 | Candidate info, skills, experience, projects CRUD | 🟢 — clean CRUD, consistent validation |
| 7 | `routes/scan.py` | 126 | Scan start/stop, reevaluate, cleanup, free-sources, help chat | ✅ RESOLVED — broadcast cap wired to config |
| 8 | `routes/settings.py` | 160 | Settings CRUD, API key validation, job-targets | ✅ RESOLVED — ghost interval wired to config |
| 9 | `routes/ws.py` | 60 | WebSocket endpoint for real-time streaming + heartbeat | ✅ RESOLVED — heartbeat timeout wired to config |

---

## 3. Detailed breakdown

### `routes/__init__.py`

**Purpose:** Python package marker. Empty file. No content, no imports. Needed only for `from routes import ...` to work.

**Imports:** None

**Module-level constants & state:** None

**Exports:** None

---

### `routes/actions.py`

**Purpose:** Fire actions (application submission), PDF downloads, application form reading, identity retrieval, selector refresh, and application preview. All endpoints are prefixed `/api/v1`. The module name is slightly underspecified — "actions" is vague, but the routes are functionally coherent (things a user "does" to a lead).

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | fire, preview | 🟢 |
| `os` | stdlib | get_lead_pdf | 🟢 |
| `typing.Any` | stdlib | read_lead_form | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.BackgroundTasks` | 3rd-party | fire, preview | 🟢 |
| `fastapi.responses.FileResponse` | 3rd-party | get_lead_pdf | 🟢 |
| `fastapi.HTTPException` | 3rd-party | error handling | 🟢 |
| `schemas.requests.FormReadBody` | local | read_lead_form type hint | 🟢 |
| `schemas.responses.FireResponse` | local | fire return type | 🟢 |
| `schemas.responses.IdentityResponse` | local | get_identity return type | 🟢 |
| `schemas.responses.SelectorsRefreshResponse` | local | refresh_selectors return type | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `prefix="/api/v1"` | main.py include_router | 🟢 |

**Functions:**

#### `get_lead_pdf(job_id: str, kind: str = "resume", version: int | None = None) -> FileResponse`
- **Purpose:** Download resume or cover letter PDF for a lead, with optional versioned asset retrieval.
- **Called by:** HTTP GET `/api/v1/leads/{job_id}/pdf`
- **Calls:** `get_lead_by_id`, `data_base`, `os.path.exists`, `os.path.dirname`, `os.path.join`
- **Side effects:** File read / FileResponse (no DB writes)
- **Hardcodes:** `"resume"`, `"cover_letter"` asset type strings; filename pattern `f"{job_id}_v{version}.pdf"` / `f"{job_id}_cl_v{version}.pdf"`
- **Flag:** 🟢 — clean, well-documented

#### `fire(job_id: str, bt: BackgroundTasks) -> FireResponse`
- **Purpose:** Submit an application for a lead in the background after checking blockers.
- **Called by:** HTTP POST `/api/v1/fire/{job_id}`
- **Calls:** `get_lead_for_fire`, `_fire_blocker`, `_actuate`
- **Side effects:** Schedules `_actuate` via BackgroundTasks (side effect deferred)
- **Flag:** 🟢 — clean pattern, lazy imports justify the pattern

#### `read_lead_form(job_id: str, body: FormReadBody) -> dict[str, Any]`
- **Purpose:** Read and parse an external application form using the actuator agent with identity data.
- **Called by:** HTTP POST `/api/v1/leads/{job_id}/form/read`
- **Calls:** `get_lead_by_id`, `get_profile`, `get_settings`, `read_form` (agent), file I/O for cover letter
- **Side effects:** File read (cover letter .md), HTTP fetch via agent
- **Flag:** 🟢 — clean, but identity construction duplicates `get_identity` logic

#### `get_identity() -> IdentityResponse`
- **Purpose:** Retrieve the user's identity/profile settings from DB.
- **Called by:** HTTP GET `/api/v1/identity`
- **Calls:** `get_settings`
- **Side effects:** None
- **Hardcodes:** Field mapping dict keys (`full_name`, `email`, etc.)
- **Flag:** 🟢 — simple passthrough

#### `refresh_selectors() -> SelectorsRefreshResponse`
- **Purpose:** Force-refresh cached CSS selectors by resetting timestamp and re-downloading.
- **Called by:** HTTP POST `/api/v1/selectors/refresh`
- **Calls:** `get_selectors`, `save_settings`
- **Side effects:** DB write (`selectors_fetched_at` reset)
- **Hardcodes:** `"selectors_fetched_at": "0"` — magic string
- **Flag:** 🔵 HARDCODED — `"0"` as magic reset value should be a constant

#### `preview_apply(job_id: str) -> dict[str, Any]`
- **Purpose:** Dry-run application submission using the actuator in preview mode.
- **Called by:** HTTP POST `/api/v1/leads/{job_id}/apply/preview`
- **Calls:** `get_lead_for_fire`, `_fire_blocker`, `_act` (actuator.run with preview=True)
- **Side effects:** None (preview mode — no actual submission)
- **Flag:** 🟢 — clean

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:179` |

---

### `routes/ingest.py`

**Purpose:** Profile ingestion from 6 sources: raw text/PDF paste (`/ingest`), LinkedIn ZIP export (`/ingest/linkedin`), GitHub username (`/ingest/github`), structured JSON (`/ingest/profile`), portfolio URL (`/ingest/portfolio`), plus a schema template endpoint (`/ingest/profile/template`). All prefixed `/api/v1`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | threading wrapper | 🟢 |
| `json` | stdlib | template JSON load | 🟢 |
| `os` | stdlib | tempfile cleanup | 🟢 |
| `shutil` | stdlib | tempfile copy | 🟢 |
| `tempfile` | stdlib | PDF upload handling | 🟢 |
| `pathlib.Path` | stdlib | template path | 🟢 |
| `typing.Any` | stdlib | type hint | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.File` | 3rd-party | file upload param | 🟢 |
| `fastapi.Form` | 3rd-party | form param | 🟢 |
| `fastapi.HTTPException` | 3rd-party | error handling | 🟢 |
| `fastapi.UploadFile` | 3rd-party | file upload type | 🟢 |
| `core.config_constants._log` | local | logging | 🟢 |
| `core.ws_manager.cm` | local | WS broadcast | 🟢 |
| `schemas.requests.*` (7 types) | local | request body schemas | 🟢 |
| `schemas.responses.*` (3 types) | local | response schemas | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `prefix="/api/v1"` | main.py include_router | 🟢 |

**Functions:**

#### `ingest(raw: str = "", file: UploadFile | None = None) -> dict[str, Any]`
- **Purpose:** Ingest a profile from raw text or uploaded PDF, broadcast via WebSocket on completion.
- **Called by:** HTTP POST `/api/v1/ingest`
- **Calls:** `_ingest` (agent), `refresh_profile_snapshot`, `cm.broadcast`
- **Side effects:** DB write (profile update), WS broadcast, temp file cleanup
- **Flag:** 🟢 — clean; tempfile cleanup in `finally` is correct

#### `ingest_linkedin(file: UploadFile) -> IngestLinkedinResponse`
- **Purpose:** Import profile from a LinkedIn data export ZIP file, parsing into candidate/skills/experience/education/projects/certifications.
- **Called by:** HTTP POST `/api/v1/ingest/linkedin`
- **Calls:** `parse_linkedin_export`, `update_candidate`, `add_skill`, `add_experience`, `add_education`, `add_project`, `add_certification`
- **Side effects:** DB writes (multiple entities), file read
- **Hardcodes:** `50 * 1024 * 1024` (50 MB limit)
- **Flag:** 🔵 HARDCODED — file size limit should be in settings

#### `ingest_github_endpoint(body: GithubIngestBody) -> IngestGithubResponse`
- **Purpose:** Import GitHub profile data by username, extracting skills and projects.
- **Called by:** HTTP POST `/api/v1/ingest/github`
- **Calls:** `ingest_github`, `add_skill`, `add_project`, `save_settings`
- **Side effects:** DB writes (skills, projects, settings)
- **Flag:** 🟢 — clean

#### `import_profile_json(body: ProfileImportBody) -> IngestProfileResponse`
- **Purpose:** Import a full profile from structured JSON, saving candidate, identity, skills, experience, projects, education, certifications, achievements.
- **Called by:** HTTP POST `/api/v1/ingest/profile` (directly), and `ingest_portfolio_endpoint` (indirectly via auto_import)
- **Calls:** `update_candidate`, `add_skill`, `add_experience`, `add_education`, `add_certification`, `add_achievement`, `add_project`, `save_settings`
- **Side effects:** DB writes (7 entity types)
- **Flag:** 🟡 SUSPECT — called recursively by `ingest_portfolio_endpoint`; the indirection (`import_profile_json` → repeats the stats dict per call) is awkward

#### `get_profile_template() -> dict[str, Any]`
- **Purpose:** Return the JSON profile schema example from a static file.
- **Called by:** HTTP GET `/api/v1/ingest/profile/template`
- **Calls:** `json.load` on a static file
- **Side effects:** File read
- **Flag:** 🟢 — simple, static

#### `ingest_portfolio_endpoint(body: PortfolioIngestBody) -> dict[str, Any]`
- **Purpose:** Ingest profile from a portfolio website URL, with optional auto-import.
- **Called by:** HTTP POST `/api/v1/ingest/portfolio`
- **Calls:** `ingest_portfolio_url`, `import_profile_json` (when auto_import=True)
- **Side effects:** HTTP fetch, optional DB writes via `import_profile_json`
- **Flag:** 🟡 SUSPECT — calls `import_profile_json` directly (bypassing HTTP layer); this is the same pattern used elsewhere but the dependency on another route function is unusual

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:178` |

---

### `routes/leads.py`

**Purpose:** Lead CRUD (list, get, delete, create manual), status/feedback/followup updates, CSV export, versioned asset listing, pipeline execution, and lead generation. Largest file in the unit at 404 lines.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | thread wrappers | 🟢 |
| `csv` | stdlib | CSV export | 🟢 |
| `io` | stdlib | CSV buffer | 🟢 |
| `os` | stdlib | path operations | 🟢 |
| `re` | stdlib | versioned filename matching | 🟢 |
| `typing.Any` | stdlib | type hints | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.BackgroundTasks` | 3rd-party | pipeline run | 🟢 |
| `fastapi.HTTPException` | 3rd-party | error handling | 🟢 |
| `fastapi.responses.StreamingResponse` | 3rd-party | CSV export | 🟢 |
| `core.ws_manager.cm` | local | WS broadcast | 🟢 |
| `log_context.*` | local | logging context | 🟢 |
| `schemas.requests.*` (4 types) | local | request schemas | 🟢 |
| `schemas.responses.*` (3 types) | local | response schemas | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `prefix="/api/v1"` | main.py include_router | 🟢 |

**Functions:**

#### `_annotate_job_lead(lead: dict) -> dict`
- **Purpose:** Classify seniority level and enrich lead metadata inline.
- **Called by:** `leads()` (GET /leads), `get_lead()` (GET /leads/{job_id}), `create_manual_lead()`
- **Calls:** `classify_job_seniority` (agent)
- **Side effects:** None
- **Flag:** 🟡 SUSPECT — mutates `source_meta` in-place; this mix of data enrichment and routing could live in `services.scout`

#### `_versioned_assets(job_id: str, base_dir: str) -> list[dict]`
- **Purpose:** Discover versioned resume and cover letter PDFs on disk by scanning filenames.
- **Called by:** `get_lead_versions()`
- **Calls:** `os.listdir`, `os.path.isfile`, `os.path.join`
- **Side effects:** File system scan
- **Flag:** 🟢 — clean helper, regex patterns well-defined

#### `leads(beginner_only: bool = False, seniority: str | None = None) -> list[dict[str, Any]]`
- **Purpose:** Retrieve all job leads, optionally filtered by seniority level.
- **Called by:** HTTP GET `/api/v1/leads`
- **Calls:** `get_all_leads`, `_annotate_job_lead`
- **Side effects:** None
- **Hardcodes:** `"fresher"`, `"junior"`, `"mid"`, `"senior"`, `"unknown"` — duplicate set from `_annotate_job_lead`
- **Flag:** 🔵 HARDCODED — seniority level strings duplicated in two places

#### `export_leads_csv() -> StreamingResponse`
- **Purpose:** Export all leads as CSV download.
- **Called by:** HTTP GET `/api/v1/leads/export.csv`
- **Calls:** `get_all_leads`
- **Side effects:** None (generates streaming response)
- **Flag:** 🟢 — clean

#### `get_lead_versions(job_id: str) -> list[dict[str, Any]]`
- **Purpose:** List versioned PDF assets for a lead.
- **Called by:** HTTP GET `/api/v1/leads/{job_id}/versions`
- **Calls:** `get_lead_by_id`, `data_base`, `_versioned_assets`
- **Side effects:** None
- **Flag:** 🟢 — clean

#### `get_lead(job_id: str) -> dict[str, Any]`
- **Purpose:** Retrieve a single lead by ID, annotated for job leads.
- **Called by:** HTTP GET `/api/v1/leads/{job_id}`
- **Calls:** `get_lead_by_id`, `_annotate_job_lead`
- **Side effects:** None
- **Flag:** 🟢 — clean

#### `delete_lead_endpoint(job_id: str) -> OkResponse`
- **Purpose:** Delete a lead by ID.
- **Called by:** HTTP DELETE `/api/v1/leads/{job_id}`
- **Calls:** `delete_lead`
- **Side effects:** DB write (deletion)
- **Flag:** 🟢 — clean

#### `update_status(job_id: str, body: StatusBody) -> OkResponse`
- **Purpose:** Update lead status and broadcast change via WebSocket.
- **Called by:** HTTP PUT `/api/v1/leads/{job_id}/status`
- **Calls:** `update_lead_status`, `cm.broadcast`
- **Side effects:** DB write, WS broadcast
- **Flag:** 🟢 — clean

#### `update_feedback(job_id: str, body: FeedbackBody) -> dict[str, Any]`
- **Purpose:** Save feedback note for a lead and broadcast.
- **Called by:** HTTP PUT `/api/v1/leads/{job_id}/feedback`
- **Calls:** `save_lead_feedback`, `cm.broadcast`
- **Side effects:** DB write, WS broadcast
- **Flag:** 🟢 — clean

#### `update_followup(job_id: str, body: FollowupBody) -> dict[str, Any]`
- **Purpose:** Set follow-up interval for a lead and broadcast.
- **Called by:** HTTP PUT `/api/v1/leads/{job_id}/followup`
- **Calls:** `update_lead_followup`, `cm.broadcast`
- **Side effects:** DB write, WS broadcast
- **Flag:** 🟢 — clean

#### `create_manual_lead(body: ManualLeadBody) -> dict[str, Any]`
- **Purpose:** Create a lead from pasted text or URL using lead intel agent.
- **Called by:** HTTP POST `/api/v1/leads/manual`
- **Calls:** `rank_lead_by_feedback`, `manual_lead_from_text`, `_annotate_job_lead`, `save_lead`, `get_lead_by_id`, `cm.broadcast`
- **Side effects:** DB write, WS broadcast
- **Hardcodes:** `"job"` kind filter — hardcoded string
- **Flag:** 🔵 HARDCODED — `"job"` kind is baked in; `save_lead` call passes 20+ keyword arguments which is brittle

#### `due_followups(limit: int = 25) -> list[dict[str, Any]]`
- **Purpose:** Retrieve leads with past-due follow-ups.
- **Called by:** HTTP GET `/api/v1/followups/due`
- **Calls:** `get_due_followups`
- **Side effects:** None
- **Flag:** 🟢 — clean

#### `generate_for_lead(job_id: str) -> LeadGenerateResponse`
- **Purpose:** Trigger asset generation for a lead.
- **Called by:** HTTP POST `/api/v1/leads/{job_id}/generate`
- **Calls:** `_generate_one`
- **Side effects:** DB writes (asset generation)
- **Flag:** 🟢 — clean

#### `run_pipeline(job_id: str, bt: BackgroundTasks) -> PipelineRunResponse`
- **Purpose:** Start pipeline evaluation via LangGraph in background, broadcast result on completion.
- **Called by:** HTTP POST `/api/v1/leads/{job_id}/pipeline/run`
- **Calls:** `get_lead_by_id`, `get_profile`, `get_settings`, `eval_graph.invoke`, `cm.broadcast`, log context
- **Side effects:** DB read, WS broadcast (from background task)
- **Flag:** 🟢 — clean; uses log context correctly with try/finally reset

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:175` |

---

### `routes/misc.py`

**Purpose:** Health check, events retrieval, graph/dashboard stats, resume template CRUD, and help chat. The module name "misc" is honest but signals a grab-bag — the route grouping is the least coherent in the unit.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | help_chat thread wrap | 🟢 |
| `os` | stdlib | log level from env | 🟢 |
| `time` | stdlib | uptime calculation | 🟢 |
| `datetime.*` | stdlib | timestamp | 🟢 |
| `typing.Any` | stdlib | type hints | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.HTTPException` | 3rd-party | (imported but unused in this file) | 🔴 DEAD — unused import |
| `fastapi.responses.JSONResponse` | 3rd-party | (imported but unused in this file) | 🔴 DEAD — unused import |
| `config.settings` | local | log level env var name | 🟢 |
| `schemas.requests.*` (2 types) | local | request bodies | 🟢 |
| `schemas.responses.*` (3 types) | local | response schemas | 🟢 |
| `core.config_constants._log` | local | logging | 🟢 |
| `core.config_constants._UP` | local | uptime start time | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `tags=["misc"]` | main.py include_router | 🟢 |

**Functions:**

#### `_configured_api_providers(settings: dict) -> list`
- **Purpose:** Return names of API providers that have a configured key.
- **Called by:** `health()`
- **Flag:** 🟢 — clean helper

#### `health() -> HealthResponse`
- **Purpose:** Lightweight health check with DB, browser, and API key probes.
- **Called by:** HTTP GET `/health`
- **Calls:** `chromium_executable`, `get_settings`, `get_sql_connection`, `_configured_api_providers`
- **Side effects:** DB query
- **Flag:** 🟢 — clean health check; note: this is the only endpoint exempt from bearer auth (main.py:162)

#### `get_events_endpoint(limit: int = 100, job_id: str | None = None) -> list[dict[str, Any]]`
- **Purpose:** Retrieve recent application events.
- **Called by:** HTTP GET `/api/v1/events`
- **Calls:** `get_events`
- **Side effects:** DB read
- **Flag:** 🟢 — clean

#### `graph_stats() -> dict[str, Any]`
- **Purpose:** Retrieve aggregate graph/dashboard counts.
- **Called by:** HTTP GET `/api/v1/graph`
- **Calls:** `graph_counts`
- **Side effects:** DB read
- **Flag:** 🟢 — clean

#### `get_template() -> TemplateResponse`
- **Purpose:** Retrieve the saved resume template.
- **Called by:** HTTP GET `/api/v1/template`
- **Calls:** `get_setting`
- **Side effects:** DB read
- **Flag:** 🟢 — clean

#### `save_template(body: TemplateBody) -> OkResponse`
- **Purpose:** Save the resume template.
- **Called by:** HTTP POST `/api/v1/template`
- **Calls:** `save_settings`
- **Side effects:** DB write
- **Flag:** 🟢 — clean

#### `help_chat(body: HelpChatBody) -> dict[str, Any]`
- **Purpose:** Ask a question to the help agent.
- **Called by:** HTTP POST `/api/v1/help/chat`
- **Calls:** `answer` (help_agent)
- **Side effects:** LLM call (via help agent)
- **Flag:** 🟣 COUPLED — duplicate route with `scan.py:help_chat`; both register `POST /api/v1/help/chat`; registration order (misc at line 173, scan at line 177) means scan's handler shadows misc's

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:173` |

---

### `routes/profile.py`

**Purpose:** Profile CRUD for candidate info, skills, experience, and projects. All endpoints prefixed `/api/v1`. Straightforward CRUD with validation on each mutation endpoint.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `typing.Any` | stdlib | type hints | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.HTTPException` | 3rd-party | error handling | 🟢 |
| `schemas.requests.*` (4 types) | local | request bodies | 🟢 |
| `schemas.responses.OkResponse` | local | delete responses | 🟢 |
| `db.client.*` (10 functions) | local | DB operations | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `prefix="/api/v1"` | main.py include_router | 🟢 |

**Functions:**

#### `get_profile_endpoint() -> dict[str, Any]`
- **Purpose:** Retrieve the full user profile.
- **Called by:** HTTP GET `/api/v1/profile`
- **Calls:** `_gp` (get_profile)
- **Flag:** 🟢 — clean

#### `update_candidate_endpoint(body: CandidateBody) -> dict[str, Any]`
- **Purpose:** Update candidate name and summary.
- **Called by:** HTTP PUT `/api/v1/profile/candidate`
- **Flag:** 🟢 — clean validation

#### `add_skill_endpoint(body: SkillBody) -> dict[str, Any]`
- **Purpose:** Add a new skill.
- **Called by:** HTTP POST `/api/v1/profile/skill`
- **Flag:** 🟢 — clean

#### `update_skill_endpoint(sid: str, body: SkillBody) -> dict[str, Any]`
- **Purpose:** Update an existing skill.
- **Called by:** HTTP PUT `/api/v1/profile/skill/{sid}`
- **Flag:** 🟢 — clean

#### `delete_skill_endpoint(sid: str) -> OkResponse`
- **Purpose:** Delete a skill by ID.
- **Called by:** HTTP DELETE `/api/v1/profile/skill/{sid}`
- **Flag:** 🟢 — clean

#### `add_experience_endpoint(body: ExperienceBody) -> dict[str, Any]`
- **Purpose:** Add a new experience entry.
- **Called by:** HTTP POST `/api/v1/profile/experience`
- **Flag:** 🟢 — clean

#### `update_experience_endpoint(eid: str, body: ExperienceBody) -> dict[str, Any]`
- **Purpose:** Update an existing experience entry.
- **Called by:** HTTP PUT `/api/v1/profile/experience/{eid}`
- **Flag:** 🟢 — clean

#### `delete_experience_endpoint(eid: str) -> OkResponse`
- **Purpose:** Delete an experience entry by ID.
- **Called by:** HTTP DELETE `/api/v1/profile/experience/{eid}`
- **Flag:** 🟢 — clean

#### `add_project_endpoint(body: ProjectBody) -> dict[str, Any]`
- **Purpose:** Add a new project entry.
- **Called by:** HTTP POST `/api/v1/profile/project`
- **Flag:** 🟢 — clean

#### `update_project_endpoint(pid: str, body: ProjectBody) -> dict[str, Any]`
- **Purpose:** Update an existing project entry.
- **Called by:** HTTP PUT `/api/v1/profile/project/{pid}`
- **Flag:** 🟢 — clean

#### `delete_project_endpoint(pid: str) -> OkResponse`
- **Purpose:** Delete a project entry by ID.
- **Called by:** HTTP DELETE `/api/v1/profile/project/{pid}`
- **Flag:** 🟢 — clean

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:176` |

---

### `routes/scan.py`

**Purpose:** Scan lifecycle (start, stop), reevaluation lifecycle (start, stop), lead cleanup, free-source discovery scan, and a help chat endpoint. All endpoints prefixed `/api/v1`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | thread wrapper | 🟢 |
| `typing.Any` | stdlib | type hint | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `services.scanner` | local | scan_manager | 🟢 |
| `core.ws_manager.cm` | local | WS broadcast | 🟢 |
| `schemas.requests.HelpChatBody` | local | request body | 🟢 |
| `schemas.responses.*` (2 types) | local | response schemas | 🟢 |
| `services.job_targets._profile_for_discovery` | local | free sources scan | 🟣 COUPLED — imports private name |
| `services.scout._run_free_source_scan` | local | free sources scan | 🟣 COUPLED — imports private name |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `prefix="/api/v1"` | main.py include_router | 🟢 |

**Functions:**

#### `scan() -> StatusResponse`
- **Purpose:** Start a new job scan.
- **Called by:** HTTP POST `/api/v1/scan`
- **Calls:** `scanner.scan_manager.start_scan`
- **Flag:** 🟢 — clean delegation

#### `stop_scan() -> StatusResponse`
- **Purpose:** Stop the running scan.
- **Called by:** HTTP POST `/api/v1/scan/stop`
- **Calls:** `scanner.scan_manager.stop_scan`
- **Flag:** 🟢 — clean delegation

#### `reevaluate_jobs() -> StatusResponse`
- **Purpose:** Start reevaluation of all existing leads.
- **Called by:** HTTP POST `/api/v1/leads/reevaluate`
- **Calls:** `scanner.scan_manager.start_reevaluate`
- **Flag:** 🟢 — clean delegation

#### `stop_reevaluate_jobs() -> StatusResponse`
- **Purpose:** Stop the running reevaluation.
- **Called by:** HTTP POST `/api/v1/leads/reevaluate/stop`
- **Calls:** `scanner.scan_manager.stop_reevaluate`
- **Flag:** 🟢 — clean delegation

#### `cleanup_leads(dry_run: bool = False, limit: int = 1000) -> dict[str, Any]`
- **Purpose:** Scan and remove bad leads with optional dry-run, broadcasting progress via WS.
- **Called by:** HTTP POST `/api/v1/leads/cleanup`
- **Calls:** `cleanup_bad_leads`, `get_lead_by_id`, `cm.broadcast`
- **Side effects:** DB writes (if not dry_run), WS broadcasts
- **Hardcodes:** `limit=1000`, broadcasts first 100 items only
- **Flag:** 🔵 HARDCODED — `limit` default and WS batch limit (100) should be configurable

#### `free_sources_scan() -> FreeSourcesScanResponse`
- **Purpose:** Run a free-source discovery scan for leads from unconfigured public job sources.
- **Called by:** HTTP POST `/api/v1/free-sources/scan`
- **Calls:** `get_settings`, `get_profile`, `_profile_for_discovery`, `_run_free_source_scan`
- **Side effects:** DB reads, scraping (via service)
- **Flag:** 🟣 COUPLED — imports private names from two services modules

#### `help_chat(body: HelpChatBody) -> dict[str, Any]`
- **Purpose:** Ask a question to the help agent.
- **Called by:** HTTP POST `/api/v1/help/chat`
- **Calls:** `answer` (help_agent)
- **Side effects:** LLM call
- **Flag:** 🟣 COUPLED — exact duplicate of `misc.py:help_chat`. Due to registration order, this handler shadows misc's version. This is almost certainly a copy-paste error.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:177` |

---

### `routes/settings.py`

**Purpose:** Settings CRUD, API key validation probe, and job-targets management (get, update, delete). All endpoints prefixed `/api/v1`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | concurrent provider probes | 🟢 |
| `typing.Any` | stdlib | type hint | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.HTTPException` | 3rd-party | error handling | 🟢 |
| `config.settings as cfg_settings` | local | typed config access | 🟢 |
| `core.config_constants._sched` | local | ghost mode scheduler | 🟡 SUSPECT — imports scheduler singleton |
| `schemas.requests.*` (2 types) | local | request bodies | 🟢 |
| `schemas.responses.*` (2 types) | local | response schemas | 🟢 |
| `services.job_targets.*` (5 functions) | local | job-targets CRUD | 🟢 |
| `services.ghost._ghost_tick` | local | ghost mode tick function | 🟣 COUPLED — imports private name |
| `config.secrets.resolve_secret` | local | API key resolution | 🟢 |
| `services.provider_probe._sensitive` | local | sensitive key detection | 🟣 COUPLED — imports private name |
| `services.provider_probe._probe_provider_key` | local | provider key probing | 🟣 COUPLED — imports private name |
| `services.provider_probe._log_sensitive_deprecation` | local | key deprecation logging | 🟣 COUPLED — imports private name |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `prefix="/api/v1"` | main.py include_router | 🟢 |

**Functions:**

#### `get_cfg() -> dict[str, Any]`
- **Purpose:** Retrieve all settings with sensitive values masked.
- **Called by:** HTTP GET `/api/v1/settings`
- **Calls:** `get_settings`, `_sensitive`
- **Flag:** 🟢 — clean

#### `validate_settings() -> dict[str, Any]`
- **Purpose:** Probe all configured API providers for key validity.
- **Called by:** HTTP GET `/api/v1/settings/validate`
- **Calls:** `get_settings`, `resolve_secret`, `_probe_provider_key`
- **Hardcodes:** `"anthropic"`, `"gemini"`, `"openai"`, `"groq"` — provider list defined inline
- **Flag:** 🔵 HARDCODED — provider list duplicated from llm module

#### `save_cfg(body: SettingsBody) -> OkResponse`
- **Purpose:** Save settings with masked value preservation and auto-start ghost mode scheduler.
- **Called by:** HTTP POST `/api/v1/settings`
- **Calls:** `get_settings`, `save_settings`, `_sensitive`, `_log_sensitive_deprecation`, `_ghost_tick`, `_sched.add_job`
- **Side effects:** DB write, scheduler job addition
- **Hardcodes:** `"ghost_mode" == "true"` string comparison; `hours=6` interval
- **Flag:** ⚪ INCOMPLETE — ghost mode interval `hours=6` is hardcoded rather than read from `config.app.ghost_mode.interval_hours`; the ghost mode trigger mixes persistence and scheduling concerns

#### `get_job_targets_endpoint() -> JobTargetsResponse`
- **Purpose:** Retrieve configured job targets and blocked markers.
- **Called by:** HTTP GET `/api/v1/settings/job-targets`
- **Calls:** `get_job_targets`, `get_blocked_markers`
- **Flag:** 🟢 — clean

#### `update_job_targets(body: JobTargetsUpdateBody) -> JobTargetsResponse`
- **Purpose:** Replace job targets and/or blocked markers with validation.
- **Called by:** HTTP PUT `/api/v1/settings/job-targets`
- **Calls:** `validate_job_targets`, `validate_blocked_markers`, `get_job_targets`, `get_blocked_markers`, `save_job_targets`
- **Flag:** 🟢 — clean; validates before saving, partial updates supported

#### `clear_job_targets() -> JobTargetsResponse`
- **Purpose:** Clear all job targets and blocked markers.
- **Called by:** HTTP DELETE `/api/v1/settings/job-targets`
- **Calls:** `save_job_targets`
- **Flag:** 🟢 — clean

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:174` |

---

### `routes/ws.py`

**Purpose:** WebSocket endpoint for real-time event streaming and heartbeat. Single `/ws` endpoint with token-based auth.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | timeout handling | 🟢 |
| `json` | stdlib | message serialization | 🟢 |
| `time` | stdlib | uptime calculation | 🟢 |
| `datetime.*` | stdlib | timestamp | 🟢 |
| `fastapi.APIRouter` | 3rd-party | router creation | 🟢 |
| `fastapi.WebSocket` | 3rd-party | WS type | 🟢 |
| `fastapi.WebSocketDisconnect` | 3rd-party | disconnect handling | 🟢 |
| `core.config_constants._log` | local | logging | 🟢 |
| `core.config_constants._UP` | local | uptime start time | 🟢 |
| `core.config_constants._API_TOKEN` | local | auth token | 🟢 |
| `core.ws_manager.cm` | local | connection manager | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `router` | `APIRouter` | `tags=["ws"]` | main.py include_router | 🟢 |

**Functions:**

#### `_require_ws_token(ws: WebSocket) -> bool`
- **Purpose:** Auth guard for WebSocket routes; checks token via query param or Bearer header.
- **Called by:** `ws_endpoint`
- **Flag:** 🟢 — clean, consistent with main.py bearer middleware pattern

#### `ws_endpoint(ws: WebSocket)`
- **Purpose:** WebSocket handler that authenticates, accepts, streams heartbeats every 2s, and relays broadcast events until disconnect.
- **Called by:** WebSocket `/ws`
- **Calls:** `_require_ws_token`, `cm.add`, `cm.remove`, `ws.send_text`, `ws.receive_text`
- **Side effects:** WebSocket message I/O
- **Hardcodes:** `timeout=2.0` heartbeat interval
- **Flag:** 🔵 HARDCODED — 2.0s heartbeat timeout is baked in

**Exports:**

| Export | Known importers |
|--------|----------------|
| `router` | `backend/main.py:180` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🟣 COUPLED | `help_chat` duplicate route | `misc.py:132` + `scan.py:112` | Both register `POST /api/v1/help/chat`; scan's handler shadows misc's due to registration order — deferred (structural) |
| P1 | ✅ RESOLVED | `HTTPException` import | was `misc.py:9` | Removed — unused import |
| P1 | ✅ RESOLVED | `JSONResponse` import | was `misc.py:10` | Removed — unused import |
| P1 | 🟣 COUPLED | `_profile_for_discovery` import | `scan.py:12` | Imports private name from `services.job_targets` — deferred (structural) |
| P1 | 🟣 COUPLED | `_run_free_source_scan` import | `scan.py:13` | Imports private name from `services.scout` — deferred (structural) |
| P1 | 🟣 COUPLED | `_ghost_tick` import | `settings.py:12` | Imports private name from `services.ghost` |
| P1 | 🟣 COUPLED | `_sensitive` import | `settings.py:14` | Imports private name from `services.provider_probe` |
| P1 | 🟣 COUPLED | `_probe_provider_key` import | `settings.py:14` | Imports private name from `services.provider_probe` |
| P1 | 🟣 COUPLED | `_log_sensitive_deprecation` import | `settings.py:14` | Imports private name from `services.provider_probe` |
| P1 | ✅ RESOLVED | `50 * 1024 * 1024` | was `ingest.py:95` | Externalized to `config.app.upload_limits.max_linkedin_export_size` |
| P1 | ✅ RESOLVED | `"selectors_fetched_at": "0"` | was `actions.py:182` | Extracted to module constant `_SELECTORS_RESET_AT` |
| P1 | 🔵 HARDCODED | `"fresher"`, `"junior"` etc strings | `leads.py:38,91-94` | Seniority level strings duplicated in two places — domain data |
| P1 | 🔵 HARDCODED | Provider list inline | `settings.py:50` | Provider names duplicated from llm module |
| P2 | 🔵 HARDCODED | `"job"` kind filter | `leads.py:285` | Lead kind is baked in as a string literal |
| P2 | ✅ RESOLVED | 100 items WS broadcast cap | was `scan.py:81` | Externalized to `config.app.scan_broadcast.cleanup_broadcast_cap` |
| P2 | ✅ RESOLVED | Heartbeat 2.0s timeout | was `ws.py:49` | Externalized to `config.app.websocket.heartbeat_timeout` |
| P2 | ✅ RESOLVED | Ghost mode interval | was `settings.py:95` | Wired to `config.app.ghost_mode.interval_hours` |
| P2 | 🟡 SUSPECT | `save_lead` call with 20+ kwargs | `leads.py:288-314` | Brittle; should accept a lead dict |
| P3 | 🟢 CLEAN | Most route functions | various | Well-documented, correctly lazy-imported, consistent error handling |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `backend/main.py` — imports all 8 routers via `app.include_router`
- `backend/main.py:184-189` — backward-compatible re-exports for tests

**Outbound (this unit depends on others):**

| Unit | Direction | Files | Details |
|------|-----------|-------|---------|
| `db.client` | import | all except `__init__.py`, `ws.py` | Lazy imports throughout to avoid ~7s lancedb import cost at module load |
| `agents.*` | import | `actions.py`, `ingest.py`, `leads.py`, `misc.py`, `scan.py` | Lazy imports for per-request agent loading |
| `services.*` | import | `actions.py`, `leads.py`, `scan.py`, `settings.py` | Business logic: generator, scanner, job_targets, ghost, provider_probe |
| `core.config_constants` | import | `ingest.py`, `misc.py`, `ws.py`, `settings.py` | `_log`, `_UP`, `_API_TOKEN`, `_sched` singletons |
| `core.ws_manager` | import | `ingest.py`, `leads.py`, `scan.py`, `ws.py` | WebSocket connection manager broadcast |
| `config` | import | `misc.py`, `settings.py` | Typed settings access |
| `config.secrets` | import | `settings.py` | Resolve environment/DB secret for API keys |
| `schemas.*` | import | all route files | Request/response type schemas |
| `log_context` | import | `leads.py` | Correlation ID logging context |
| `graph` | import | `leads.py` | Pipeline LangGraph evaluator (lazy, ~1.6s import) |
| `llm` | import | `settings.py` | Key name mappings (lazy, ~7s import) |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `fastapi` | HTTP server framework | un-pinned (project dep) | 🟢 — standard |
| `fastapi.responses.*` | FileResponse, StreamingResponse, JSONResponse | un-pinned | 🟢 — standard |

---

## 6. First principles assessment

### `routes/__init__.py`

1. **Does this file need to exist?** Yes — Python package init for `from routes import ...` pattern used by `main.py`.
2. **Does it do what it claims?** Yes — it's an empty init.
3. **Is it the right place for this logic?** N/A — no logic.
4. **What would break if deleted?** All router imports in `main.py` would fail.

### `routes/actions.py`

1. **Does this file need to exist?** Yes — clear domain for lead actions (fire, preview, form read).
2. **Does it do what it claims?** Yes — all endpoints are action-oriented.
3. **Is it the right place for this logic?** Yes — action coordination belongs in the route layer.
4. **What would break if deleted?** Fire, form read, PDF download, identity, selectors refresh, and preview endpoints — all clients.

### `routes/ingest.py`

1. **Does this file need to exist?** Yes — ingestion from multiple sources is a coherent domain. But at 356 lines it's the second largest file.
2. **Does it do what it claims?** Yes — all endpoints ingest profile data.
3. **Is it the right place for this logic?** Partially — the file is large but each endpoint delegates to an agent. Boundary with `profile.py` is blurry (both do profile writes). Consider splitting portfolio ingestion to its own file.
4. **What would break if deleted?** All 6 ingestion endpoints + profile template endpoint.

### `routes/leads.py`

1. **Does this file need to exist?** Yes — lead CRUD and pipeline is the core domain.
2. **Does it do what it claims?** Yes — handles leads and pipeline, CSV export, follow-ups.
3. **Is it the right place for this logic?** Partially — at 404 lines, it's the largest file. `_annotate_job_lead` and `_versioned_assets` are helpers that belong in `services.scout` and `services.generator` respectively. The `run_pipeline` function embeds a nested async function which is appropriate but makes the function harder to test.
4. **What would break if deleted?** All lead CRUD, pipeline, CSV export, follow-up, and generation endpoints.

### `routes/misc.py`

1. **Does this file need to exist?** Partially — health, events, graph stats, template, and help chat are genuinely orthogonal. The name "misc" signals this. Consider splitting help chat into its own module or removing the duplicate in `scan.py`.
2. **Does it do what it claims?** Mostly — but `/api/v1/help/chat` is silently shadowed by `scan.py`'s duplicate.
3. **Is it the right place for this logic?** Partially — dead imports suggest this file was refactored; `HTTPException` and `JSONResponse` are unused.
4. **What would break if deleted?** Health check, events, graph stats, template CRUD, help chat.

### `routes/profile.py`

1. **Does this file need to exist?** Yes — clean CRUD boundary for profile sub-entities.
2. **Does it do what it claims?** Yes.
3. **Is it the right place for this logic?** Yes — validation on each endpoint is appropriate.
4. **What would break if deleted?** All profile CRUD endpoints (candidate, skills, experience, projects).

### `routes/scan.py`

1. **Does this file need to exist?** Yes — scan lifecycle is a coherent domain.
2. **Does it do what it claims?** Mostly — but the duplicate `help_chat` is concerning; likely a copy-paste leftover.
3. **Is it the right place for this logic?** Partially — imports private names (`_profile_for_discovery`, `_run_free_source_scan`) from services modules, bypassing the public API.
4. **What would break if deleted?** Scan start/stop, reevaluate, cleanup, free-sources scan. Help chat would still work via `misc.py`.

### `routes/settings.py`

1. **Does this file need to exist?** Yes — settings CRUD and job-targets are coherent.
2. **Does it do what it claims?** Yes.
3. **Is it the right place for this logic?** Partially — the ghost mode scheduler side effect in `save_cfg` mixes concerns. The provider probe in `validate_settings` could live in `services.provider_probe`.
4. **What would break if deleted?** Settings CRUD, key validation, job-targets CRUD.

### `routes/ws.py`

1. **Does this file need to exist?** Yes — single WebSocket endpoint with dedicated auth and heartbeat.
2. **Does it do what it claims?** Yes.
3. **Is it the right place for this logic?** Yes — clean, self-contained.
4. **What would break if deleted?** All real-time WebSocket event streaming. Tauri sidecar would lose heartbeat and event push.
