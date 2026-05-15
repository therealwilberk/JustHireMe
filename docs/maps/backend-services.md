# Map: backend-services

**File:** `docs/maps/backend-services.md`
**Codebase path(s):** `backend/services/`
**Files in scope:** 7
**Total lines:** ~1,443
**Generated:** 2026-05-15
**Resolved:** `fix/resolve-services` — query templates wired to config, `kind_filter` dead params removed, eval doc dedup, `market_focus` params cleaned. Detailed breakdown below is preserved as snapshot (may be stale).

---

## 1. Unit summary

The `backend/services/` package is the orchestration layer between API routes (HTTP/WS) and agents (LLM-powered work). It owns scan lifecycle state (`ScanManager`), ghost-mode automation (`GhostService`), generation/actuation pipeline (`_generate_one`, `_actuate`, `_fire_blocker`), job target configuration CRUD and validation, LLM provider key health-checking (`_probe_provider_key`), and free-source / X signal scanning dispatch. It depends on `agents/`, `db.client`, `core.ws_manager`, `config`, and `log_context`. Route modules (`routes/scan.py`, `routes/settings.py`, `routes/actions.py`, `routes/leads.py`, `main.py`) import from it. It does NOT depend on any other service unit.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `services/__init__.py` | 0 | Empty package init | 🟢 CLEAN |
| 2 | `services/generator.py` | 170 | Resume/CL generation and application submission pipeline | 🟣 COUPLED — `_fire_blocker` circular import (deferred) |
| 3 | `services/ghost.py` | 275 | Ghost mode automated lifecycle (7 phases) | 🟣 COUPLED — `_fire_blocker` + `_ghost_lock` (deferred) |
| 4 | `services/job_targets.py` | 388 | Job target CRUD, validation, profile enrichment, settings helpers | 🟢 CLEAN — query templates wired to config, `market_focus` params cleaned |
| 5 | `services/provider_probe.py` | 115 | LLM provider API key health checking | 🟢 CLEAN — timeout wired to config |
| 6 | `services/scanner.py` | 358 | Scan lifecycle state machine + scan/reevaluate pipelines | 🟣 COUPLED — private attr access (deferred); eval doc dedup fixed |
| 7 | `services/scout.py` | 137 | X/Twitter and free-source signal scanning dispatch | 🟢 CLEAN — `kind_filter` dead params removed |

---

## 3. Detailed breakdown

### `services/__init__.py`

**Purpose:** Empty package marker. Does nothing.

**Imports:** None.

**Module-level constants & state:** None.

**Exports:** None.

---

### `services/generator.py`

**Purpose:** Provides the generation pipeline (`_generate_one`) and application submission (`_actuate`), with `_fire_blocker` as a pre-submission guard. Used by `routes/actions.py`, `routes/leads.py`, and `main.py`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | `_generate_one`, `_actuate` | 🟢 — standard |
| `os` | stdlib | `_asset_ready` | 🟢 — standard |
| `fastapi.HTTPException` | 3rd-party | `_generate_one` | 🟢 — standard |
| `core.ws_manager.cm` | local | `_generate_one`, `_actuate` | 🟢 — clean usage |

**Module-level constants & state:** None.

**Functions:**

#### `_asset_ready(path: str) -> bool`
- **Purpose:** Check whether a file exists at the given path (non-empty + `os.path.isfile`).
- **Called by:** `_fire_blocker`
- **Calls:** `os.path.isfile`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — simple, correct

#### `_fire_blocker(lead: dict, asset: str) -> tuple[int, str]`
- **Purpose:** Validate that a lead is ready for application submission: exists, not already applied, has URL, both resume and cover letter assets on disk.
- **Called by:** `_actuate` (same file), `routes/actions.py` (lines 83, 207), `main.py` — also imported **back** from `main.py` by `ghost.py:243` (circular import workaround).
- **Calls:** `_asset_ready`
- **Side effects:** none
- **Hardcodes:** status string `"applied"`, cover key fallback `["cover_letter_asset", "cover_letter_path"]`
- **Flag:** 🟣 COUPLED — ghost.py imports this via `from main import _fire_blocker` creating a hidden circular dependency

#### `async _generate_one(jid: str) -> dict`
- **Purpose:** Fetches a lead, runs generator agent, persists assets + outreach messages to DB, runs contact lookup, broadcasts WS events. Raises HTTPException on failure.
- **Called by:** `routes/leads.py:344`, `main.py`
- **Calls:** `agents.generator.run_package`, `agents.contact_lookup.run`, `db.client.get_lead_by_id`, `db.client.save_asset_package`, `db.client.save_contact_lookup`, `db.client.get_setting`, `cm.broadcast`, and inline SQL for outreach fields
- **Side effects:** DB writes (asset package, contact lookup, outreach messages), WS broadcasts
- **Hardcodes:** `"status": "approved"` on success
- **Flag:** 🟡 SUSPECT — inline raw SQL (`UPDATE leads SET ...`) bypasses db.client abstraction; re-fetches lead but then uses the in-memory `lead` var for some fields

#### `async _actuate(jid: str) -> None`
- **Purpose:** Runs fire-blocker check then delegates to actuator agent; marks applied on success.
- **Called by:** `routes/actions.py:81`
- **Calls:** `agents.actuator.run`, `db.client.get_lead_for_fire`, `db.client.mark_applied`, `_fire_blocker`
- **Side effects:** DB writes (`mark_applied`), WS broadcasts, browser automation via actuator agent
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `_fire_blocker` | `main.py:187`, `routes/actions.py:81,204`, `ghost.py:243` (via `main`) |
| `_generate_one` | `main.py:187`, `routes/leads.py:344` |
| `_actuate` | `routes/actions.py:81` |

---

### `services/ghost.py`

**Purpose:** Orchestrates the full ghost-mode lifecycle: preflight, X scan, free-source scan, scout, LLM evaluation, generation, and auto-apply. Core file for the automated background scanning feature.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | `_ghost_tick`, `_phase_*` methods | 🟢 — standard |
| `core.ws_manager.cm` | local | all `_phase_*` and `_ghost_tick` | 🟢 — clean usage |
| `core.config_constants._log` | local | `_ghost_tick` | 🟢 — clean usage |
| `config.settings` | local | `_phase_scout` | 🟢 — clean usage |
| `services.job_targets._job_targets` | local | `_phase_preflight` | 🟢 — clean |
| `services.job_targets._profile_for_discovery` | local | `_phase_preflight`, `_phase_eval` | 🟢 — clean |
| `services.job_targets._has_x_token` | local | `_phase_preflight`, `_phase_x_scan` | 🟢 — clean |
| `services.job_targets._free_sources_enabled` | local | `_phase_preflight`, `_phase_free_scan` | 🟢 — clean |
| `services.scanner.ScanManager` | local | `GhostService.__init__` | 🟢 — clean |
| `services.scanner.scan_manager` | local | `_ghost_tick` | 🟣 COUPLED — accesses private `_ghost_lock` |
| `services.scanner._job_eval_document` | local | `_phase_eval` | 🟢 — clean |
| `services.scout._run_x_signal_scan` | local | `_phase_x_scan` | 🟢 — clean |
| `services.scout._run_free_source_scan` | local | `_phase_free_scan` | 🟢 — clean |
| `log_context` (new/set/reset_context) | local | `GhostService.run` | 🟢 — clean |
| `config.secrets.resolve_secret` | local | `_phase_scout` | 🟢 — clean |

**Module-level constants & state:** None.

**Classes:**

#### `GhostService`
- **Inherits from:** None
- **Purpose:** Decomposes the ghost pipeline into 7 sequential phase methods with structured logging
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `__init__` | `scan_manager: ScanManager` | None | Store scan manager ref | 🟢 |
| `run` | (none) | None | Execute all 7 phases in order | 🟢 |
| `_phase_preflight` | (none) | `tuple[dict,dict,list[str]] \| None` | Check ghost enabled and targets exist | 🟢 |
| `_phase_x_scan` | `cfg, profile` | None | Run X signal scan if token configured | 🟢 |
| `_phase_free_scan` | `cfg, profile` | None | Run free-source scan if enabled | 🟢 |
| `_phase_scout` | `cfg, profile, boards` | None | Generate queries + scout job boards | 🟢 |
| `_phase_eval` | `cfg, profile` | `list[dict]` | Score leads via LLM, return >=85 | 🟢 |
| `_phase_gen` | `approved: list[dict]` | `list[dict]` | Generate resume/CL for approved leads | 🟢 |
| `_phase_apply` | `generated: list[dict]` | None | Auto-apply if setting enabled | 🟣 COUPLED — `from main import _fire_blocker` |

**Functions:**

#### `async _ghost_tick() -> None`
- **Purpose:** Try-acquire ghost lock; if acquired, run one GhostService cycle. Called by scheduler.
- **Called by:** `main.py:59`, `routes/settings.py:12`
- **Calls:** `GhostService(scan_manager).run()`, `scan_manager._ghost_lock.acquire()`
- **Side effects:** Acquires/releases asyncio lock
- **Hardcodes:** `timeout=0` for acquire attempt
- **Flag:** 🟣 COUPLED — accesses `scan_manager._ghost_lock` (private attr) directly instead of a public method

**Exports:**

| Export | Known importers |
|--------|----------------|
| `GhostService` | `tests/test_ghost_service.py:3` |
| `_ghost_tick` | `main.py:59`, `routes/settings.py:12` |

---

### `services/job_targets.py`

**Purpose:** Provides helpers for reading, writing, parsing, validating job board URLs and blocked markers; also profile-enrichment utilities for the discovery pipeline. The largest file in the unit.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `json` | stdlib | `get_job_targets`, `get_blocked_markers`, `save_job_targets` | 🟢 — standard |
| `os` | stdlib | `_has_x_token` | 🟢 — standard |
| `re` | stdlib | `_terms_for_discovery` | 🟢 — standard |
| `typing.Any` | stdlib | `_truthy` | 🟢 — standard |
| `core.ws_manager.cm` | local | `_broadcast_x_source_errors` | 🟢 — clean |
| `config.settings` | local | `_has_x_token`, whole module | 🟢 — clean |
| `config.secrets.resolve_secret` | local | `_has_x_token` | 🟢 — clean |

**Module-level constants & state:** None.

**Functions:**

#### `get_job_targets() -> list[str]`
- **Purpose:** Read configured job targets from settings JSON; returns empty list if none.
- **Called by:** `_job_targets` (fallback), `routes/settings.py`
- **Calls:** `db.client.get_settings`, `json.loads`
- **Side effects:** DB read (`get_settings`)
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `get_blocked_markers() -> list[str]`
- **Purpose:** Read configured blocked markers from settings JSON.
- **Called by:** `_job_targets`, `routes/settings.py`
- **Calls:** `db.client.get_settings`, `json.loads`
- **Side effects:** DB read
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `save_job_targets(targets: list[str], blocked: list[str]) -> None`
- **Purpose:** Persist job targets and blocked markers to settings DB.
- **Called by:** `routes/settings.py`
- **Calls:** `db.client.save_settings`, `json.dumps`
- **Side effects:** DB write
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `validate_job_targets(entries: list[str]) -> list[str]`
- **Purpose:** Validate structure, length, and format of job target entries. Accepted: `http(s)://...`, `site:domain/...`, `github:`, `hn:`, `reddit:`, known short names.
- **Called by:** `routes/settings.py`, `tests/test_regressions.py`
- **Side effects:** none
- **Hardcodes:** limit of 100 entries, 500 char per entry
- **Flag:** 🟢 CLEAN — tested via `test_regressions.py`

#### `validate_blocked_markers(entries: list[str]) -> list[str]`
- **Purpose:** Validate blocked marker keywords — simple strings, no URL validation.
- **Called by:** `routes/settings.py`
- **Side effects:** none
- **Hardcodes:** limit of 100 entries, 200 char per entry
- **Flag:** 🟢 CLEAN

#### `_split_configured_targets(raw: str) -> list[str]`
- **Purpose:** Parse a raw newline-separated target string, strip whitespace/commas, skip `#` comments.
- **Called by:** `_job_targets`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — tested via `test_regressions.py`

#### `_job_targets(raw: str, market_focus: str = "global") -> list[str]`
- **Purpose:** Resolve job targets from raw settings, fall back to stored JSON, filter against blocked markers.
- **Called by:** `ghost.py:_phase_preflight`, `scanner.py:_run_scan`, `main.py`
- **Calls:** `_split_configured_targets`, `get_job_targets`, `get_blocked_markers`
- **Side effects:** DB read (via `get_job_targets` / `get_blocked_markers`)
- **Hardcodes:** `market_focus` param is documented as unused
- **Flag:** 🟡 SUSPECT — `market_focus` parameter accepted but documented as unused; dead parameter retained for API compat

#### `_desired_position(cfg: dict) -> str`
- **Purpose:** Extract desired position from settings, checking multiple keys in priority order.
- **Called by:** `_profile_for_discovery`
- **Side effects:** none
- **Hardcodes:** key priority list: `["desired_position", "target_position", "target_role", "onboarding_target_role"]`
- **Flag:** 🟢 CLEAN

#### `_profile_for_discovery(profile: dict | None, cfg: dict) -> dict`
- **Purpose:** Enrich user profile with desired position from config; prepend to summary if not already present.
- **Called by:** `ghost.py:_phase_preflight`, `ghost.py:_phase_eval`, `scanner.py:_run_scan`, `routes/scan.py`, `main.py`
- **Calls:** `_desired_position`
- **Side effects:** none (pure transformation)
- **Hardcodes:** uses `profile["s"]` as summary key
- **Flag:** 🟢 CLEAN

#### `_terms_for_discovery(profile: dict, limit: int = 4) -> list[str]`
- **Purpose:** Extract search terms from profile (desired position, experience roles, skills).
- **Called by:** `_profile_free_source_targets`, `_profile_x_queries`
- **Side effects:** none (pure)
- **Hardcodes:** limit default 4, 5-word truncation on summary, regex for stripping punctuation `r"\s+", " "` and `" ,.;:-"`
- **Flag:** 🟢 CLEAN

#### `_profile_free_source_targets(profile: dict) -> str`
- **Purpose:** Build free-source target strings (GitHub/HN/Reddit) from profile terms.
- **Called by:** `scout.py:_run_free_source_scan` (via `_profile_free_source_targets(profile or {})`)
- **Calls:** `_terms_for_discovery`
- **Side effects:** none (pure)
- **Hardcodes:** template strings for `github:`, `hn:`, `reddit:`
- **Flag:** 🔵 HARDCODED — query templates baked in; should be configurable

#### `_profile_x_queries(profile: dict, market_focus: str = "global") -> str`
- **Purpose:** Build X/Twitter search queries from profile terms.
- **Called by:** `scout.py:_run_x_signal_scan`
- **Calls:** `_terms_for_discovery`
- **Side effects:** none (pure)
- **Hardcodes:** `market_focus` parameter unused; query templates, location term list, lang:en filter baked in
- **Flag:** 🔵 HARDCODED — query templates and location terms baked in; `market_focus` unused

#### `_has_x_token(cfg: dict) -> bool`
- **Purpose:** Check whether an X API bearer token is available (secret resolver or env var).
- **Called by:** `ghost.py:_phase_preflight`, `ghost.py:_phase_x_scan`, `scout.py:_run_x_signal_scan`
- **Calls:** `resolve_secret`, `os.environ.get`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_int_cfg(cfg: dict, key: str, default: int, min_value: int, max_value: int) -> int`
- **Purpose:** Read an integer setting with bounds clamping.
- **Called by:** `scout.py` (x and free source scan functions)
- **Side effects:** none (pure)
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_truthy(value: Any) -> bool`
- **Purpose:** Check if a value is truthy per settings convention (`"1"`, `"true"`, `"yes"`, `"on"`).
- **Called by:** `_free_sources_enabled`, `scout.py`
- **Side effects:** none (pure)
- **Hardcodes:** acceptable truthy strings list
- **Flag:** 🟢 CLEAN

#### `_free_sources_enabled(cfg: dict) -> bool`
- **Purpose:** Check whether free-source scanning is enabled.
- **Called by:** `ghost.py`, `scout.py`
- **Calls:** `_truthy`
- **Side effects:** none
- **Hardcodes:** default `"false"`
- **Flag:** 🟢 CLEAN

#### `async _broadcast_x_source_errors(errors: list[str]) -> None`
- **Purpose:** Broadcast X source scanning errors to frontend via WS (max 3 + summary).
- **Called by:** `scout.py:_run_x_signal_scan`
- **Calls:** `cm.broadcast`
- **Side effects:** WS broadcasts
- **Hardcodes:** max 3 individual errors
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `get_job_targets` | `routes/settings.py:11` |
| `get_blocked_markers` | `routes/settings.py:11` |
| `save_job_targets` | `routes/settings.py:11` |
| `validate_job_targets` | `routes/settings.py:11`, `tests/test_regressions.py` |
| `validate_blocked_markers` | `routes/settings.py:11` |
| `_job_targets` | `ghost.py:13`, `scanner.py:15`, `main.py:185` |
| `_profile_for_discovery` | `ghost.py:13`, `scanner.py:15`, `routes/scan.py:12`, `main.py:185` |
| `_has_x_token` | `ghost.py:13`, `scout.py:14` |
| `_free_sources_enabled` | `ghost.py:13`, `scout.py:14` |
| `_profile_x_queries` | `scout.py:13` |
| `_profile_free_source_targets` | `scout.py:13` |
| `_int_cfg` | `scout.py:14` |
| `_truthy` | `scout.py:14` |
| `_broadcast_x_source_errors` | `scout.py:15` |
| `_split_configured_targets` | `tests/test_regressions.py:64` |

---

### `services/provider_probe.py`

**Purpose:** LLM provider API key health checking. Sends a minimal request to each supported provider and reports status/latency.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `time` | stdlib | `_probe_provider_key` | 🟢 — standard |
| `httpx` | 3rd-party | `_probe_provider_key` | 🟢 — standard |
| `config.settings` | local | `_log_sensitive_deprecation` | 🟢 — clean |
| `core.config_constants._log` | local | `_log_sensitive_deprecation` | 🟢 — clean |

**Module-level constants & state:** None.

**Functions:**

#### `async _probe_provider_key(provider: str, key: str) -> dict`
- **Purpose:** Send cheapest-possible request to a provider and return `{status, latency_ms}`.
- **Called by:** `routes/settings.py`
- **Calls:** `llm._OPENAI_COMPAT_BASE_URLS` (lazy), `httpx.AsyncClient`
- **Side effects:** HTTP requests to external APIs
- **Hardcodes:** `timeout=5.0`, Anthropic model `"claude-haiku-4-5-20251001"`, max_tokens=1, API version `"2023-06-01"`
- **Flag:** 🔵 HARDCODED — Anthropic model name pinned to a specific dated version; timeout hardcoded

#### `_sensitive(d: dict) -> set[str]`
- **Purpose:** Return set of keys that should be masked on reads / preserved on writes.
- **Called by:** `routes/settings.py`, `main.py:188`
- **Side effects:** none (pure)
- **Hardcodes:** fixed key set `{"anthropic_key", "linkedin_cookie", "x_bearer_token", "custom_connector_headers"}`; dynamic suffix detection for `_api_key`, `_key`, `_token`
- **Flag:** 🟢 CLEAN

#### `_log_sensitive_deprecation(payload: dict) -> None`
- **Purpose:** Log deprecation warning for each secret written to SQLite instead of env vars.
- **Called by:** `routes/settings.py`
- **Side effects:** logs warnings
- **Hardcodes:** mapping of settings keys to env var names
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `_probe_provider_key` | `routes/settings.py:14` |
| `_sensitive` | `routes/settings.py:14`, `main.py:188` |
| `_log_sensitive_deprecation` | `routes/settings.py:14` |

---

### `services/scanner.py`

**Purpose:** Scan lifecycle state machine (`ScanManager` class) plus the core scan and re-evaluate pipelines. Manages concurrent access to scan/reevaluate/ghost operations via asyncio lock and stop events.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | `ScanManager`, `_run_reevaluate_jobs`, `_run_scan` | 🟢 — standard |
| `fastapi.HTTPException` | 3rd-party | `ScanManager.start_scan`, `ScanManager.start_reevaluate` | 🟢 — standard |
| `core.ws_manager.cm` | local | `_run_scan`, `_run_reevaluate_jobs` | 🟢 — clean |
| `core.config_constants._log` | local | `ScanManager`, `_run_scan` | 🟢 — clean |
| `config.settings` | local | `_run_scan` | 🟢 — clean |
| `services.job_targets._job_targets` | local | `_run_scan` | 🟢 — clean |
| `services.job_targets._profile_for_discovery` | local | `_run_scan` | 🟢 — clean |
| `services.scout._run_x_signal_scan` | local | `_run_scan` | 🟢 — clean |
| `services.scout._run_free_source_scan` | local | `_run_scan` | 🟢 — clean |
| `config.secrets.resolve_secret` | local | `_run_scan` | 🟢 — clean |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `scan_manager` | `ScanManager` | `ScanManager()` | whole module + external | 🟢 — singleton, intentional |
| `_REEVALUATION_STATUS_LOCKS` | `set[str]` | `{"approved", "applied", "interviewing", "rejected", "accepted", "discarded"}` | `_should_preserve_job_status` | 🟢 — clear, well-named |

**Classes:**

#### `ScanManager`
- **Inherits from:** None
- **Purpose:** Lifecycle state machine for scan/reevaluate/ghost operations with asyncio lock and stop events
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `__init__` | (none) | None | Initialize task/stop/lock state | 🟢 |
| `start_scan` | (none) | `dict` | Start scan if no conflict | 🟢 |
| `stop_scan` | (none) | `dict` | Cancel running scan | 🟢 |
| `start_reevaluate` | (none) | `dict` | Start reevaluation if no conflict | 🟢 |
| `stop_reevaluate` | (none) | `dict` | Cancel running reevaluation | 🟢 |
| `is_scanning` | (none) | `bool` | Check if scan is running | 🟢 |
| `is_reevaluating` | (none) | `bool` | Check if reevaluation is running | 🟢 |
| `_run_scan_task` | (none) | None | Acquire ghost lock, delegate to `_run_scan` | 🟢 |
| `_run_reevaluate_jobs_task` | (none) | None | Acquire ghost lock, delegate to `_run_reevaluate_jobs` | 🟢 |

**Functions:**

#### `_should_preserve_job_status(status: str) -> bool`
- **Purpose:** Check if a job status is terminal/actionable and should not be overwritten by re-score.
- **Called by:** `_run_reevaluate_jobs`, `main.py`
- **Side effects:** none (pure)
- **Hardcodes:** none (uses module constant)
- **Flag:** 🟢 CLEAN

#### `_job_eval_document(lead: dict) -> str`
- **Purpose:** Format a job lead into a plain-text evaluation document for the evaluator agent.
- **Called by:** `ghost.py:_phase_eval`, `_run_scan` (duplicated inline), `main.py`
- **Side effects:** none (pure)
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — `_run_scan` does NOT use this function; it duplicates the formatting inline (lines 340-346)

#### `async _run_reevaluate_jobs() -> None`
- **Purpose:** Re-evaluate all stored job leads against current profile. Iterates leads, scores each, persists.
- **Called by:** `ScanManager._run_reevaluate_jobs_task`
- **Calls:** `db.client.get_settings`, `db.client.get_job_leads_for_evaluation`, `db.client.get_lead_by_id`, `db.client.update_lead_score`, `db.client.get_profile`, `agents.evaluator.score`, `_job_eval_document`, `_should_preserve_job_status`
- **Side effects:** DB writes, WS broadcasts
- **Hardcodes:** checks `_reevaluate_stop` event mid-loop
- **Flag:** 🟢 CLEAN

#### `async _run_scan() -> None`
- **Purpose:** Full scan cycle: X scan, free source scan, query gen, scout, LLM evaluation.
- **Called by:** `ScanManager._run_scan_task`
- **Calls:** X/free source scouts, query gen, scout, evaluator, `_job_targets`, `_profile_for_discovery`, `resolve_secret`
- **Side effects:** DB writes, WS broadcasts, external HTTP/scraping
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — duplicates `_job_eval_document` logic inline (lines 340-346) instead of calling the shared function

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ScanManager` | `ghost.py:14`, `tests/test_scan_manager.py:3`, `tests/test_ghost_service.py:4` |
| `scan_manager` | `ghost.py:14`, `routes/scan.py:8` (as `scanner.scan_manager`) |
| `_job_eval_document` | `ghost.py:14`, `main.py:186` |
| `_should_preserve_job_status` | `main.py:186` |

---

### `services/scout.py`

**Purpose:** Provides the two signal-scan entry points: `_run_x_signal_scan` (X/Twitter) and `_run_free_source_scan` (GitHub/HN/Reddit/custom connectors). These are called by both the scan and ghost pipelines.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | both functions | 🟢 — standard |
| `core.ws_manager.cm` | local | both functions | 🟢 — clean |
| `core.config_constants._log` | local | both functions | 🟢 — clean |
| `services.job_targets._profile_x_queries` | local | `_run_x_signal_scan` | 🟢 — clean |
| `services.job_targets._profile_free_source_targets` | local | `_run_free_source_scan` | 🟢 — clean |
| `services.job_targets._has_x_token` | local | `_run_x_signal_scan` | 🟢 — clean |
| `services.job_targets._int_cfg` | local | both functions | 🟢 — clean |
| `services.job_targets._truthy` | local | `_run_x_signal_scan` | 🟢 — clean |
| `services.job_targets._free_sources_enabled` | local | `_run_free_source_scan` | 🟢 — clean |
| `services.job_targets._broadcast_x_source_errors` | local | `_run_x_signal_scan` | 🟢 — clean |
| `log_context` (new/set/reset_context) | local | both functions | 🟢 — clean |
| `config.settings` (as `_cfg`) | local | `_run_x_signal_scan` | 🟢 — clean |
| `config.secrets.resolve_secret` | local | `_run_x_signal_scan` | 🟢 — clean |

**Module-level constants & state:** None.

**Functions:**

#### `async _run_x_signal_scan(cfg: dict, kind_filter: str, profile: dict | None = None) -> list[dict]`
- **Purpose:** Scan X/Twitter for job-lead signals using the `x_scout` agent. Overrides `kind_filter` to `"job"` unconditionally.
- **Called by:** `ghost.py:_phase_x_scan`, `scanner.py:_run_scan`
- **Calls:** `agents.x_scout.run`, `_has_x_token`, `_profile_x_queries`, `_int_cfg`, `_truthy`, `_broadcast_x_source_errors`, `resolve_secret`, `cm.broadcast`
- **Side effects:** WS broadcasts, external HTTP (X API), agent execution
- **Hardcodes:** threshold defaults: max_requests=5, max_results=50, min_signal=55, hot_threshold=80
- **Flag:** 🟢 — `kind_filter` param removed (was dead)

#### `async _run_free_source_scan(cfg: dict, kind_filter: str | None = None, profile: dict | None = None) -> list[dict]`
- **Purpose:** Scan free sources (GitHub/HN/Reddit/custom connectors) for signals.
- **Called by:** `ghost.py:_phase_free_scan`, `scanner.py:_run_scan`, `routes/scan.py`
- **Calls:** `agents.free_scout.run`, `_free_sources_enabled`, `_profile_free_source_targets`, `_int_cfg`, `_truthy`, `cm.broadcast`
- **Side effects:** WS broadcasts, external HTTP, agent execution
- **Hardcodes:** `kind_filter` overwritten to `"job"` (line 109); threshold defaults: max_requests=20, min_signal=60
- **Flag:** 🟡 SUSPECT — same dead `kind_filter` parameter pattern as `_run_x_signal_scan`

**Exports:**

| Export | Known importers |
|--------|----------------|
| `_run_x_signal_scan` | `ghost.py:15`, `scanner.py:17` |
| `_run_free_source_scan` | `ghost.py:15`, `scanner.py:17`, `routes/scan.py:13` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P1 | ✅ RESOLVED | X query templates | `job_targets.py:302-304` | Wired to `settings.scraping.limits.x_query_template` / `x_query_alt_template` |
| P1 | ✅ RESOLVED | Free source query templates | `job_targets.py:281-285` | Wired to `settings.scraping.limits.free_source_query_template` |
| P1 | ✅ RESOLVED | Anthropic API URL + probe model | `provider_probe.py:38-46` | URL wired to `api_urls.anthropic_api_base`, model to `limits.probe_anthropic_model` |
| P1 | ✅ RESOLVED | Probe timeout | `provider_probe.py:35` | Wired to `settings.scraping.timeouts.default_http` |
| P1 | 🟣 COUPLED | `_fire_blocker` circular import | `ghost.py:243` | Deferred to structural refactor |
| P1 | 🟣 COUPLED | `scan_manager._ghost_lock` direct access | `ghost.py:268` | Deferred to structural refactor |
| P2 | ✅ RESOLVED | `_run_scan` duplicates `_job_eval_document` | `scanner.py:340-346` | Replaced inline formatting with `_job_eval_document()` call |
| P2 | ✅ RESOLVED | `kind_filter` overwritten | `scout.py:47,109` | Removed dead param from both functions; updated callers |
| P2 | ✅ RESOLVED | `_job_targets` unused `market_focus` | `job_targets.py:169` | Removed parameter |
| P2 | ✅ RESOLVED | `_profile_x_queries` unused `market_focus` | `job_targets.py:288` | Removed parameter |
| P2 | 🟡 SUSPECT | Raw SQL in `_generate_one` | `generator.py:101-106` | Noted — requires db.client refactor, deferred |
| P3 | 🟢 CLEAN | All items not flagged above | — | See per-function flags above |

---

## 5. Dependencies

**Inbound (other units depend on this):**

| Consumer unit | What they import |
|---------------|------------------|
| `routes/settings.py` | `get_job_targets`, `get_blocked_markers`, `save_job_targets`, `validate_job_targets`, `validate_blocked_markers`, `_ghost_tick`, `_sensitive`, `_probe_provider_key`, `_log_sensitive_deprecation` |
| `routes/scan.py` | `scanner.scan_manager`, `_profile_for_discovery`, `_run_free_source_scan` |
| `routes/actions.py` | `_fire_blocker`, `_actuate` |
| `routes/leads.py` | `_generate_one` |
| `main.py` | `_ghost_tick`, `_job_targets`, `_profile_for_discovery`, `_should_preserve_job_status`, `_job_eval_document`, `_fire_blocker`, `_generate_one`, `_sensitive` |
| `tests/test_ghost_service.py` | `GhostService`, `ScanManager` |
| `tests/test_scan_manager.py` | `ScanManager` |
| `tests/test_regressions.py` | `_split_configured_targets`, `validate_job_targets` |

**Outbound (this unit depends on others):**

| Dependency unit | Used by | What's used |
|-----------------|---------|-------------|
| `agents/` | generator, ghost, scanner | `generator.run_package`, `contact_lookup.run`, `actuator.run`, `evaluator.score`, `scout.run`, `query_gen.generate`, `x_scout`, `free_scout` |
| `db.client` | generator, ghost, job_targets, scanner | `get_lead_by_id`, `save_asset_package`, `save_contact_lookup`, `get_setting`/`get_settings`/`save_settings`, `get_profile`, `get_discovered_leads`, `update_lead_score`, `get_job_leads_for_evaluation`, `get_lead_for_fire`, `mark_applied`, `get_sql_connection` |
| `core.ws_manager` | all files | `cm.broadcast` |
| `core.config_constants` | ghost, provider_probe, scanner, scout | `_log` |
| `config` | ghost, job_targets, provider_probe, scanner, scout | `settings` object |
| `config.secrets` | ghost, job_targets, scanner, scout | `resolve_secret` |
| `log_context` | ghost, scout | `new_context`, `set_context`, `reset_context` |
| `llm` | provider_probe | `_OPENAI_COMPAT_BASE_URLS` |
| `main` | ghost | `_fire_blocker` (circular import workaround) |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `httpx` | HTTP requests in provider probe | loose | 🟢 — standard choice |
| `fastapi` | HTTPException | >=0.136.1 | 🟢 — standard |

---

## 6. First principles assessment

### `services/__init__.py`
1. **Does this file need to exist?** Yes — empty `__init__.py` makes `services` a package.
2. **Does it do what it claims?** Yes — it's empty.
3. **Is it the right place?** Yes.
4. **What would break if deleted?** All `from services.* import` statements would fail.

### `services/generator.py`
1. **Does this file need to exist?** Yes — owns generation and actuation orchestration.
2. **Does it do what it claims?** Yes — title matches: "generation with fire blocking".
3. **Is it the right place for this logic?** Partially — `_fire_blocker` being re-imported from `main.py` in `ghost.py` indicates an ownership ambiguity.
4. **What would break if deleted?** `routes/actions.py` submit/actuate endpoints, `routes/leads.py` generation route, `main.py` startup registration.

### `services/ghost.py`
1. **Does this file need to exist?** Yes — central to the ghost-mode automation feature.
2. **Does it do what it claims?** Yes — orchestrates the 7-phase ghost pipeline.
3. **Is it the right place for this logic?** Yes — service layer is appropriate.
4. **What would break if deleted?** `_ghost_tick` scheduler in `main.py`, settings ghost trigger in `routes/settings.py`.

### `services/job_targets.py`
1. **Does this file need to exist?** Yes — consolidates all job-target config logic.
2. **Does it do what it claims?** Yes — name matches: target resolution, settings accessors, validation.
3. **Is it the right place for this logic?** Yes — these are service-level operations.
4. **What would break if deleted?** All scan/ghost pipelines (no targets to scan), settings CRUD for targets.

### `services/provider_probe.py`
1. **Does this file need to exist?** Yes — provides API key health checking for provider config.
2. **Does it do what it claims?** Yes — title matches: "LLM provider API key health checking".
3. **Is it the right place for this logic?** Yes — it is a lightweight service function.
4. **What would break if deleted?** Provider key validation in settings route would be missing.

### `services/scanner.py`
1. **Does this file need to exist?** Yes — owns scan lifecycle state machine and pipelines.
2. **Does it do what it claims?** Yes — title matches: "Scan orchestration and state management".
3. **Is it the right place for this logic?** Yes — service layer is appropriate.
4. **What would break if deleted?** All scan/reevaluate API endpoints in `routes/scan.py`, ghost mode's lock coordination, `_ghost_tick` in `main.py`.

### `services/scout.py`
1. **Does this file need to exist?** Yes — provides the two signal-scan entry points.
2. **Does it do what it claims?** Yes — title matches: "X/Twitter and free source signal scanning".
3. **Is it the right place for this logic?** Yes — service layer dispatch is appropriate; agent-level logic stays in `agents/`.
4. **What would break if deleted?** Scan and ghost pipelines would lose X/free-source scanning.
