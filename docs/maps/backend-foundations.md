# Map: backend-foundations
**File:** `docs/maps/backend-foundations.md`
**Codebase path(s):** `backend/core/`, `backend/schemas/`, `backend/models/`
**Files in scope:** 8
**Total lines:** ~478
**Generated:** 2026-05-15

---

## 1. Unit summary

The backend-foundations unit provides the foundational layer for the entire Python backend: configuration constants/singletons (`core/config_constants.py`), the WebSocket connection manager (`core/ws_manager.py`), Pydantic request/response schema contracts (`schemas/requests.py`, `schemas/responses.py`), and compact internal data models for the ingestor agent (`models/schema.py`). Three of the eight files are empty `__init__.py` package markers. The non-empty files are actively imported by routes, services, agents, and tests across the backend, making this a high-traffic, low-ownership unit — many modules depend on it, but no single team owns all of it.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `backend/core/__init__.py` | 0 | Package marker for `core` | 🟢 CLEAN — standard namespace package |
| 2 | `backend/core/config_constants.py` | 21 | Module-level constants and shared singletons (scheduler, auth token, CORS regex, logger) | 🟢 CLEAN — well-scoped, actively consumed |
| 3 | `backend/core/ws_manager.py` | 92 | Thread-safe WebSocket connection manager with broadcast and dead-connection cleanup | 🟢 CLEAN — well-structured, widely used |
| 4 | `backend/schemas/__init__.py` | 0 | Package marker for `schemas` | 🟢 CLEAN — standard namespace package |
| 5 | `backend/schemas/requests.py` | 214 | Pydantic request body models for all API endpoints | 🟢 CLEAN — comprehensive, well-typed |
| 6 | `backend/schemas/responses.py` | 117 | Pydantic response models for all API endpoints | 🟢 CLEAN — complete coverage |
| 7 | `backend/models/__init__.py` | 0 | Package marker for `models` | 🟢 CLEAN — standard namespace package |
| 8 | `backend/models/schema.py` | 34 | Compact Pydantic models for ingestor agent internal representation | 🟡 SUSPECT — cryptic single-letter class names, field `s` used ambiguously |

---

## 3. Detailed breakdown

### `backend/core/__init__.py`

**Purpose:** Makes `core` a Python package. Empty — no re-exports, no logic.

**Imports:** None.

**Module-level constants & state:** None.

**Classes:** None.

**Functions:** None.

**Exports:** None (empty file).

---

### `backend/core/config_constants.py`

**Purpose:** Central home for module-level constants and singletons that must be initialized at import time (not config-system values). Hosts the scheduler, auth token, bearer scheme, CORS origin regex, uptime timestamp, and a shared logger instance. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import secrets` | stdlib | yes — `secrets.token_hex(32)` | 🟢 — standard |
| `import time` | stdlib | yes — `time.monotonic()` | 🟢 — standard |
| `from apscheduler.schedulers.asyncio import AsyncIOScheduler` | 3rd-party | yes — `_sched = AsyncIOScheduler()` | 🟢 — standard |
| `from fastapi.security import HTTPBearer` | 3rd-party | yes — `_bearer = HTTPBearer(auto_error=False)` | 🟢 — standard |
| `from logger import get_logger` | local | yes — `get_logger(__name__)` | 🟢 — consistent with rest of backend |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | `get_logger(__name__)` | scout, scanner, provider_probe, ghost, routes/ws, main, routes/misc, routes/ingest | 🟢 CLEAN — active usage across 8 modules |
| `_UP` | float | `time.monotonic()` | routes/ws.py (`/health`), routes/misc.py | 🟢 CLEAN — properly scoped |
| `_sched` | AsyncIOScheduler | `AsyncIOScheduler()` | main.py (`lifespan`), routes/settings.py | 🟢 CLEAN — global scheduler instance |
| `_API_TOKEN` | str | `secrets.token_hex(32)` | main.py (emit + verify), routes/ws.py | 🟢 CLEAN — auto-generated per-run |
| `_LOCAL_ORIGIN_RE` | str | regex string | main.py (`CORSMiddleware`) | 🟢 CLEAN — local-dev default, not a config leak |
| `_bearer` | HTTPBearer | `HTTPBearer(auto_error=False)` | main.py (auth middleware) | 🟢 CLEAN — standard FastAPI pattern |

**Classes:** None.

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `_log` | `services/scout.py`, `services/scanner.py`, `services/provider_probe.py`, `services/ghost.py`, `routes/ws.py`, `main.py`, `routes/misc.py`, `routes/ingest.py` |
| `_UP` | `routes/ws.py`, `routes/misc.py` |
| `_sched` | `main.py`, `routes/settings.py` |
| `_API_TOKEN` | `main.py`, `routes/ws.py` |
| `_LOCAL_ORIGIN_RE` | `main.py` |
| `_bearer` | `main.py` |

---

### `backend/core/ws_manager.py`

**Purpose:** WebSocket connection manager that maintains a thread-safe registry of active connections, broadcasts JSON messages to all clients, persists agent events to the database, and auto-cleans stale connections. Name matches content well.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import asyncio` | stdlib | yes — `asyncio.Lock()`, `asyncio.to_thread()` | 🟢 — standard |
| `import json` | stdlib | yes — `json.dumps(msg)` | 🟢 — standard |
| `from fastapi import WebSocket` | 3rd-party | yes — type hint in `_CM` methods | 🟢 — standard |
| `from logger import get_logger` | local | yes — `get_logger(__name__)` | 🟢 — consistent with backend convention |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | `get_logger(__name__)` | `_CM.broadcast()` | 🟢 CLEAN |
| `cm` | `_CM` | `_CM()` | 9 modules (scout, scanner, job_targets, ghost, generator, routes/ws, routes/scan, routes/ingest, routes/leads) | 🟢 CLEAN — connection manager singleton |

**Classes:**

#### `_CM`
- **Inherits from:** None
- **Purpose:** Thread-safe connection registry that manages WebSocket connections and broadcasts messages
- **Still needed:** yes
- **Flag:** 🟢 CLEAN — well-designed, appropriate locking

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `__init__` | self | None | Initialize empty registry + asyncio lock | 🟢 CLEAN |
| `add` | self, ws: WebSocket | None | Register a new connection (thread-safe) | 🟢 CLEAN |
| `remove` | self, ws: WebSocket | None | Unregister a connection (thread-safe) | 🟢 CLEAN |
| `broadcast` | self, msg: dict | None | Send JSON to all clients, persist agent events, remove dead connections | 🟣 COUPLED — lazy-imports `db.client.record_event` inside method |

**Functions:**

#### `_agent_event_action(msg: dict) -> str`
- **Purpose:** Format an agent event dict into a compact "event: detail" action string
- **Called by:** `_CM.broadcast()` (internal), `main.py:184` (lazy import for event recording)
- **Calls:** `str(msg.get(...))` — no local callees
- **Side effects:** none
- **Hardcodes:** fallback string `"agent"` when event key missing
- **Flag:** 🟢 CLEAN — simple utility function

**Exports:**

| Export | Known importers |
|--------|----------------|
| `cm` | `services/scout.py`, `services/job_targets.py`, `services/scanner.py`, `routes/ws.py`, `routes/scan.py`, `services/ghost.py`, `services/generator.py`, `routes/leads.py`, `routes/ingest.py` |
| `_CM` | `tests/test_websocket.py` (direct import for testing) |
| `_agent_event_action` | `main.py` (lazy import) |

---

### `backend/schemas/__init__.py`

**Purpose:** Makes `schemas` a Python package. Empty — no re-exports, no logic.

**Imports:** None.

**Module-level constants & state:** None.

**Classes:** None.

**Functions:** None.

**Exports:** None.

---

### `backend/schemas/requests.py`

**Purpose:** Defines all Pydantic request body models for the backend REST API. Covers lead management, settings, help chat, profile management (manual editing + import), GitHub/portfolio ingestion, form auto-fill, and job target configuration. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from typing import Literal` | stdlib | yes — `LeadStatus`, `FeedbackBody.feedback`, etc. | 🟢 — standard |
| `from pydantic import BaseModel, ConfigDict, Field, model_validator` | 3rd-party | yes — all used | 🟢 — standard |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `LeadStatus` | Literal type | 14 string options | `StatusBody.status` | 🟢 CLEAN — comprehensive status enum |

**Classes:**

#### `StrictBody(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Base model that rejects extra fields (`extra="forbid"`)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN — consistent usage pattern

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(inherited)* | — | — | — | 🟢 |

#### `StatusBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Update a lead's status
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `FeedbackBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Submit feedback on a lead (good/trash/duplicate/etc.)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `FollowupBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Schedule a follow-up reminder (days field)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ManualLeadBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Manually enter a lead by text and URL
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `HelpMessage(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** A single message (user/assistant) in help chat
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `HelpChatBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Send a help chat message with history
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `TemplateBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Update the tailoring template
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `CandidateBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Candidate name and summary (profile editing)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `SkillBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** A skill entry with id, name, category
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ExperienceBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** An experience entry (role, company, period, description)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProjectBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** A project entry (title, stack, repo, impact)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `SettingsBody(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Flexible settings update body — allows extra keys with validated length/type
- **Still needed:** yes
- **Flag:** 🟡 SUSPECT — custom `model_validator` duplicates Pydantic's built-in type enforcement; loose `extra="allow"` defeats schema guarantees

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `_validate_extra_settings` | self | self | validates length and type of extra keys | 🟡 SUSPECT — manual validation reinvention |

#### `GithubIngestBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Import a GitHub profile (username, optional token, max repos)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `PortfolioIngestBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Import a portfolio/personal website with optional auto-write
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileSkill(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** A skill within a profile import (name + category)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileExperience(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** An experience entry within a profile import
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileProject(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** A project entry within a profile import
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileEntry(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** A generic list entry (education, certification, achievement) within a profile import
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileIdentity(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Identity fields within a profile import (email, phone, URLs, city)
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileCandidate(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Candidate name and summary within a profile import
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `ProfileImportBody(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Full candidate profile import — aggregates all sub-models
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

#### `FormReadBody(StrictBody)`
- **Inherits from:** `StrictBody`
- **Purpose:** Read a form via auto-fill (URL input)
- **Still needed:** unclear
- **Flag:** 🟡 SUSPECT — no confirmed endpoint consumer in scope; purpose ("read a form") is vague

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟡 |

#### `JobTargetsUpdateBody(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Update job targets and blocked markers
- **Still needed:** yes
- **Flag:** 🟢 CLEAN — added as part of externalize-job-targets phase

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟢 |

**Exports:**

| Export | Known importers |
|--------|----------------|
| `LeadStatus` | (type alias, used within file + importers of `StatusBody`) |
| `StrictBody` | (base class, used within file) |
| `StatusBody` | `routes/leads.py` |
| `FeedbackBody` | `main.py` |
| `FollowupBody` | — (check cross-ref) |
| `ManualLeadBody` | — (check cross-ref) |
| `HelpMessage`, `HelpChatBody` | `routes/scan.py`, `routes/misc.py` |
| `TemplateBody` | `routes/misc.py` |
| `CandidateBody`, `SkillBody`, `ExperienceBody`, `ProjectBody` | `routes/profile.py` |
| `SettingsBody` | `routes/settings.py` |
| `GithubIngestBody` | `routes/ingest.py` |
| `PortfolioIngestBody` | `routes/ingest.py` |
| `ProfileImportBody` | `main.py` |
| `FormReadBody` | `routes/actions.py` |
| `JobTargetsUpdateBody` | `routes/settings.py` |

---

### `backend/schemas/responses.py`

**Purpose:** Defines all Pydantic response models for the backend REST API. Covers health, status, identity, scraping, lead generation, pipeline, ingestion, and job targets. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes — all models | 🟢 — standard |
| `from typing import Any` | stdlib | yes — `dict[str, Any]` in several models | 🟢 — standard |

**Module-level constants & state:** None.

**Classes:**

#### `OkResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Generic `{"ok": bool}` success response
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `StatusResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Generic `{"status": str}` response
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `HealthResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** `/health` endpoint response with uptime, timestamp, log level, dependency status
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `TemplateResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response containing the tailoring template
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `FireResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response for triggering a lead generation action
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `IdentityResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response containing user identity information
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `SelectorsRefreshResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response after refreshing scraper selectors
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `FreeSourcesScanResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response for a free-sources scan result
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `LeadGenerateResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response after generating a single lead
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `PipelineRunResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response after triggering a pipeline run
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `IngestLinkedinResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response after importing a LinkedIn profile
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `IngestGithubResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response after importing a GitHub profile
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `IngestProfileResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response after importing a portfolio/personal website
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `JobTargetsResponse(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Response containing current job targets and blocked markers
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `OkResponse` | `routes/profile.py`, `routes/misc.py`, `routes/leads.py`, `routes/settings.py` |
| `StatusResponse` | `routes/scan.py` |
| `HealthResponse` | `routes/misc.py` |
| `TemplateResponse` | `routes/misc.py` |
| `FireResponse`, `IdentityResponse`, `SelectorsRefreshResponse` | `routes/actions.py` |
| `FreeSourcesScanResponse` | `routes/scan.py` |
| `LeadGenerateResponse`, `PipelineRunResponse` | `routes/leads.py` |
| `IngestLinkedinResponse`, `IngestGithubResponse`, `IngestProfileResponse` | `routes/ingest.py` |
| `JobTargetsResponse` | `routes/settings.py` |

---

### `backend/models/__init__.py`

**Purpose:** Makes `models` a Python package. Empty — no re-exports, no logic.

**Imports:** None.

**Module-level constants & state:** None.

**Classes:** None.

**Functions:** None.

**Exports:** None.

---

### `backend/models/schema.py`

**Purpose:** Compact Pydantic models representing skills, experience, projects, and the candidate aggregate — used internally by the ingestor agent. The single-letter class names (`S`, `E`, `P`, `C`) are terse to the point of being cryptic.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 — standard |
| `from typing import List, Optional` | stdlib | yes | 🟢 — standard |

**Module-level constants & state:** None.

**Classes:**

#### `S(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** A skill with name (`n`) and category (`cat`)
- **Still needed:** yes
- **Flag:** 🟡 SUSPECT — single-letter name `S` harms readability

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟡 |

#### `E(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** An experience entry with role, company, period, description, and associated skills (`s`)
- **Still needed:** yes
- **Flag:** 🟡 SUSPECT — single-letter name `E`; field `s` ambiguous (skills list vs. string)

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟡 |

#### `P(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** A project entry with title, stack, repo, impact, and associated skills (`s`)
- **Still needed:** yes
- **Flag:** 🟡 SUSPECT — single-letter name `P`; field `s` reused from `E` with same meaning but no shared base

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟡 |

#### `C(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** The candidate aggregate — wraps name, summary, skills, experience, projects, education, certifications, achievements
- **Still needed:** yes
- **Flag:** 🟡 SUSPECT — single-letter name `C`; education/certifications/achievements are `list[str]` with no structured model

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| *(none)* | — | — | — | 🟡 |

**Exports:**

| Export | Known importers |
|--------|----------------|
| `S` | `agents/ingestor.py` |
| `E` | `agents/ingestor.py` |
| `P` | `agents/ingestor.py` |
| `C` | `agents/ingestor.py` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P2 | 🟣 COUPLED | `_CM.broadcast` lazy-imports `db.client.record_event` | `core/ws_manager.py:72` | Runtime dependency on db module; silent failure on error |
| P2 | 🟡 SUSPECT | `SettingsBody._validate_extra_settings` | `schemas/requests.py:115` | Manual validation reinvention; Pydantic can enforce types |
| P2 | 🟡 SUSPECT | `FormReadBody` | `schemas/requests.py:204` | No confirmed endpoint consumer; purpose vague |
| P3 | 🟡 SUSPECT | Model names `S`, `E`, `P`, `C` | `models/schema.py:5-27` | Single-letter class names harm readability |
| P3 | 🟡 SUSPECT | Field `s` in `E` and `P` | `models/schema.py:14,23` | Ambiguous field name; no docstring clarifying "skills" |
| P3 | 🟡 SUSPECT | `C.education`, `C.certifications`, `C.achievements` as `list[str]` | `models/schema.py:32-34` | Inconsistent with structured models for skills/experience/projects |
| P3 | 🟢 CLEAN | All other items | — | Well-scoped, typed, and actively consumed |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- **`backend-foundations` → routes** (all route modules import schemas or core constants)
- **`backend-foundations` → services** (scout, scanner, ghost, generator, job_targets import `cm` and/or `_log`)
- **`backend-foundations` → agents** (`agents/ingestor.py` imports models/schema)
- **`backend-foundations` → tests** (`tests/test_websocket.py` imports `_CM`)
- **`backend-foundations` → main.py** (imports from both core modules)

**Outbound (this unit depends on others):**
- **config_constants.py → logger** (`from logger import get_logger`)
- **ws_manager.py → logger** (`from logger import get_logger`)
- **ws_manager.py → db.client** (lazy import `record_event` — one-direction runtime dep)
- **models/schema.py → (none besides pydantic)**

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `apscheduler` | Background task scheduling (`_sched`) | implicit (in project deps) | 🟢 — standard usage |
| `fastapi` | WebSocket type + HTTPBearer | >=0.136.1 (project-level) | 🟢 — standard usage |
| `pydantic` | All request/response/data models | project-level | 🟢 — standard usage |

---

## 6. First principles assessment

### `backend/core/__init__.py`
1. **Does this file need to exist?** Yes — makes `core` a package.
2. **Does it do what it claims?** Yes — it's an empty init.
3. **Is it the right place for this logic?** N/A.
4. **What would break if deleted?** All `from core.xxx import` statements would fail.

### `backend/core/config_constants.py`
1. **Does this file need to exist?** Yes — centralizes import-time constants and singletons that don't belong in the config system.
2. **Does it do what it claims?** Yes — docstring accurately describes the purpose.
3. **Is it the right place for this logic?** Yes — keeps singletons (scheduler, bearer auth) out of `main.py` and avoids circular imports.
4. **What would break if deleted?** `main.py`, 4 services, 3 route modules — all fail to boot.

### `backend/core/ws_manager.py`
1. **Does this file need to exist?** Yes — encapsulates WebSocket connection management cleanly.
2. **Does it do what it claims?** Yes — docstring accurately describes thread-safe broadcast with cleanup.
3. **Is it the right place for this logic?** Yes — single-responsibility connection manager.
4. **What would break if deleted?** 9 modules across services, routes, and tests — real-time event broadcasting would stop.

### `backend/schemas/__init__.py`
1. **Does this file need to exist?** Yes — makes `schemas` a package.
2. **Does it do what it claims?** Yes — empty init.
3. **Is it the right place for this logic?** N/A.
4. **What would break if deleted?** All `from schemas.xxx import` statements would fail.

### `backend/schemas/requests.py`
1. **Does this file need to exist?** Yes — single source of truth for API request contracts.
2. **Does it do what it claims?** Yes — defines all request body models.
3. **Is it the right place for this logic?** Yes — co-locates related schemas; alternatively, could be split per route module.
4. **What would break if deleted?** Every route handler that accepts a request body would fail.

### `backend/schemas/responses.py`
1. **Does this file need to exist?** Yes — single source of truth for API response contracts.
2. **Does it do what it claims?** Yes — defines all response models.
3. **Is it the right place for this logic?** Yes — co-locates with requests; alternative is inline `response_model=` dicts.
4. **What would break if deleted?** Every route handler that returns a typed response would fail.

### `backend/models/__init__.py`
1. **Does this file need to exist?** Yes — makes `models` a package.
2. **Does it do what it claims?** Yes — empty init.
3. **Is it the right place for this logic?** N/A.
4. **What would break if deleted?** All `from models.xxx import` statements would fail.

### `backend/models/schema.py`
1. **Does this file need to exist?** Yes — provides internal representation models for the ingestor agent.
2. **Does it do what it claims?** Partially — implements the aggregate, but single-letter names and ambiguous field `s` obscure intent.
3. **Is it the right place for this logic?** Yes — `models/` is the natural home for data models, though the overlap with `schemas/requests.py` profile models is notable and could be consolidated.
4. **What would break if deleted?** `agents/ingestor.py` — cannot parse or construct candidate profiles.
