# Subagent Template — Codebase Unit Map

---

## Unit assignment

```
# Map: backend-db
**File:** `docs/maps/backend-db.md`
**Codebase path(s):** `backend/db/`
**Files in scope:** 2 (`__init__.py`, `client.py`)
**Total lines:** ~1607 (was 1641; -34 lines resolved 2026-05-15)
**Generated:** 2026-05-15
```

---

## 1. Unit summary

The `backend/db/` unit is the data access layer for the entire JustHireMe application. It owns all persistent state across three storage engines: SQLite (leads CRM, events, settings, profile snapshots), Kuzu (graph database for candidate profile entities and relationships), and LanceDB (vector store for skill and project embeddings). Every other backend unit — routes, services, agents, config (`secrets.py`), and the graph workflow — imports from `db.client`. The unit has a circular-ish dependency on `backend/config/` (it imports `settings` for the data directory at module level). The `__init__.py` is empty, making `client.py` a 1641-line monolith.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `backend/db/__init__.py` | 0 | Empty — exists only for package resolution | 🟢 |
| 2 | `backend/db/client.py` | 1607 | Multi-engine data access: SQLite, Kuzu, LanceDB | 🟣 COUPLED — three DBs in one file, module-level side effects, circular dep with config |

---

## 3. Detailed breakdown

### `backend/db/client.py`

**Purpose:** Single-file data-access megamodule. Owns SQLite schema/migration for the leads CRM, Kuzu schema/migration for the candidate graph, LanceDB schema management for vector embeddings, and all CRUD operations across all three. The name "client" is misleading — it is not a client abstraction but a flat collection of functions with module-level initialization side effects.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import os` | stdlib | `data_base`, `_ensure_dir`, `_read_pdf_text`, `_delete_vec_rows` | 🟢 |
| `import sys` | stdlib | `data_base` | 🟢 |
| `import sqlite3 as _sq` | stdlib | `get_sql_connection` | 🟢 |
| `import json` | stdlib | `save_lead`, `save_asset_package`, `save_contact_lookup`, `recompute_learning_scores`, `_json_list`, `_json_dumps_list`, `_json_dict`, `_normal_profile`, `_save_profile_snapshot` | 🟢 |
| `from datetime import UTC, datetime, timedelta` | stdlib | `_utc_timestamp`, `update_lead_followup` | 🟢 |
| `from logger import get_logger` | local | `_log` at module level | 🟢 |
| `try: import kuzu` | 3rd-party | `db`, `conn`, `_init`, `graph_counts`, `_read_profile_from_graph`, all Kuzu CRUD functions | 🟢 — optional dep, wrapped in try/except |
| `try: import lancedb` | 3rd-party | `vec` at module level | 🟢 — optional dep, wrapped in try/except |
| `from config import settings` | local | `data_base` (inside function body) | 🟣 COUPLED — `db.client` depends on `config` which depends on `db.client` (via `secrets.py`) creating potential circular import at module level |
| `from kuzu import Connection` | 3rd-party | Inside several Kuzu CRUD functions (local import) | 🟣 COUPLED — imported locally in 8+ functions, would break if Kuzu is unavailable (guarded by `graph_available()` pattern but functions don't check) |
| `from agents.feedback_ranker import apply_feedback_learning` | local | `rank_lead_by_feedback`, `recompute_learning_scores` | 🟣 COUPLED — `db.client` depends on `agents` module |
| `from agents.ingestor import _emb` | local | `_add_skill_vec`, `_add_project_vec` | 🟣 COUPLED — `db.client` depends on `agents.ingestor` for embedding function |
| `from pypdf import PdfReader` | 3rd-party | `_read_pdf_text` | 🟢 — lazy local import |
| `import html`, `import re` | stdlib | `_cleanup_text`, `_without_learning_suffix`, `_contact_from_text`, `_h` | 🟢 |
| `import hashlib` | stdlib | `_h`, `update_candidate` | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_KUZU_IMPORT_ERROR` | str | `""` or error msg from try/except | `_init` guard, `_GRAPH_ERROR` | 🟢 |
| `_LANCEDB_IMPORT_ERROR` | str | `""` or error msg from try/except | `vec` initialization guard | 🟢 |
| `_log` | Logger | `get_logger(__name__)` | Throughout file | 🟢 |
| `_b` (first assign) | str | result of `data_base()` | — | ✅ RESOLVED — premature `_g`, `_v`, `sql` computation removed; `sql` now computed after `_ensure_dir` |
| `_g` | str | `os.path.join(_b, "graph")` | `kuzu.Database()` | 🟢 |
| `_v` | str | `os.path.join(_b, "vector")` | `lancedb.connect()` | 🟢 |
| `sql` | str | `os.path.join(_b, "crm.db")` | `get_sql_connection`, exported to `agents/generator.py` and `e2e/manval/run_live_fire.py` | ✅ RESOLVED — now computed after `_ensure_dir`, uses ensured path |
| `_b` (second assign) | str | result of `_ensure_dir(data_base())` | `_g`, `_v`, `sql`, data directory for all stores | 🟢 |
| `_GRAPH_ERROR` | str | `""` or error msg | — | 🟡 `graph_error()` removed; `_GRAPH_ERROR` still used internally for warning log |
| `db` | kuzu.Database / None | `kuzu.Database(_g)` or None | `conn`, `graph_counts`, all graph CRUD, `_read_profile_from_graph` | 🟢 |
| `conn` | kuzu.Connection / None | `kuzu.Connection(db)` or None | `_init`, `graph_counts` | 🟢 — `graph_available()` removed |
| `vec` | lancedb.LanceDBConnection / _NullVectorStore | `lancedb.connect(_v)` or `_NullVectorStore()` | `_delete_vec_rows`, `_add_skill_vec`, `_add_project_vec`, exported to `agents/ingestor.py` and `agents/semantic.py` | 🟢 |
| `_LEAD_SELECT_COLUMNS` | str | long comma-separated column list | `get_all_leads`, `get_job_leads_for_evaluation`, `cleanup_bad_leads`, `recompute_learning_scores`, `get_lead_by_id`, `get_due_followups` | 🔵 HARDCODED — 38-column list must be kept in sync with schema |
| `_PROFILE_SNAPSHOT_KEY` | str | `"profile_snapshot_json"` | `_load_profile_snapshot`, `_save_profile_snapshot` | 🟢 |

**Classes:**

#### `_NullVectorStore`
- **Inherits from:** None
- **Purpose:** No-op fallback so profile CRUD never fails when LanceDB is unavailable
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `list_tables` | self | `[]` | No-op table listing | 🟢 |
| `create_table` | self, `*_args`, `**_kwargs` | None | No-op table creation | 🟢 |
| `open_table` | self, `*_args`, `**_kwargs` | self | Returns self as no-op table | 🟢 |
| `add` | self, `*_args`, `**_kwargs` | None | No-op add | 🟢 |

**Functions:**

#### `data_base() -> str`
- **Purpose:** Resolves the app data directory from env vars or platform defaults
- **Called by:** module-level line 41 (first `_b` assign), module-level line 84 (via `_ensure_dir(data_base())`)
- **Calls:** `os.environ.get`, `os.path.join`
- **Side effects:** env var reads, no writes
- **Hardcodes:** `"JustHireMe"` app folder name, default fallback paths
- **Flag:** 🟢 — straightforward, but 🔵 HARDCODED app folder name should be in settings

#### `_utc_timestamp(offset: timedelta | None = None) -> str`
- **Purpose:** Generates ISO-8601 UTC timestamp with Z suffix
- **Called by:** `save_lead_feedback`, `update_lead_followup`, `get_due_followups`
- **Calls:** `datetime.now`, `timedelta`
- **Side effects:** none
- **Flag:** 🟢

#### `_ensure_dir(path: str) -> str`
- **Purpose:** Creates directory if missing, falls back to `{path}_store` on failure
- **Called by:** module-level line 84 and 86 (second `_b`, `_v`)
- **Calls:** `os.makedirs`
- **Side effects:** Filesystem directory creation
- **Flag:** 🟢 — sensible fallback pattern

#### `_init()`
- **Purpose:** Creates Kuzu node/rel tables if they don't exist
- **Called by:** module-level line 131 (`_init()`)
- **Calls:** `conn.execute` with 12 CREATE statements
- **Side effects:** Kuzu schema mutation at module load
- **Hardcodes:** All 9 node table schemas and 7 rel table schemas, table names, property names, and types
- **Flag:** 🔵 HARDCODED — all table names and schemas are baked in; 🟣 COUPLED — runs at module level, assumes Kuzu is available

#### `graph_available() -> bool` — ✅ REMOVED
- **Was:** Returns whether the Kuzu graph store is operational
- **Status:** Deleted — never imported or called anywhere

#### `graph_error() -> str` — ✅ REMOVED
- **Was:** Returns the graph initialization error message
- **Status:** Deleted — never imported or called anywhere

#### `graph_counts() -> dict`
- **Purpose:** Returns approximate node counts per entity type from Kuzu
- **Called by:** `routes/misc.py` line 102
- **Calls:** `conn.execute` with MATCH/RETURN count queries
- **Side effects:** Kuzu queries
- **Hardcodes:** 5 node table names
- **Flag:** 🟢

#### `get_sql_connection()`
- **Purpose:** Returns a SQLite connection with WAL journaling, foreign keys, and 5s busy timeout
- **Called by:** Every SQLite operation function in the file, `agents/generator.py`
- **Calls:** `_sq.connect(sql)`, pragma executions
- **Side effects:** Opens a new SQLite connection each call (connection-per-operation pattern)
- **Flag:** 🟡 SUSPECT — connection-per-call pattern could be pooled; WAL mode is correct but no connection reuse

#### `_init_sql()`
- **Purpose:** Creates SQLite tables (leads, events, settings) and runs column migration
- **Called by:** module-level line 242
- **Calls:** `get_sql_connection`, `c.executescript`, `c.execute` in migration loop
- **Side effects:** SQLite schema mutation at module load
- **Hardcodes:** All table schemas, column definitions, migration column list
- **Flag:** 🟣 COUPLED — runs at module level; ⚪ INCOMPLETE — duplicate `resume_version` migration on lines 228 and 234-238 (the second block is redundant since the first loop on line 228 already adds `resume_version`)

#### `record_event(job_id: str | None, action: str)`
- **Purpose:** Inserts a row into the events table
- **Called by:** `core/ws_manager.py`
- **Calls:** `get_sql_connection`, `c.execute`, `c.commit`, `c.close`
- **Side effects:** SQLite INSERT
- **Hardcodes:** truncation limits (160, 1000)
- **Flag:** 🟢

#### `url_exists(jid: str) -> bool`
- **Purpose:** Checks if a lead with given job_id exists
- **Called by:** `agents/scout.py`, `agents/x_scout.py`, `agents/free_scout.py`
- **Calls:** `get_sql_connection`, `c.execute`, `c.close`
- **Flag:** 🟢

#### `save_lead(jid, t, co, u, plat, desc, kind, budget, ...)`
- **Purpose:** Inserts a new lead with all optional signal fields
- **Called by:** `agents/scout.py`, `agents/x_scout.py`, `agents/free_scout.py`, `routes/leads.py`, `e2e/manval/run_live_fire.py`
- **Calls:** `rank_lead_by_feedback`, `get_sql_connection`, `_json_dumps_list`, `json.dumps`
- **Side effects:** SQLite INSERT
- **Flag:** 🟢 — but function has 17 parameters (could be refactored to accept a lead dict)

#### `update_lead_score(jid: str, s: int, r: str, match_points, gaps, preserve_status)`
- **Purpose:** Updates a lead's score and status based on evaluation
- **Called by:** `services/scanner.py`, `routes/leads.py`, `graph/__init__.py`, `e2e/manval/run_live_fire.py`
- **Calls:** `get_sql_connection`, `_json_dumps_list`
- **Side effects:** SQLite UPDATE + INSERT event
- **Hardcodes:** score thresholds (76), status values ("tailoring", "discarded", "matched")
- **Flag:** 🔵 HARDCODED — score thresholds should be configurable

#### `save_asset_path(jid: str, path: str)`
- **Purpose:** Updates lead status to 'approved' and records asset path
- **Called by:** `e2e/manval/run_live_fire.py`
- **Calls:** `get_sql_connection`, `c.execute`, `c.commit`, `c.close`
- **Flag:** 🟡 SUSPECT — largely superseded by `save_asset_package` which handles both resume and cover letter paths

#### `save_asset_package(jid, resume_path, cover_letter_path, selected_projects, keyword_coverage)`
- **Purpose:** Saves resume + cover letter paths, selected projects, and keyword coverage metadata
- **Called by:** `services/generator.py`, `services/ghost.py`, `graph/__init__.py`
- **Calls:** `get_sql_connection`, `json.dumps`, `_json_dict`
- **Side effects:** SQLite UPDATE + INSERT event
- **Flag:** 🟢

#### `save_contact_lookup(jid: str, contact_lookup: dict | None)`
- **Purpose:** Stores contact lookup results in source_meta JSON
- **Called by:** `services/generator.py`
- **Calls:** `get_sql_connection`, `_json_dict`, `json.dumps`
- **Side effects:** SQLite UPDATE + INSERT event
- **Flag:** 🟢

#### `mark_applied(jid: str)`
- **Purpose:** Sets lead status to 'applied' and records event
- **Called by:** `services/generator.py`, `services/ghost.py`, `e2e/manval/run_live_fire.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Side effects:** SQLite UPDATE + INSERT event
- **Flag:** 🟢

#### `get_all_leads() -> list`
- **Purpose:** Returns all leads ordered by created_at DESC
- **Called by:** `routes/leads.py`
- **Calls:** `get_sql_connection`, `_LEAD_SELECT_COLUMNS`, `_lead_row_dict`
- **Flag:** 🟢

#### `_lead_row_dict(r) -> dict`
- **Purpose:** Converts a SQLite row tuple to a dict with proper parsing of JSON fields
- **Called by:** `get_all_leads`, `get_job_leads_for_evaluation`, `cleanup_bad_leads`, `recompute_learning_scores`, `get_lead_by_id`, `get_due_followups`
- **Calls:** `_json_dict`, `_json_list`
- **Flag:** 🟢 — but index-based tuple access (r[0]..r[38]) is fragile, depends on column order matching `_LEAD_SELECT_COLUMNS`

#### `get_all_freelance_leads() -> list` — ✅ REMOVED
- **Was:** Returns all freelance/gig leads
- **Status:** Deleted — never imported or called anywhere

#### `get_job_leads_for_evaluation() -> list`
- **Purpose:** Returns job-type leads (not freelance) for evaluation
- **Called by:** `services/scanner.py`
- **Calls:** `get_sql_connection`, `_lead_row_dict`
- **Flag:** 🟢

#### `_json_list(s: str) -> list`
- **Purpose:** Safely parses a JSON string to list, with fallback to comma-split
- **Called by:** `_lead_row_dict`, `get_feedback_training_examples`, `get_lead_for_fire`, `get_lead_by_id`
- **Flag:** 🟢

#### `_json_dumps_list(items: list | None) -> str`
- **Purpose:** Safely serializes list to JSON string
- **Called by:** `save_lead`, `update_lead_score`
- **Flag:** 🟢

#### `_json_dict(s: str) -> dict`
- **Purpose:** Safely parses JSON string to dict
- **Called by:** `save_asset_package`, `save_contact_lookup`, `_lead_row_dict`, `get_feedback_training_examples`
- **Flag:** 🟢

#### `_cleanup_text(lead: dict) -> str`
- **Purpose:** Strips HTML tags from lead text fields
- **Called by:** `lead_cleanup_reasons`, `_looks_like_cleanup_hn_job`
- **Calls:** `html.unescape`, `re.sub`
- **Hardcodes:** list of 7 lead fields to concatenate
- **Flag:** 🟢

#### `_looks_like_cleanup_hn_job(text: str) -> bool`
- **Purpose:** Heuristic detection of HN job postings vs discussion threads
- **Called by:** `lead_cleanup_reasons`
- **Calls:** `_cleanup_text`
- **Hardcodes:** Role terms list, hiring terms list, minimum text length (80)
- **Flag:** 🟢 — but hardcoded term lists could be configurable

#### `lead_cleanup_reasons(lead: dict) -> list[str]`
- **Purpose:** Returns list of reasons a lead should be discarded
- **Called by:** `cleanup_bad_leads`, `tests/test_regressions.py`
- **Calls:** `_cleanup_text`, `_looks_like_cleanup_hn_job`
- **Flag:** 🟢

#### `cleanup_bad_leads(limit: int = 1000, dry_run: bool = False) -> dict`
- **Purpose:** Scans leads and discards those failing quality checks
- **Called by:** `routes/scan.py`
- **Calls:** `get_sql_connection`, `_lead_row_dict`, `lead_cleanup_reasons`
- **Side effects:** SQLite UPDATE on discarded leads
- **Hardcodes:** status exclusion list, limit clamp (max 5000)
- **Flag:** 🟢

#### `get_feedback_training_examples(limit: int = 300) -> list[dict]`
- **Purpose:** Returns leads with non-empty feedback as training examples
- **Called by:** `rank_lead_by_feedback`, `recompute_learning_scores`
- **Calls:** `get_sql_connection`, `_json_list`, `_json_dict`
- **Flag:** 🟢

#### `rank_lead_by_feedback(lead: dict) -> dict`
- **Purpose:** Applies feedback-learning ranker to a lead's signal scores
- **Called by:** `save_lead`, `routes/leads.py`, `agents/x_scout.py`, `agents/free_scout.py`
- **Calls:** `apply_feedback_learning`, `get_feedback_training_examples`
- **Side effects:** none (pure-ish, agents.feedback_ranker may have side effects)
- **Flag:** 🟣 COUPLED — depends on `agents.feedback_ranker`; fallback to defaults on failure

#### `_without_learning_suffix(reason: str) -> str`
- **Purpose:** Strips feedback-learning delta annotation from reason string
- **Called by:** `recompute_learning_scores`
- **Calls:** `re.sub`
- **Flag:** 🟢

#### `recompute_learning_scores(limit: int = 500) -> int`
- **Purpose:** Re-runs feedback learning on all non-discarded leads
- **Called by:** `save_lead_feedback`
- **Calls:** `apply_feedback_learning`, `get_feedback_training_examples`, `get_sql_connection`, `_lead_row_dict`, `_without_learning_suffix`
- **Side effects:** SQLite bulk UPDATE
- **Flag:** 🟢

#### `_read_pdf_text(path: str) -> str`
- **Purpose:** Extracts text from a PDF file using pypdf
- **Called by:** `get_lead_for_fire`
- **Calls:** `PdfReader`
- **Side effects:** File I/O
- **Flag:** 🟢

#### `_pick_first_line(text: str) -> str`
- **Purpose:** Picks the first short non-URL, non-email line from text
- **Called by:** `get_lead_for_fire`
- **Flag:** 🟢

#### `_contact_from_text(text: str) -> dict`
- **Purpose:** Extracts email, phone, LinkedIn, GitHub, website from raw text
- **Called by:** `get_lead_for_fire`
- **Calls:** `re.search`, `re.findall`
- **Flag:** 🟢

#### `get_lead_for_fire(jid: str) -> tuple`
- **Purpose:** Assembles a complete lead dict with profile, settings, and contact info for submission
- **Called by:** `services/generator.py`, `services/ghost.py`, `routes/actions.py`
- **Calls:** `get_sql_connection`, `get_profile`, `_read_pdf_text`, `get_settings`, `_contact_from_text`, `_pick_first_line`, `_json_list`
- **Side effects:** SQLite read, file I/O (PDF reading)
- **Flag:** 🟢 — but returns a massive dict (30+ keys) assembled from 4 different data sources

#### `save_settings(d: dict)`
- **Purpose:** Saves key-value pairs to the settings table
- **Called by:** `routes/settings.py`, `routes/ingest.py`, `routes/misc.py`, `routes/actions.py`, `services/job_targets.py`, `agents/selectors.py`, `tests/test_regressions.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Side effects:** SQLite INSERT OR REPLACE
- **Flag:** 🟣 COUPLED — duplicates the Pydantic config layer; values are ALL stored as strings via `str(v)`

#### `get_settings() -> dict`
- **Purpose:** Returns all settings as a flat dict
- **Called by:** `services/scanner.py`, `services/ghost.py`, `services/job_targets.py`, `routes/settings.py`, `routes/scan.py`, `routes/actions.py`, `routes/misc.py`, `agents/contact_lookup.py`, `get_lead_for_fire`
- **Calls:** `get_sql_connection`, `c.execute`
- **Flag:** 🟣 COUPLED — duplicates the Pydantic config layer; returns all values as strings

#### `get_setting(k: str, default: str = "") -> str`
- **Purpose:** Returns a single setting value
- **Called by:** `config/secrets.py`, `services/ghost.py`, `services/generator.py`, `routes/misc.py`, `agents/actuator.py`, `agents/evaluator.py`, `agents/selectors.py`, `llm.py`, `tests/test_api.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Flag:** 🟣 COUPLED — creates circular dependency: `config/secrets.py` uses this, and `db.client` imports from `config`

#### `get_lead_by_id(jid: str) -> dict`
- **Purpose:** Returns a single lead with its recent events
- **Called by:** `routes/leads.py`, `routes/scan.py`, `routes/actions.py`, `services/scanner.py`, `services/generator.py`
- **Calls:** `get_sql_connection`, `_lead_row_dict`
- **Flag:** 🟢

#### `delete_lead(jid: str)`
- **Purpose:** Deletes a lead and its events; raises LookupError if not found
- **Called by:** `routes/leads.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Side effects:** SQLite DELETE
- **Flag:** 🟢

#### `update_lead_status(jid: str, status: str)`
- **Purpose:** Updates lead status with validation against allowed set
- **Called by:** `routes/leads.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Side effects:** SQLite UPDATE + INSERT event
- **Hardcodes:** allowed status set
- **Flag:** 🔵 HARDCODED — status values baked in

#### `save_lead_feedback(jid: str, feedback: str, note: str = "") -> dict`
- **Purpose:** Applies user feedback to a lead, potentially changing its status
- **Called by:** `routes/leads.py`
- **Calls:** `get_sql_connection`, `_utc_timestamp`, `recompute_learning_scores`, `get_lead_by_id`
- **Side effects:** SQLite UPDATE + INSERT event; triggers `recompute_learning_scores`
- **Hardcodes:** feedback-to-status mappings, 5-day followup for "already_contacted"
- **Flag:** 🔵 HARDCODED — feedback values and status transitions baked in; 🐌 triggers full recompute (potentially expensive for large DBs)

#### `update_lead_followup(jid: str, days: int = 5) -> dict`
- **Purpose:** Sets the followup due date on a lead
- **Called by:** `routes/leads.py`
- **Calls:** `_utc_timestamp`, `get_sql_connection`, `get_lead_by_id`
- **Side effects:** SQLite UPDATE + INSERT event
- **Flag:** 🟢

#### `get_due_followups(limit: int = 25) -> list`
- **Purpose:** Returns leads whose followup date is past due
- **Called by:** `routes/leads.py`
- **Calls:** `_utc_timestamp`, `get_sql_connection`, `_lead_row_dict`
- **Flag:** 🟢

#### `get_events(limit: int = 100, job_id: str | None = None) -> list`
- **Purpose:** Returns events, optionally filtered by job_id
- **Called by:** `routes/misc.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Flag:** 🟢

#### `get_discovered_leads() -> list`
- **Purpose:** Returns job leads in 'discovered' status
- **Called by:** `services/scanner.py`, `services/ghost.py`
- **Calls:** `get_sql_connection`, `c.execute`
- **Flag:** 🟢

#### `get_discovered_freelance_leads() -> list` — ✅ REMOVED
- **Was:** Returns freelance leads in 'discovered' status
- **Status:** Deleted — never imported or called anywhere

#### `_h(t: str) -> str`
- **Purpose:** Returns first 12 hex chars of MD5 hash for ID generation
- **Called by:** `add_skill`, `add_experience`, `add_project`, `add_education`, `add_certification`, `add_achievement`, `update_candidate`
- **Flag:** 🟢 — consistent ID generation pattern

#### `_stack_list(value) -> list[str]`
- **Purpose:** Normalizes stack values to list of strings
- **Called by:** `_read_profile_from_graph`
- **Flag:** 🟢

#### `_profile_has_data(profile: dict | None) -> bool`
- **Purpose:** Checks if a profile dict has any meaningful data
- **Called by:** `_load_profile_snapshot`, `_save_profile_snapshot`, `get_profile`
- **Flag:** 🟢

#### `_empty_profile() -> dict`
- **Purpose:** Returns a profile dict with all empty fields
- **Called by:** `get_profile`
- **Flag:** 🟢

#### `_normal_profile(profile: dict | None) -> dict`
- **Purpose:** Normalizes raw profile dict to canonical shape with aliases for certs/awards
- **Called by:** `_load_profile_snapshot`, `_save_profile_snapshot`, `get_profile`
- **Flag:** 🟢 — alias mapping (`certs` → `certifications`, `awards` → `achievements`) is reasonable

#### `_load_profile_snapshot() -> dict`
- **Purpose:** Loads profile snapshot from SQLite settings table
- **Called by:** `get_profile`
- **Calls:** `get_sql_connection`, `_normal_profile`, `_profile_has_data`, `json.loads`
- **Flag:** 🟢

#### `_save_profile_snapshot(profile: dict)`
- **Purpose:** Saves profile snapshot to SQLite settings table
- **Called by:** `get_profile`, `refresh_profile_snapshot`, all Kuzu CRUD functions
- **Calls:** `get_sql_connection`, `_normal_profile`, `_profile_has_data`, `json.dumps`
- **Side effects:** SQLite INSERT OR REPLACE
- **Flag:** 🟢

#### `_read_profile_from_graph() -> dict`
- **Purpose:** Reads candidate profile from Kuzu graph, assembling data from all node types
- **Called by:** `get_profile`, `refresh_profile_snapshot`
- **Calls:** `Connection(db)`, multiple `MATCH` queries, `_stack_list`
- **Side effects:** Opens new Kuzu connection each call, multiple graph queries
- **Hardcodes:** All node labels, property names, relationship types
- **Flag:** 🔵 HARDCODED — all entity types, properties, and queries are baked in; 🟣 COUPLED — creates a new `Connection(db)` each call

#### `get_profile() -> dict`
- **Purpose:** Main profile accessor: tries graph, falls back to snapshot, then empty
- **Called by:** `services/scanner.py`, `services/ghost.py`, `routes/scan.py`, `routes/actions.py`, `routes/leads.py`, `agents/contact_lookup.py`, `get_lead_for_fire` (internal), `graph/__init__.py`
- **Calls:** `_load_profile_snapshot`, `_read_profile_from_graph`, `_normal_profile`, `_empty_profile`, `_save_profile_snapshot`
- **Flag:** 🟢 — good fallback chain

#### `refresh_profile_snapshot()`
- **Purpose:** Forces re-read from graph and saves to snapshot
- **Called by:** `routes/ingest.py`, `tests/test_observability.py`
- **Calls:** `_save_profile_snapshot`, `_read_profile_from_graph`
- **Side effects:** SQLite INSERT OR REPLACE (via `_save_profile_snapshot`)
- **Flag:** 🟢

#### `add_skill(n: str, cat: str) -> dict`
- **Purpose:** Creates or updates a skill node in Kuzu graph and adds to vector store
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)`, `_h`, `_add_skill_vec`, `refresh_profile_snapshot`
- **Side effects:** Kuzu CREATE/MERGE, LanceDB add, SQLite profile snapshot update
- **Flag:** 🟣 COUPLED — creates 2-3 Kuzu connections per call; touches 3 databases

#### `update_skill(sid: str, n: str, cat: str) -> dict`
- **Purpose:** Updates a skill node and re-indexes in vector store
- **Called by:** `tests/test_observability.py`
- **Calls:** `Connection(db)`, `_add_skill_vec`, `refresh_profile_snapshot`
- **Side effects:** Kuzu SET, LanceDB add, SQLite profile snapshot update
- **Flag:** 🟣 COUPLED — same 3-DB pattern as add_skill

#### `delete_skill(sid: str)`
- **Purpose:** Deletes a skill node from graph and vector store
- **Called by:** not confirmed imported — check cross-refs
- **Calls:** `Connection(db)`, `_delete_vec_rows`, `refresh_profile_snapshot`
- **Side effects:** Kuzu DETACH DELETE, LanceDB delete, SQLite profile snapshot update
- **Flag:** 🟡 SUSPECT — not found in import grep results; may be dead or used via `from db import client`

#### `add_experience(role, co, period, d) -> dict`
- **Purpose:** Creates an experience node and links to candidate
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)` 2-3 times, `_h`, `refresh_profile_snapshot`
- **Side effects:** Kuzu multiple queries
- **Flag:** 🟣 COUPLED — creates 2-3 Kuzu connections per call

#### `update_experience(eid, role, co, period, d) -> dict`
- **Purpose:** Updates an experience node
- **Called by:** unknown
- **Calls:** `Connection(db)`, `refresh_profile_snapshot`
- **Flag:** 🟡 SUSPECT — not in import grep results; may be dead UI feature

#### `delete_experience(eid: str)`
- **Purpose:** Deletes an experience node
- **Called by:** unknown
- **Calls:** `Connection(db)`, `refresh_profile_snapshot` (called twice)
- **Flag:** 🟡 SUSPECT — `refresh_profile_snapshot` called twice (lines 1410 and 1413), likely a bug; not in import grep results

#### `add_project(title, stack, repo, impact) -> dict`
- **Purpose:** Creates a project node, links to candidate, adds to vector store
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)` 2-3 times, `_h`, `_add_project_vec`, `refresh_profile_snapshot`
- **Side effects:** Kuzu, LanceDB, SQLite
- **Flag:** 🟣 COUPLED — 3 DBs, 2-3 Kuzu connections per call

#### `update_project(pid, title, stack, repo, impact) -> dict`
- **Purpose:** Updates a project node and re-indexes in vector store
- **Called by:** unknown
- **Calls:** `Connection(db)`, `_add_project_vec`, `refresh_profile_snapshot`
- **Flag:** 🟡 SUSPECT — not in import grep results

#### `delete_project(pid: str)`
- **Purpose:** Deletes a project node and vector embedding
- **Called by:** unknown
- **Calls:** `Connection(db)`, `_delete_vec_rows`, `refresh_profile_snapshot`
- **Flag:** 🟡 SUSPECT — not in import grep results

#### `add_education(title: str) -> dict`
- **Purpose:** Creates an education node and links to candidate
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)` 2-3 times, `_h`, `refresh_profile_snapshot`
- **Flag:** 🟣 COUPLED — multiple Kuzu connections per call

#### `add_certification(title: str) -> dict`
- **Purpose:** Creates a certification node and links to candidate
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)` 2-3 times, `_h`, `refresh_profile_snapshot`
- **Flag:** 🟣 COUPLED — multiple Kuzu connections per call

#### `add_achievement(title: str) -> dict`
- **Purpose:** Creates an achievement node and links to candidate
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)` 2-3 times, `_h`, `refresh_profile_snapshot`
- **Flag:** 🟣 COUPLED — multiple Kuzu connections per call

#### `update_candidate(name: str, summary: str) -> dict`
- **Purpose:** Creates or updates the single candidate node
- **Called by:** `routes/ingest.py`
- **Calls:** `Connection(db)` 2 times, `hashlib.md5`, `refresh_profile_snapshot`
- **Flag:** 🟣 COUPLED — calls `refresh_profile_snapshot` twice (lines 1574 and 1594), first call is unnecessary

#### `_delete_vec_rows(table_name: str, ids: list[str])`
- **Purpose:** Deletes vector rows by id; no-op if table doesn't exist
- **Called by:** `delete_skill`, `delete_project`, `_add_skill_vec`, `_add_project_vec`, `tests/test_observability.py`
- **Calls:** `vec.list_tables`, `vec.open_table`, `vec.open_table(name).delete`
- **Flag:** 🟢

#### `_add_skill_vec(sid: str, n: str, cat: str)`
- **Purpose:** Creates/updates a skill embedding in LanceDB
- **Called by:** `add_skill`, `update_skill`
- **Calls:** `_emb` (from `agents.ingestor`), `_delete_vec_rows`, `vec.create_table`/`vec.open_table`
- **Flag:** 🟣 COUPLED — depends on `agents.ingestor._emb`; | `_emb` is a private import from another module

#### `_add_project_vec(pid: str, title: str, stack: str, impact: str)`
- **Purpose:** Creates/updates a project embedding in LanceDB
- **Called by:** `add_project`, `update_project`
- **Calls:** `_emb` (from `agents.ingestor`), `_delete_vec_rows`, `vec.create_table`/`vec.open_table`
- **Flag:** 🟣 COUPLED — depends on `agents.ingestor._emb`

**Exports (what other modules import from this file):**

| Export | Known importers |
|--------|----------------|
| `data_base` | `agents/generator.py`, `routes/actions.py`, `routes/leads.py`, `tests/test_paths.py` |
| `get_sql_connection` | `agents/generator.py`, `routes/misc.py`, `tests/test_api.py`, `tests/test_sqlite.py`, `tests/test_observability.py` |
| `sql` | `agents/generator.py`, `e2e/manval/run_live_fire.py` |
| `get_profile` | `services/scanner.py`, `services/ghost.py`, `routes/scan.py`, `routes/actions.py`, `routes/leads.py`, `agents/contact_lookup.py` |
| `get_settings` | `services/scanner.py`, `services/ghost.py`, `services/job_targets.py`, `routes/settings.py`, `routes/scan.py`, `routes/actions.py`, `routes/misc.py`, `agents/contact_lookup.py` |
| `get_setting` | `config/secrets.py`, `services/ghost.py`, `services/generator.py`, `routes/misc.py`, `agents/actuator.py`, `agents/evaluator.py`, `agents/selectors.py`, `llm.py`, `tests/test_api.py` |
| `save_settings` | `routes/settings.py`, `routes/ingest.py`, `routes/misc.py`, `routes/actions.py`, `services/job_targets.py`, `agents/selectors.py`, `tests/test_regressions.py` |
| `get_lead_by_id` | `routes/leads.py`, `routes/scan.py`, `routes/actions.py`, `services/scanner.py`, `services/generator.py` |
| `get_lead_for_fire` | `services/generator.py`, `services/ghost.py`, `routes/actions.py` |
| `save_lead` | `agents/scout.py`, `agents/x_scout.py`, `agents/free_scout.py`, `routes/leads.py`, `e2e/manval/run_live_fire.py` |
| `update_lead_score` | `services/scanner.py`, `routes/leads.py`, `graph/__init__.py`, `e2e/manval/run_live_fire.py` |
| `url_exists` | `agents/scout.py`, `agents/x_scout.py`, `agents/free_scout.py` |
| `record_event` | `core/ws_manager.py` |
| `save_asset_package` | `services/generator.py`, `services/ghost.py`, `graph/__init__.py` |
| `save_contact_lookup` | `services/generator.py` |
| `mark_applied` | `services/generator.py`, `services/ghost.py`, `e2e/manval/run_live_fire.py` |
| `save_asset_path` | `e2e/manval/run_live_fire.py` |
| `get_due_followups` | `routes/leads.py` |
| `update_lead_followup` | `routes/leads.py` |
| `save_lead_feedback` | `routes/leads.py` |
| `delete_lead` | `routes/leads.py` |
| `update_lead_status` | `routes/leads.py` |
| `rank_lead_by_feedback` | `routes/leads.py`, `agents/x_scout.py`, `agents/free_scout.py` |
| `get_all_leads` | `routes/leads.py` |
| `get_discovered_leads` | `services/scanner.py`, `services/ghost.py` |
| `cleanup_bad_leads` | `routes/scan.py` |
| `get_events` | `routes/misc.py` |
| `graph_counts` | `routes/misc.py` |
| `refresh_profile_snapshot` | `routes/ingest.py`, `tests/test_observability.py` |
| `update_candidate` | `routes/ingest.py` |
| `add_skill` | `routes/ingest.py`, `tests/test_observability.py` |
| `update_skill` | `routes/profile.py`, `tests/test_observability.py` |
| `delete_skill` | `routes/profile.py` |
| `add_experience` | `routes/ingest.py` |
| `update_experience` | `routes/profile.py` |
| `delete_experience` | `routes/profile.py` |
| `add_education` | `routes/ingest.py` |
| `add_project` | `routes/ingest.py` |
| `update_project` | `routes/profile.py` |
| `delete_project` | `routes/profile.py` |
| `add_certification` | `routes/ingest.py` |
| `add_achievement` | `routes/ingest.py` (via `add_skill, add_project, save_settings` import on line 165) |
| `vec` | `agents/ingestor.py`, `agents/semantic.py` |
| `db` | `agents/ingestor.py` |
| `_delete_vec_rows` | `tests/test_observability.py` |
| `_ensure_dir` | `tests/test_paths.py` |
| `get_job_leads_for_evaluation` | `services/scanner.py` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | ✅ RESOLVED | `graph_available()` | was `client.py:134` | Removed — never imported or called |
| P0 | ✅ RESOLVED | `graph_error()` | was `client.py:138` | Removed — never imported or called |
| P0 | ✅ RESOLVED | `get_all_freelance_leads()` | was `client.py:523` | Removed — never imported or called |
| P0 | ✅ RESOLVED | `get_discovered_freelance_leads()` | was `client.py:1114` | Removed — never imported or called |
| P0 | ✅ RESOLVED | `_b` premature path computation | was `client.py:41-43` | Removed — `_g`, `_v`, `sql` now computed after `_ensure_dir` |
| P1 | 🟣 COUPLED | Module-level import chain | `client.py:28+125+236` | `from config import settings` creates circular dep (config → db.client → config via secrets.py); `_init()` and `_init_sql()` run at module level |
| P1 | 🟣 COUPLED | Kuzu CRUD functions | `client.py:1263-1551` | Create new `Connection(db)` 2-3 times per call, no connection reuse; mixed with SQLite and LanceDB in same functions |
| P1 | 🟣 COUPLED | `save_settings`/`get_settings`/`get_setting` | `client.py:920-939` | SQLite-based key-value store duplicates the Pydantic config layer (`config/*.py`) |
| P1 | ⚪ INCOMPLETE | Duplicate `resume_version` migration | `client.py:222,228-232` | Lines 222 and 228-232 both attempt to add `resume_version` column — second block is redundant |
| P1 | ⚪ INCOMPLETE | `refresh_profile_snapshot` called twice | `client.py:1530,1550` | `update_candidate` calls `refresh_profile_snapshot` twice (before and after Kuzu operation) — likely bug |
| P1 | ⚪ INCOMPLETE | `refresh_profile_snapshot` called twice | `client.py:1366,1369` | `delete_experience` calls `refresh_profile_snapshot` twice |
| P2 | ✅ RESOLVED | Score thresholds (76) | was `client.py:369,371` | Externalized to `config.scoring.quality_gate.score_threshold_matched` |
| P2 | ✅ RESOLVED | Status string set | was `client.py:970-974` | Externalized to `config.scoring.LEAD_STATUSES` |
| P2 | ✅ RESOLVED | Feedback-to-status mappings | was `client.py:990-1014` | Externalized to `config.scoring.VALID_FEEDBACK`, `FEEDBACK_DISCARDED` |
| P2 | 🔵 HARDCODED | `_LEAD_SELECT_COLUMNS` | `client.py:236-243` | 38-column list must be kept in sync with schema by hand |
| P2 | 🔵 HARDCODED | All Kuzu table names/schemas | `client.py:106-122` | All node/rel table names, property names, and types are baked in |
| P2 | 🔵 HARDCODED | All SQLite table names/schemas | `client.py:167-188` | All table names, column names, and types are baked in |
| P2 | 🟡 SUSPECT | `save_asset_path()` | `client.py:397` | Partially superseded by `save_asset_package()` — only used by `e2e/manval/run_live_fire.py` |
| P2 | 🟢 USED | `update_skill()` | `client.py:1289` | Used by `routes/profile.py:update_skill_endpoint` and `tests/test_observability.py` — NOT dead |
| P2 | 🟢 USED | `delete_skill()` | `client.py:1303` | Used by `routes/profile.py:delete_skill_endpoint` — NOT dead |
| P2 | 🟢 USED | `update_experience()` | `client.py:1349` | Used by `routes/profile.py:update_experience_endpoint` — NOT dead |
| P2 | 🟢 USED | `delete_experience()` | `client.py:1364` | Used by `routes/profile.py:delete_experience_endpoint` — NOT dead |
| P2 | 🟢 USED | `update_project()` | `client.py:1415` | Used by `routes/profile.py:update_project_endpoint` — NOT dead |
| P2 | 🟢 USED | `delete_project()` | `client.py:1434` | Used by `routes/profile.py:delete_project_endpoint` — NOT dead |
| P3 | 🟢 CLEAN | `_utc_timestamp()` | `client.py:46` | Well-scoped helper, no issues |
| P3 | 🟢 CLEAN | `url_exists()` | `client.py:265` | Simple, correct, well-used |
| P3 | 🟢 CLEAN | `get_sql_connection()` | `client.py:155` | Correct pragma usage (WAL, foreign_keys, busy_timeout) |
| P3 | 🟢 CLEAN | `_NullVectorStore` | `client.py:53` | Sensible no-op fallback pattern |
| P3 | 🟢 CLEAN | `_json_list`/`_json_dumps_list`/`_json_dict` | `client.py:546-582` | Consistent JSON serialization helpers |
| P3 | 🟢 CLEAN | `get_profile()` fallback chain | `client.py:1282` | Good: graph → snapshot → empty |
| P3 | 🟢 CLEAN | `_ensure_dir()` | `client.py:69` | Sensible path fallback on failure |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `backend/routes/` — all route modules import from `db.client`
- `backend/services/` — all service modules import from `db.client`
- `backend/agents/` — ingestor, scout, x_scout, free_scout, contact_lookup, semantic, selector, actuator, evaluator, generator all import from `db.client`
- `backend/config/secrets.py` — imports `get_setting` (🔴 circular dep)
- `backend/llm.py` — imports `get_setting`
- `backend/graph/__init__.py` — imports `save_asset_package`, `update_lead_score`
- `backend/core/ws_manager.py` — imports `record_event`
- `backend/tests/` — 6 test files import from `db.client`
- `e2e/manval/run_live_fire.py` — imports from `db.client`

**Outbound (this unit depends on others):**
- `backend/config/` — imports `settings` from `config` (`client.py:28`)
- `backend/agents/` — imports `apply_feedback_learning` from `agents.feedback_ranker` and `_emb` from `agents.ingestor`
- `backend/logger.py` — imports `get_logger`

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| kuzu | Graph database (node/rel store) | no — optional try/except | 🟢 — graceful fallback |
| lancedb | Vector store for embeddings | no — optional try/except | 🟢 — graceful fallback |
| pypdf | PDF text extraction | no — lazy import inside function | 🟢 — lazy import |

---

## 6. First principles assessment

1. **Does this file need to exist?** Partially — the data access logic is essential, but a single 1641-line file managing three different databases is too large. It should be split into at least `sqlite.py`, `graph.py`, and `vector.py`.

2. **Does it do what it claims?** No — the filename `client.py` suggests a client abstraction, but it's actually a flat collection of procedural functions with module-level side effects. The name is misleading.

3. **Is it the right place for this logic?** No — settings CRUD (`get_settings`/`save_settings`/`get_setting`) duplicates the Pydantic config layer and creates a circular dependency. The feedback-ranking integration (`rank_lead_by_feedback`, `recompute_learning_scores`) couples DB logic with ML agent logic. The vector store helpers (`_add_skill_vec`, `_add_project_vec`) import from `agents.ingestor`, inverting the dependency direction.

4. **What would break if deleted?** Everything — this is the most-imported file in the entire backend. All routes, services, agents, and graph workflows depend on it. The application would not start without it.
