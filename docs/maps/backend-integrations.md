# Map: Backend Integrations

**File:** `docs/maps/backend-integrations.md`
**Codebase path(s):** `backend/agents/`
**Files in scope:** 9 (8 source + `__init__.py`)
**Total lines:** ~1,873
**Generated:** 2026-05-15

---

## 1. Unit summary

The backend-integrations unit owns all third-party integration agents in the justHireMe sidecar backend: browser automation (Playwright), contact enrichment (Hunter.io/Proxycurl), in-app help (LLM + hardcoded guides), form-field selectors (OTA), Chromium runtime management, and data ingestion from GitHub, LinkedIn exports, and personal portfolio sites. It depends on `config` for settings, `llm` for LLM calls, `db.client` for settings storage, and `logger` for structured logging. Other units (routes, services) consume it via lazy imports — every public function is imported inline to avoid circular imports at module load time.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `agents/__init__.py` | 0 | empty package marker | 🟢 CLEAN |
| 2 | `agents/actuator.py` | 455 | experimental auto-apply browser automation with vision fallback | 🟠 STALE — experimental, gated, heavily hardcoded |
| 3 | `agents/contact_lookup.py` | 218 | Hunter.io + Proxycurl company contact enrichment | 🟢 CLEAN — well-structured, config-driven |
| 4 | `agents/help_agent.py` | 466 | in-app help system with LLM + deterministic fallback | 🟠 STALE — 300+ lines hardcoded guide text, model lists will stale |
| 5 | `agents/selectors.py` | 84 | OTA form selectors with remote→cache→bundled fallback | 🟢 CLEAN — well-layered fallback, reasonable TTL |
| 6 | `agents/browser_runtime.py` | 164 | cross-platform Chromium discovery + download | 🟢 CLEAN — well-structured, tested |
| 7 | `agents/github_ingestor.py` | 189 | GitHub profile/project ingestion via API + LLM | 🟢 CLEAN — well-scoped, typed extraction |
| 8 | `agents/linkedin_parser.py` | 131 | LinkedIn data export ZIP parser | 🟢 CLEAN — focused, deterministic CSV parsing |
| 9 | `agents/portfolio_ingestor.py` | 165 | personal portfolio ingestion via Playwright→HTTP→raw | 🟡 SUSPECT — nested imports, regex HTML stripping, brittle |

---

## 3. Detailed breakdown

### `agents/__init__.py`

**Purpose:** Empty file marking the `agents` package. No logic.

**Imports:** None.

**Module-level constants & state:** None.

**Exports:** None.

---

### `agents/actuator.py`

**Purpose:** Experimental auto-apply browser automation. `read_form()` detects and reads OTA job application form fields. `run()` fills fields via DOM selectors, falls back to vision-based (screenshot→LLM→coordinates) clicking/typing, and conditionally submits the form. Gated behind `JHM_AUTO_APPLY` env var for the submission step. The "run" name conflicts with `run` in `contact_lookup.py` and other modules — callers import as `_act`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import asyncio` | stdlib | yes (line 454) | 🟢 |
| `import base64` | stdlib | yes (lines 118, 325, 411, 430) | 🟢 |
| `import json` | stdlib | yes (line 237) | 🟢 |
| `import os` | stdlib | yes (lines 13, 168, 364) | 🟢 |
| `import sys` | stdlib | no | 🔴 DEAD — unused import |
| `from pydantic import BaseModel, Field` | 3rd-party | yes (lines 205-213) | 🟢 |
| `from typing import List` | stdlib | yes (line 213) | 🟢 |
| `from config import settings` | local | yes (line 13) | 🟢 |
| `from logger import get_logger` | local | yes (line 11) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_AUTO_APPLY_ENABLED` | bool | env var `JHM_AUTO_APPLY` | `_run()` line 420 | 🟢 — gated by config |
| `_TYPE_TO_CANDIDATE_KEY` | dict | field-name->lambda map | `resolve_answer()` | 🟢 — clean mapping |
| `_DOM_MAP` | list[tuple] | 18 hardcoded CSS selector→field pairs | `_fill_dom()` | 🔵 HARDCODED — selectors baked in, should derive from selectors.json |
| `_FILL_DELAY` | int | 500 | `_fill_dom`, `_fill_vision`, `_upload_resume` | 🔵 HARDCODED — should be configurable |
| `_VISION_SYSTEM` | str | multi-line system prompt | `_vision_actions_anthropic`, `_vision_actions_openai_compatible` | 🔵 HARDCODED — large hardcoded prompt |

**Classes:**

#### `_Act(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Single vision action (click or type at coordinates)
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| — | — | — | data model with `kind`, `x`, `y`, `text` | 🟢 |

#### `_Acts(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Container for list of `_Act` actions
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| — | — | — | data model with `actions: List[_Act]` | 🟢 |

**Functions:**

#### `resolve_answer(field_type: str, candidate: dict) -> str`
- **Purpose:** Extract candidate value for a given field type using the lambda map
- **Called by:** `read_form` line 78
- **Calls:** `_TYPE_TO_CANDIDATE_KEY.get()`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `async read_form(url, candidate, cover_letter) -> dict`
- **Purpose:** Navigate to job URL, detect platform, match fields to candidate, return structured field results with screenshot
- **Called by:** `routes/actions.py:107`
- **Calls:** `launch_chromium`, `get_selectors`, `detect_platform`, `get_platform_fields`, `resolve_answer`, `page.screenshot`
- **Side effects:** launches Playwright browser, navigates to URL
- **Hardcodes:** viewport 1280×900, user-agent string, `wait_until="domcontentloaded"`, timeout 20000, wait_for_timeout 2000, `covered_words` set
- **Flag:** 🔵 HARDCODED — viewport, UA, timeouts, label-filter words all baked in

#### `async _upload_resume(p, asset) -> bool`
- **Purpose:** Upload resume file via `<input type='file'>`
- **Called by:** `_fill_dom`, `_fill_vision` (implicitly through `_run`)
- **Calls:** `page.locator`, `set_input_files`
- **Side effects:** file I/O (`os.path.isfile`)
- **Hardcodes:** `input[type='file']` selector, timeout 5000
- **Flag:** 🟢 — pragmatic, low-risk

#### `async _fill_dom(p, j, a) -> dict`
- **Purpose:** Fill form fields using hardcoded DOM selector map
- **Called by:** `_run` line 391
- **Calls:** `_upload_resume`, iterates `_DOM_MAP`
- **Side effects:** mutates browser DOM
- **Hardcodes:** `_DOM_MAP` selectors, timeout 2000/3000, `_FILL_DELAY`
- **Flag:** 🔵 HARDCODED — selectors should come from selectors.json

#### `_ready_to_submit(result) -> bool`
- **Purpose:** Check if enough fields were filled to attempt submission
- **Called by:** `_run` lines 395, 404
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 — clean boolean logic

#### `_parse_actions(text: str) -> _Acts`
- **Purpose:** Parse JSON action text into `_Acts` model, with manual JSON extraction fallback
- **Called by:** `_vision_actions_openai_compatible`
- **Calls:** `_Acts.model_validate_json`, `json.loads`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 — robust parsing with fallback

#### `_vision_actions_anthropic(model, key, b64, ctx) -> _Acts`
- **Purpose:** Call Anthropic API with screenshot for vision-based form filling
- **Called by:** `_vision_actions`
- **Calls:** `anthropic.Anthropic().messages.parse()`
- **Side effects:** external API call
- **Hardcodes:** timeout 120.0, max_tokens 2048
- **Flag:** 🟢 — clean typed API call

#### `_vision_actions_openai_compatible(provider, model, key, b64, ctx) -> _Acts`
- **Purpose:** Call OpenAI-compatible API (OpenAI, Groq, NVIDIA, Ollama) with screenshot
- **Called by:** `_vision_actions`
- **Calls:** `OpenAI().chat.completions.create()`, `_parse_actions`
- **Side effects:** external API call
- **Hardcodes:** Groq base URL `https://api.groq.com/openai/v1`, NVIDIA `https://integrate.api.nvidia.com/v1`, Ollama `http://localhost:11434/v1` (from `get_setting`), `enable_thinking: False` for NVIDIA
- **Flag:** 🔵 HARDCODED — provider base URLs baked in

#### `_vision_actions(b64, ctx) -> _Acts`
- **Purpose:** Dispatch to vision provider based on resolved LLM config
- **Called by:** `_fill_vision` via `asyncio.to_thread`
- **Calls:** `resolve_config("actuator")`, provider dispatch
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 — clean dispatch

#### `async _fill_vision(p, j, a) -> int`
- **Purpose:** Take screenshot, call vision LLM, execute returned click/type actions on page
- **Called by:** `_run` line 397
- **Calls:** `page.screenshot`, `asyncio.to_thread(_vision_actions)`, `page.mouse.click`, `page.keyboard.type`
- **Side effects:** mutates browser DOM
- **Hardcodes:** cover_letter truncated to 1500 chars, type delay 40ms
- **Flag:** 🟡 SUSPECT — cover letter truncated in context (1500 chars), may silently lose data

#### `async _find_submit(p)`
- **Purpose:** Find submit button by iterating hardcoded selectors
- **Called by:** `_run` line 403
- **Calls:** `page.locator`, `wait_for`
- **Side effects:** none
- **Hardcodes:** 6 hardcoded CSS/text selectors, timeout 2000
- **Flag:** 🔵 HARDCODED — submit-button selectors should come from selectors.json

#### `async _run(job, asset, dry_run) -> bool | dict`
- **Purpose:** Full auto-apply pipeline: launch browser, fill DOM, fall back to vision, find submit, optionally submit
- **Called by:** `run()` (synchronous wrapper)
- **Calls:** `launch_chromium`, `_fill_dom`, `_fill_vision`, `_find_submit`, `_ready_to_submit`, `page.screenshot`
- **Side effects:** launches Playwright, navigates URLs, optionally submits form
- **Hardcodes:** viewport, user-agent, wait_until, timeout 30000, `slow_mo` values
- **Flag:** 🟣 COUPLED — deeply coupled to Playwright lifecycle, many hardcoded values, complex state machine

#### `run(job, asset, dry_run) -> bool | dict`
- **Purpose:** Synchronous entry point wrapping `_run` via `asyncio.run()`
- **Called by:** `services/generator.py:146`, `services/ghost.py:236`, `routes/actions.py:202`
- **Calls:** `asyncio.run(_run(...))`
- **Side effects:** none (delegates)
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — `asyncio.run()` in async context (FastAPI) may raise "already running" errors; callers seem to invoke via `asyncio.to_thread` but it's fragile

**Exports:**

| Export | Known importers |
|--------|----------------|
| `read_form` | `routes/actions.py` |
| `run` | `services/generator.py`, `services/ghost.py`, `routes/actions.py` |

---

### `agents/contact_lookup.py`

**Purpose:** Company contact enrichment via Hunter.io (email lookup) and Proxycurl (LinkedIn URL resolution). `run(lead)` infers the company domain from a job posting, queries Hunter for contacts, optionally resolves LinkedIn URLs via Proxycurl, and generates a personalized outreach email draft. Well-factored into single-responsibility helpers.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import json` | stdlib | yes (line 63) | 🟢 |
| `import os` | stdlib | no | 🔴 DEAD — unused import |
| `import re` | stdlib | yes (lines 103-113, 147) | 🟢 |
| `import urllib.parse` | stdlib | yes (lines 29, 59, 94, 124, 129) | 🟢 |
| `import urllib.request` | stdlib | yes (lines 60-62) | 🟢 |
| `import config as cfg` | local | yes (lines 15, 16, 147, 183-191) | 🟢 |
| `from db.client import get_profile, get_settings` | local | yes (lines 135, 139, 175) | 🟢 |
| `from logger import get_logger` | local | yes (line 11) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `ATS_HOSTS` | set | from `cfg.settings.contact.ats_hosts.hosts` | `_domain_from_url` | 🟢 — config-driven |
| `CONTACT_PRIORITY` | tuple | from `cfg.settings.contact.priority_roles.roles` | `_contact_score` | 🟢 — config-driven |

**Classes:** None.

**Functions:**

#### `_setting(settings, *keys) -> str`
- **Purpose:** Get first non-empty value from settings dict for any of the key names
- **Called by:** `_infer_company_domain`, `run`
- **Calls:** `settings.get()`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `_domain_from_url(url) -> str`
- **Purpose:** Extract registered domain (e.g., `example.com`) from a URL, skip ATS hosts
- **Called by:** `_domain_from_meta`, `_infer_company_domain`
- **Calls:** `urllib.parse.urlparse`
- **Side effects:** none
- **Hardcodes:** strips `www.` prefix
- **Flag:** 🟢

#### `_domain_from_meta(lead) -> str`
- **Purpose:** Extract domain from lead's `source_meta` dict
- **Called by:** `_infer_company_domain`
- **Calls:** `_domain_from_url`
- **Side effects:** none
- **Hardcodes:** checks `company_domain`, `domain`, `website` keys
- **Flag:** 🟢

#### `_infer_company_domain(lead, settings) -> str`
- **Purpose:** Infer company domain from override, meta, or job URL
- **Called by:** `run`
- **Calls:** `_setting`, `_domain_from_meta`, `_domain_from_url`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 — clean priority chain

#### `_json_get(url, headers, timeout) -> dict`
- **Purpose:** Low-level HTTP GET returning parsed JSON
- **Called by:** `_hunter_contacts`, `_proxycurl_linkedin`
- **Calls:** `urllib.request.urlopen`
- **Side effects:** network I/O
- **Hardcodes:** default User-Agent `"JustHireMe/1.0"`, default timeout 12
- **Flag:** 🔵 HARDCODED — user-agent string and timeout are hardcoded defaults (though timeout matches config)

#### `_clean_contact(raw) -> dict`
- **Purpose:** Normalize raw Hunter.io contact into standard shape
- **Called by:** `_hunter_contacts`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** maps `position` or `title`, `value` or `email`
- **Flag:** 🟢

#### `_contact_score(contact) -> tuple[int, int]`
- **Purpose:** Compute sort key (priority, confidence) for ranking contacts
- **Called by:** `_hunter_contacts` (sort key)
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `_hunter_contacts(domain, key) -> list[dict]`
- **Purpose:** Query Hunter.io API for company emails
- **Called by:** `run`
- **Calls:** `_json_get`, `_clean_contact`, `_contact_score`
- **Side effects:** external API call
- **Hardcodes:** limit=10 (matches config)
- **Flag:** 🟢 — config-driven via settings

#### `_extract_manager_name(text) -> str`
- **Purpose:** Extract hiring manager name from job description text with regex
- **Called by:** `_proxycurl_linkedin`
- **Calls:** `re.search`
- **Side effects:** none
- **Hardcodes:** 4 regex patterns (matches config)
- **Flag:** 🟢 — patterns live in config

#### `_proxycurl_linkedin(domain, key, contact, lead) -> str`
- **Purpose:** Resolve LinkedIn profile URL via Proxycurl API
- **Called by:** `run`
- **Calls:** `_json_get`, `_extract_manager_name`
- **Side effects:** external API call
- **Hardcodes:** API URL `https://nubela.co/proxycurl/api/linkedin/profile/resolve` (matches config)
- **Flag:** 🟢

#### `_candidate_name() -> str`
- **Purpose:** Get the user's name from profile or settings
- **Called by:** `_personalized_email`
- **Calls:** `get_profile`, `get_settings`
- **Side effects:** DB read
- **Hardcodes:** fallback `"Candidate"`
- **Flag:** 🟢

#### `_skills_line(lead) -> str`
- **Purpose:** Build a comma-separated skills string from lead's tech_stack or regex-detect from description
- **Called by:** `_personalized_email`
- **Calls:** `re.findall` with pattern from config
- **Side effects:** none
- **Hardcodes:** `"ci/cd"` upper-case special case, fallback message string
- **Flag:** 🔵 HARDCODED — `"ci/cd"` normalization, fallback string

#### `_personalized_email(lead, contact) -> str`
- **Purpose:** Generate a short personalized outreach email draft
- **Called by:** `run`
- **Calls:** `_candidate_name`, `_skills_line`
- **Side effects:** none
- **Hardcodes:** email template string
- **Flag:** 🟢 — template is reasonable, intentionally hardcoded

#### `run(lead) -> dict`
- **Purpose:** Main entry: infer domain, call Hunter/Proxycurl, return contacts with email draft
- **Called by:** `services/generator.py:74`
- **Calls:** `_setting`, `_infer_company_domain`, `resolve_secret`, `_hunter_contacts`, `_proxycurl_linkedin`, `_personalized_email`
- **Side effects:** reads settings from DB, makes external API calls
- **Hardcodes:** none
- **Flag:** 🟢 — clean, well-factored

**Exports:**

| Export | Known importers |
|--------|----------------|
| `run` | `services/generator.py` |

---

### `agents/help_agent.py`

**Purpose:** In-app help/FAQ agent. Answers user questions about JustHireMe usage. Uses topic classification to either return a deterministic fallback answer or call the LLM with focused product knowledge. The guides are ~300 lines of hardcoded prose embedded in the source file.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes (type hints) | 🟢 |
| `import re` | stdlib | yes (lines 305, 306) | 🟢 |
| `from pathlib import Path` | stdlib | yes (lines 262, 267) | 🟢 |
| `from llm import call_raw, resolve_config` | local | yes (lines 428, 459) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_DOCS` | tuple[str] | 4 doc file paths | `_knowledge()`, `_focused_knowledge()` | 🟢 — DRY path list |
| `_USER_GUIDE` | str | ~150 lines hardcoded text | `_knowledge()`, `_focused_knowledge()` | 🟠 STALE — huge inline string, India market section baked in |
| `_PROVIDER_GUIDE` | str | ~33 lines hardcoded | `_focused_knowledge()` | 🟠 STALE — model names will go out of date |
| `_SOURCE_GUIDE` | str | ~30 lines hardcoded | `_focused_knowledge()` | 🟢 — stable reference info |
| `_WORKFLOW_GUIDE` | str | ~10 lines hardcoded | `_focused_knowledge()`, `_fallback()` | 🟢 — stable |
| `_CUSTOMIZE_GUIDE` | str | ~10 lines hardcoded | `_focused_knowledge()` | 🟢 — stable |

**Classes:** None.

**Functions:**

#### `_repo_root() -> Path`
- **Purpose:** Resolve repository root (3 levels up from this file)
- **Called by:** `_read_doc`
- **Calls:** `Path(__file__).resolve().parents[2]`
- **Side effects:** none
- **Hardcodes:** `parents[2]` assumes file is at `backend/agents/help_agent.py`
- **Flag:** 🟢 — standard pattern

#### `_read_doc(path, limit) -> str`
- **Purpose:** Read a doc file from repo root, truncated to `limit` chars
- **Called by:** `_knowledge`
- **Calls:** `_repo_root()`, `file.read_text()`
- **Side effects:** file I/O
- **Hardcodes:** limit default 9000
- **Flag:** 🟢

#### `_knowledge() -> str`
- **Purpose:** Build full product knowledge string (brief + user guide + docs)
- **Called by:** not currently called (superseded by `_focused_knowledge`)
- **Calls:** `_read_doc` for each `_DOCS` path
- **Side effects:** file I/O
- **Hardcodes:** product brief string
- **Flag:** 🟡 SUSPECT — `_focused_knowledge` is used instead, `_knowledge` may be dead

#### `_words(question) -> set[str]`
- **Purpose:** Extract lowercase alphanumeric tokens from question
- **Called by:** `_topic`
- **Calls:** `re.findall`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `_topic(question) -> str`
- **Purpose:** Classify question into topic: providers, sources, customize, workflow, auto_apply, install, general
- **Called by:** `answer`, `_focused_knowledge`, `_fallback`
- **Calls:** `_words`
- **Side effects:** none
- **Hardcodes:** keyword-based classification rules
- **Flag:** 🟢 — pragmatic keyword matching

#### `_focused_knowledge(question) -> str`
- **Purpose:** Return topic-focused subset of knowledge (capped at 5500 chars)
- **Called by:** `answer`
- **Calls:** `_topic`, string slicing of guide constants
- **Side effects:** none
- **Hardcodes:** product brief string, chunk mapping, 5500 char limit
- **Flag:** 🟡 SUSPECT — `_USER_GUIDE` is sliced by `str.find()`, fragile to text changes

#### `_steps(title, items) -> str`
- **Purpose:** Format numbered steps from title + list
- **Called by:** `_fallback`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `_fallback(question) -> str`
- **Purpose:** Deterministic fallback answer without LLM. Returns topic-specific or general steps.
- **Called by:** `answer` (lines 441, 465)
- **Calls:** `_topic`, `_steps`
- **Side effects:** none
- **Hardcodes:** every answer string, provider list with specific model names
- **Flag:** 🟠 STALE — model names (grok-4, kimi-k2-turbo-preview) will go stale; maintained manually alongside `_PROVIDER_GUIDE`

#### `answer(question, history) -> dict`
- **Purpose:** Main entry: classify topic, return fallback for stable topics or call LLM for general
- **Called by:** `routes/scan.py:122`, `routes/misc.py:142`
- **Calls:** `resolve_config("help")`, `_topic`, `_fallback`, `call_raw`, `_focused_knowledge`
- **Side effects:** LLM API call (for general queries)
- **Hardcodes:** limits history to last 8 messages, 1000 chars each; max response 4000 chars
- **Flag:** 🟢 — clean hybrid approach

**Exports:**

| Export | Known importers |
|--------|----------------|
| `answer` | `routes/scan.py`, `routes/misc.py` |

---

### `agents/selectors.py`

**Purpose:** OTA form-field selectors management. Provides remote→cache→bundled fallback chain for CSS selector configurations used by `actuator.py`'s form reading. Bundled default living at `backend/data/selectors.json`. `detect_platform()` and `get_platform_fields()` are the utility consumers.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes (type hints) | 🟢 |
| `import json` | stdlib | yes (lines 17, 33, 41, 51) | 🟢 |
| `import time` | stdlib | yes (line 29) | 🟢 |
| `from pathlib import Path` | stdlib | yes (line 16) | 🟢 |
| `from logger import get_logger` | local | yes (line 7) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_BUNDLED` | Path | `backend/data/selectors.json` | `_load_bundled` | 🟢 |
| `_CACHE_KEY` | str | `"selectors_json"` | `get_selectors` | 🟢 |
| `_CACHE_TS_KEY` | str | `"selectors_fetched_at"` | `get_selectors` | 🟢 |
| `_TTL` | int | 86400 (24h) | `get_selectors` | 🔵 HARDCODED — should be configurable |

**Classes:** None.

**Functions:**

#### `_load_bundled() -> dict`
- **Purpose:** Load bundled selectors JSON from disk
- **Called by:** `get_selectors` (final fallback)
- **Calls:** `Path.open`, `json.load`
- **Side effects:** file I/O
- **Hardcodes:** `_BUNDLED` path
- **Flag:** 🟢

#### `get_selectors() -> dict`
- **Purpose:** Return selectors config: fresh remote → cached → bundled, never raises
- **Called by:** `actuator.py:53`, `routes/actions.py:179`
- **Calls:** `get_setting`, `save_settings`, `httpx.get`, `_load_bundled`
- **Side effects:** may fetch HTTP, may write settings cache
- **Hardcodes:** remote fetch timeout 8s
- **Flag:** 🟢 — clean fallback chain, never raises

#### `detect_platform(url, selectors) -> str | None`
- **Purpose:** Detect platform (workday, greenhouse, etc.) from URL substring matching
- **Called by:** `actuator.py:54`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `get_platform_fields(url, selectors) -> list[dict]`
- **Purpose:** Return ordered field selectors: platform-specific first, then generic for uncovered types
- **Called by:** `actuator.py:55`
- **Calls:** `detect_platform`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `get_selectors` | `actuator.py`, `routes/actions.py` |
| `detect_platform` | `actuator.py` |
| `get_platform_fields` | `actuator.py` |

---

### `agents/browser_runtime.py`

**Purpose:** Cross-platform Chromium/Playwright runtime management. Discovers browser binaries via env vars, platform-specific paths, or `shutil.which()`. Downloads bundled Chromium from GitHub releases if no local browser found. Entry point `launch_chromium()` provides a unified launcher with graceful fallback.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes (type hints) | 🟢 |
| `import os` | stdlib | yes (lines 22, 26, 30, 50, 59, 66, 154) | 🟢 |
| `import platform` | stdlib | yes (line 35) | 🟢 |
| `import shutil` | stdlib | yes (lines 61, 87, 132, 133) | 🟢 |
| `import sys` | stdlib | yes (line 26) | 🟢 |
| `import tempfile` | stdlib | yes (line 109) | 🟢 |
| `import urllib.request` | stdlib | yes (line 112) | 🟢 |
| `import zipfile` | stdlib | yes (line 115) | 🟢 |
| `from pathlib import Path` | stdlib | yes (lines 24-31, 96-97, etc.) | 🟢 |
| `from logger import get_logger` | local | yes (line 14) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_RELEASE_DOWNLOAD_BASE` | str | GitHub releases URL | `browser_runtime_url()` | 🔵 HARDCODED — repo-specific, backed by env var override |

**Classes:** None.

**Functions:**

#### `browser_runtime_dir() -> Path`
- **Purpose:** Determine Playwright browser storage directory: env var → OS-specific default
- **Called by:** `browser_runtime_ready`, `ensure_browser_runtime`
- **Calls:** `os.environ.get`, `settings.app.browser.*`, `sys_platform`
- **Side effects:** none
- **Hardcodes:** `"JustHireMe" / "browser-runtime" / "ms-playwright"` subpath
- **Flag:** 🟢 — config-driven with OS defaults

#### `sys_platform() -> str`
- **Purpose:** Normalized OS name
- **Called by:** `browser_runtime_asset_name`, `browser_runtime_dir`
- **Calls:** `platform.system().lower()`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `browser_runtime_asset_name() -> str`
- **Purpose:** Asset filename for bundled browser per platform
- **Called by:** `browser_runtime_url`, `ensure_browser_runtime`
- **Calls:** `sys_platform`
- **Side effects:** none
- **Hardcodes:** `"JustHireMe-browser-runtime-{windows,macos,linux}.zip"`
- **Flag:** 🔵 HARDCODED — naming convention, backed by env var override

#### `browser_runtime_url() -> str`
- **Purpose:** Full download URL: env var override or default GitHub release URL
- **Called by:** `ensure_browser_runtime`
- **Calls:** `os.environ.get`, `browser_runtime_asset_name`
- **Side effects:** none
- **Hardcodes:** constructs fallback URL from hardcoded base + asset name
- **Flag:** 🟢 — env var overrideable

#### `chromium_executable() -> str | None`
- **Purpose:** Locate a browser binary: env var → Playwright env → platform-specific paths → `shutil.which`
- **Called by:** `launch_chromium`, `routes/misc.py:39`
- **Calls:** `shutil.which`, `os.path.exists`
- **Side effects:** none
- **Hardcodes:** Windows: 4 Chrome/Edge paths; Linux: 7 binary names (Chrome, Chromium, Firefox, Brave)
- **Flag:** 🔵 HARDCODED — browser names and Windows paths baked in

#### `browser_runtime_ready(path) -> bool`
- **Purpose:** Check if Playwright Chromium directory exists and contains a chromium folder
- **Called by:** `ensure_browser_runtime`, `tests/test_regressions.py:1194`
- **Calls:** `path.exists()`, `path.iterdir()`
- **Side effects:** none
- **Hardcodes:** checks for directory name starting with `"chromium"`
- **Flag:** 🟢

#### `ensure_browser_runtime() -> Path`
- **Purpose:** Download and extract bundled Chromium from GitHub releases if not ready
- **Called by:** `launch_chromium`
- **Calls:** `browser_runtime_dir`, `browser_runtime_ready`, `urllib.request.urlretrieve`, `zipfile.ZipFile`
- **Side effects:** downloads ~100MB+ zip, extracts to runtime dir, may delete existing dir
- **Hardcodes:** temp dir prefix `"jhm-browser-runtime-"`, checks nested `ms-playwright`
- **Flag:** 🟢 — clean with good error messages

#### `async launch_chromium(playwright, *, headless, **kwargs)`
- **Purpose:** Launch Playwright Chromium with auto-fallback to discovered system browser or downloaded runtime
- **Called by:** `actuator.py`, `portfolio_ingestor.py`, `scout.py`
- **Calls:** `playwright.chromium.launch`, `chromium_executable`, `ensure_browser_runtime`
- **Side effects:** may trigger browser download; sets `os.environ["PLAYWRIGHT_BROWSERS_PATH"]`
- **Hardcodes:** none
- **Flag:** 🟢 — robust 3-tier fallback

**Exports:**

| Export | Known importers |
|--------|----------------|
| `launch_chromium` | `actuator.py`, `portfolio_ingestor.py`, `scout.py` |
| `chromium_executable` | `routes/misc.py` |
| `browser_runtime_ready` | `tests/test_regressions.py` |
| `ensure_browser_runtime` | (internal) |

---

### `agents/github_ingestor.py`

**Purpose:** Ingest a GitHub user's public profile and top repos. Fetches repo metadata, READMEs, then calls LLM to extract structured project summaries (`_RepoExtract`). Filters forks unless starred ≥10. Returns profile additions (projects, skills) in a shape compatible with profile import.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes (type hints) | 🟢 |
| `import asyncio` | stdlib | yes (lines 93, 179) | 🟢 |
| `import base64` | stdlib | yes (line 52) | 🟢 |
| `import re` | stdlib | yes (lines 162, 132) | 🟢 |
| `from pydantic import BaseModel, Field` | 3rd-party | yes (lines 17-22) | 🟢 |
| `from logger import get_logger` | local | yes (line 8) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `GITHUB_API` | str | `"https://api.github.com"` | `ingest_github`, `_fetch`, `_process_repo` | 🔵 HARDCODED — GitHub API base URL |
| `_HEADERS` | dict | Accept/X-GitHub-Api-Version | `_gh_headers` | 🟢 — standard headers |

**Classes:**

#### `_RepoExtract(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Structured LLM extraction result for a single repo
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| — | — | — | data model: `description`, `stack`, `impact`, `is_relevant` | 🟢 |

**Functions:**

#### `_gh_headers(token) -> dict`
- **Purpose:** Build GitHub API headers with optional bearer token
- **Called by:** `_fetch`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `async _fetch(url, token) -> dict | list | None`
- **Purpose:** Async HTTP GET to GitHub API with error handling
- **Called by:** `ingest_github`, `_process_repo`
- **Calls:** `httpx.AsyncClient.get`
- **Side effects:** network I/O
- **Hardcodes:** timeout 10 seconds
- **Flag:** 🔵 HARDCODED — timeout should be configurable

#### `_decode_readme(readme_data) -> str`
- **Purpose:** Decode GitHub API README response (base64-encoded content)
- **Called by:** `_process_repo`
- **Calls:** `base64.b64decode`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢

#### `_truncate(text, max_chars) -> str`
- **Purpose:** Truncate text with ellipsis
- **Called by:** `_extract_project`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** default 3000 chars (same as user prompt)
- **Flag:** 🟢

#### `async _extract_project(repo, readme) -> _RepoExtract | None`
- **Purpose:** Call LLM to extract structured project info from repo metadata + README
- **Called by:** `_process_repo`
- **Calls:** `call_llm` via `asyncio.to_thread`
- **Side effects:** LLM API call
- **Hardcodes:** system prompt, user prompt template, 3000-char README limit
- **Flag:** 🟢 — well-scoped

#### `async ingest_github(username, token, max_repos) -> dict`
- **Purpose:** Main entry: fetch user profile, repos, extract projects via LLM, return profile additions
- **Called by:** `routes/ingest.py:164`
- **Calls:** `_fetch`, `_decode_readme`, `_extract_project`, `asyncio.gather`
- **Side effects:** GitHub API calls, LLM API calls, concurrent processing
- **Hardcodes:** `max_repos` default 12, fork filter threshold 10 stars, skill name max length 40, skill split regex `[,;/]`
- **Flag:** 🔵 HARDCODED — repo count, star threshold, skill name limits baked in

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ingest_github` | `routes/ingest.py` |

---

### `agents/linkedin_parser.py`

**Purpose:** Parse a LinkedIn data export ZIP file into structured profile data. Deterministic CSV parsing — no LLM calls. Handles Profile.csv, Skills.csv, Positions.csv, Education.csv, Projects.csv, Certifications.csv.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes (type hints) | 🟢 |
| `import csv, io, zipfile` | stdlib | yes (lines 8-18) | 🟢 |
| `from logger import get_logger` | local | yes (line 5) | 🟢 |

**Module-level constants & state:** None.

**Classes:** None.

**Functions:**

#### `_read_csv(zf, name) -> list[dict]`
- **Purpose:** Find a CSV by case-insensitive filename pattern in ZIP, parse with DictReader
- **Called by:** `parse_linkedin_export` (for each CSV type)
- **Calls:** `zf.namelist`, `zf.open`, `csv.DictReader`
- **Side effects:** none
- **Hardcodes:** uses `utf-8-sig` for BOM handling
- **Flag:** 🟢 — correct encoding choice

#### `parse_linkedin_export(zip_bytes) -> dict`
- **Purpose:** Main entry: parse full LinkedIn export ZIP into structured profile
- **Called by:** `routes/ingest.py:89`
- **Calls:** `_read_csv` six times
- **Side effects:** none
- **Hardcodes:** 6 hardcoded filenames (`Profile.csv`, `Skills.csv`, etc.), 20+ hardcoded column names (`"First Name"`, `"Last Name"`, `"Headline"`, etc.)
- **Flag:** 🔵 HARDCODED — CSV column names are LinkedIn-format-specific and will break if LinkedIn changes export schema

**Exports:**

| Export | Known importers |
|--------|----------------|
| `parse_linkedin_export` | `routes/ingest.py` |

---

### `agents/portfolio_ingestor.py`

**Purpose:** Ingest a personal portfolio website. Primary path: Playwright browser → page text → LLM extraction. Fallback: HTTP request → regex HTML stripping → raw text. Returns structured profile data in the same shape as `linkedin_parser` output.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes (type hints) | 🟢 |
| `import asyncio` | stdlib | yes (lines 72, 100) | 🟢 |
| `import re` | stdlib | yes (line 160-164) | 🟢 |
| `from pydantic import BaseModel, Field` | 3rd-party | yes (lines 14-30) | 🟢 |
| `from agents.browser_runtime import launch_chromium` | local | yes (line 8) | 🟢 |
| `from logger import get_logger` | local | yes (line 11) | 🟢 |

**Module-level constants & state:** None.

**Classes:**

#### `_PortfolioExtract(BaseModel)`
- **Inherits from:** BaseModel
- **Purpose:** Structured LLM extraction result from portfolio page
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| — | — | — | `candidate_summary`, `skills`, `projects`, `achievements` | 🟢 |

**Functions:**

#### `async ingest_portfolio_url(url) -> dict`
- **Purpose:** Main entry: Playwright→LLM→structured profile; fallback HTTP→raw text
- **Called by:** `routes/ingest.py:332`
- **Calls:** `launch_chromium`, `page.evaluate`, `page.screenshot`, `_fetch_portfolio_text_http`, `call_llm`
- **Side effects:** launches Playwright browser, external API call (LLM), network HTTP call
- **Hardcodes:** timeout 25000, wait_for_timeout 1500, `networkidle` wait strategy, page text limit 6000, embedded JS for text extraction, user-agent, LLM system prompt
- **Flag:** 🟡 SUSPECT — nested imports, regex HTML stripping in fallback is brittle, LLM `_resolve` import bypasses normal `resolve_config`

#### `_fetch_portfolio_text_http(url) -> str`
- **Purpose:** Fallback: plain HTTP GET + regex-based HTML-to-text conversion
- **Called by:** `ingest_portfolio_url`
- **Calls:** `httpx.Client.get`, `re.sub` for tag stripping, `html.unescape`
- **Side effects:** network I/O
- **Hardcodes:** timeout 20, user-agent, regex patterns for stripping tags
- **Flag:** 🟡 SUSPECT — regex HTML parsing is inherently brittle; `re.sub(r"<[^>]+>", " ", text)` is a well-known antipattern

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ingest_portfolio_url` | `routes/ingest.py` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 DEAD | `import sys` | `actuator.py:5` | Unused import |
| P2 | 🟡 SUSPECT | `_knowledge()` | `help_agent.py:275` | Defined but not called — superseded by `_focused_knowledge`, verify |
| P1 | 🔵 HARDCODED | `_DOM_MAP` selectors | `actuator.py:144-162` | 18 hardcoded CSS selectors, should come from selectors.json |
| P1 | 🔵 HARDCODED | `_FILL_DELAY = 500` | `actuator.py:164` | Should be configurable |
| P1 | 🔵 HARDCODED | `_VISION_SYSTEM` prompt | `actuator.py:216-227` | 8-line hardcoded prompt |
| P1 | 🔵 HARDCODED | Provider base URLs | `actuator.py:268-273` | Groq/NVIDIA/Ollama URLs baked in |
| P1 | 🔵 HARDCODED | Submit button selectors | `actuator.py:346-353` | 6 CSS/text selectors, should be in config |
| P2 | 🔵 HARDCODED | Viewport, UA strings, timeouts | `actuator.py:68-73, 378-383` | Multiple baked-in browser config values |
| P2 | 🔵 HARDCODED | `_TTL = 86400` | `selectors.py:12` | Cache TTL should be configurable |
| P2 | 🔵 HARDCODED | `_RELEASE_DOWNLOAD_BASE` | `browser_runtime.py:16` | GitHub URL baked in, has env override |
| P2 | 🔵 HARDCODED | Browser binary names/paths | `browser_runtime.py:70-89` | Hardcoded OS-specific paths |
| P2 | 🔵 HARDCODED | `GITHUB_API` | `github_ingestor.py:10` | Static API URL |
| P2 | 🔵 HARDCODED | HTTP timeout 10s | `github_ingestor.py:35` | Should be configurable |
| P2 | 🔵 HARDCODED | max_repos=12, fork threshold=10 | `github_ingestor.py:132-133` | Magic numbers |
| P2 | 🔵 HARDCODED | CSV column names | `linkedin_parser.py:39-114` | 20+ LinkedIn-format-specific column names |
| P2 | 🔵 HARDCODED | Model names in guides | `help_agent.py:177-194, 362-370` | Will stale as providers release new models |
| P3 | 🔵 HARDCODED | `"ci/cd"` normalization | `contact_lookup.py:150` | Special case for CI/CD casing |
| P2 | 🟣 COUPLED | `_run()` state machine | `actuator.py:363-451` | Deeply coupled to Playwright lifecycle, 3-tier fill→vision→submit |
| P2 | 🟣 COUPLED | `asyncio.run()` in `run()` | `actuator.py:454` | May conflict with running event loop in FastAPI |
| P2 | 🟡 SUSPECT | Cover letter 1500-char truncation | `actuator.py:330` | Silently truncates in vision context |
| P2 | 🟡 SUSPECT | `_focused_knowledge` string-slicing | `help_agent.py:336-341` | Uses `str.find()` to slice guides, fragile |
| P2 | 🟡 SUSPECT | `_resolve` import bypass | `portfolio_ingestor.py:80-81` | Uses private `llm._resolve` instead of `llm.resolve_config` |
| P2 | 🟡 SUSPECT | Regex HTML stripping | `portfolio_ingestor.py:160-163` | `re.sub(r"<[^>]+>", " ")` is a well-known antipattern |
| P2 | 🟡 SUSPECT | Nested lazy imports | `portfolio_ingestor.py:46, 80, 98` | Multiple inline imports inside function body |
| P3 | 🟠 STALE | `_USER_GUIDE` India market section | `help_agent.py:75, 209` | India market hardcoded in inline string |
| P3 | 🟠 STALE | `_PROVIDER_GUIDE` model list | `help_agent.py:177-194` | Model names will go out of date |
| P3 | 🟠 STALE | `_fallback` model list | `help_agent.py:362-370` | Duplicate stale model references |
| P3 | 🟢 CLEAN | `contact_lookup.py` | — | Well-factored, config-driven, clean pipeline |
| P3 | 🟢 CLEAN | `selectors.py` | — | Clean fallback chain, never raises |
| P3 | 🟢 CLEAN | `browser_runtime.py` | — | Well-structured multi-tier discovery |
| P3 | 🟢 CLEAN | `github_ingestor.py` | — | Clean async design, typed output |
| P3 | 🟢 CLEAN | `linkedin_parser.py` | — | Deterministic, no external deps |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `routes/actions.py` → `actuator.read_form`, `actuator.run`, `selectors.get_selectors`
- `routes/scan.py` → `help_agent.answer`
- `routes/misc.py` → `browser_runtime.chromium_executable`, `help_agent.answer`
- `routes/ingest.py` → `linkedin_parser.parse_linkedin_export`, `github_ingestor.ingest_github`, `portfolio_ingestor.ingest_portfolio_url`
- `services/generator.py` → `contact_lookup.run`, `actuator.run`
- `services/ghost.py` → `actuator.run`
- `tests/test_regressions.py` → `help_agent.answer`, `actuator._ready_to_submit`, `browser_runtime.browser_runtime_ready`
- `tests/test_observability.py` → `selectors.get_selectors`
- `tests/test_paths.py` → `browser_runtime.chromium_executable`

**Outbound (this unit depends on others):**
- `config` — all files reference `config` or `settings`
- `config.secrets` — `contact_lookup.py` (lazy import)
- `llm` — `help_agent.py`, `github_ingestor.py`, `portfolio_ingestor.py`, `actuator.py` (lazy import)
- `db.client` — `contact_lookup.py` (`get_profile`, `get_settings`), `selectors.py` (`get_setting`, `save_settings`), `actuator.py` (`get_setting`, lazy)
- `logger` — all files
- 3rd-party libs (Playwright, httpx, anthropic, openai, pydantic)

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `playwright` | Browser automation | no explicit pin in scope | 🟡 SUSPECT — dependency on system/bundled Chromium |
| `httpx` | HTTP requests | no explicit pin in scope | 🔵 HARDCODED — no version constraint visible |
| `anthropic` | Claude vision API | no explicit pin in scope | 🔵 HARDCODED — no version constraint visible |
| `openai` | OpenAI-compatible API | no explicit pin in scope | 🔵 HARDCODED — no version constraint visible |

---

## 6. First principles assessment

### `actuator.py`
1. **Does this file need to exist?** Partially — `read_form` is used by routes; `run` is experimental and gated. The vision fallback and DOM fill logic are complex but fragile.
2. **Does it do what it claims?** Yes — reads forms and auto-applies when enabled.
3. **Is it the right place for this logic?** Partially — browser lifecycle management should probably be shared with `browser_runtime.py` (it already imports `launch_chromium`), but the fill/vision/submit pipeline is cohesive here.
4. **What would break if deleted?** `routes/actions.py` (read_form, run), `services/generator.py` (run), `services/ghost.py` (run) — would lose all auto-apply functionality.

### `contact_lookup.py`
1. **Does this file need to exist?** Yes — Contact enrichment is a core workflow step.
2. **Does it do what it claims?** Yes — name matches behavior.
3. **Is it the right place for this logic?** Yes — well-scoped to contact enrichment.
4. **What would break if deleted?** `services/generator.py` would lose personalized email generation.

### `help_agent.py`
1. **Does this file need to exist?** Yes — in-app help is a user-facing feature.
2. **Does it do what it claims?** Partially — India market references baked into global guide text drift from current market focus config (which only supports "global" as valid focus value in `config/app.py:100`).
3. **Is it the right place for this logic?** Yes — it's a self-contained help agent.
4. **What would break if deleted?** `routes/scan.py`, `routes/misc.py` — both routes serve help endpoints.

### `selectors.py`
1. **Does this file need to exist?** Yes — provides the selector config layer for form reading.
2. **Does it do what it claims?** Yes — name matches.
3. **Is it the right place for this logic?** Yes — clean abstraction.
4. **What would break if deleted?** `actuator.py.read_form` and `routes/actions.py` selector endpoint.

### `browser_runtime.py`
1. **Does this file need to exist?** Yes — centralizes cross-platform browser management.
2. **Does it do what it claims?** Yes — name matches.
3. **Is it the right place for this logic?** Yes — well-contained.
4. **What would break if deleted?** `actuator.py`, `portfolio_ingestor.py`, `scout.py`, `routes/misc.py` — all use `launch_chromium` or `chromium_executable`.

### `github_ingestor.py`
1. **Does this file need to exist?** Yes — GitHub profile ingestion is a user-facing feature.
2. **Does it do what it claims?** Yes — name matches.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** `routes/ingest.py` — GitHub import endpoint.

### `linkedin_parser.py`
1. **Does this file need to exist?** Yes — LinkedIn export import is a user-facing feature.
2. **Does it do what it claims?** Yes — name matches.
3. **Is it the right place for this logic?** Yes — deterministic parsing is clean.
4. **What would break if deleted?** `routes/ingest.py` — LinkedIn import endpoint.

### `portfolio_ingestor.py`
1. **Does this file need to exist?** Partially — web scraping via Playwright plus regex fallback is fragile.
2. **Does it do what it claims?** Yes — name matches.
3. **Is it the right place for this logic?** Maybe — could live in a `scrapers/` package alongside other HTTP scrapers.
4. **What would break if deleted?** `routes/ingest.py` — portfolio import endpoint.
