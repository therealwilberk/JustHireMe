# Map: backend-scrapers

**File:** `docs/maps/backend-scrapers.md`
**Codebase path(s):** `backend/agents/`
**Files in scope:** 5
**Total lines:** ~2,665
**Generated:** 2026-05-15

---

## 1. Unit summary

This unit owns the "scouting" layer — every code path that discovers job leads from external sources. It contains five modules: (1) `scout.py` — the primary orchestrator that handles LLM-based extraction from scraped pages, RSS feeds, HN Hiring threads, and API-based boards (RemoteOK, Remotive, Jobicy); (2) `free_scout.py` — scrapes organic/free sources (Greenhouse, Lever, Ashby, Workable ATS boards, GitHub issues, HN comments, Reddit) with a custom connector system; (3) `x_scout.py` — searches X/Twitter API v2 for hiring-signal tweets; (4) `quality_gate.py` — deterministic lead quality filter shared across scrapers; (5) `query_gen.py` — generates profile-tailored Google `site:` search queries via LLM. The unit depends on `agents/lead_intel`, `agents/browser_runtime`, `llm`, `db.client`, `config`, and `logger`. Consumers are `services/scout.py`, `services/scanner.py`, `services/ghost.py`, `routes/leads.py`, and `mcp_server.py`.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `agents/scout.py` | 1,027 | Primary job-lead scraper: crawl, extract, save | 🟠 STALE — duplicates exist across `free_scout.py` and `quality_gate.py`; `_ensure_scheme` is defined twice |
| 2 | `agents/free_scout.py` | 718 | Free-source signal scraper: ATS, GitHub, HN, Reddit, custom connectors | 🟡 SUSPECT — imports and re-uses private (`_`) functions from `scout.py`; large code duplication with `scout.py` run loop |
| 3 | `agents/x_scout.py` | 478 | X/Twitter API v2 hiring-signal scanner | 🟢 CLEAN — well-structured single-responsibility module; minor hardcoded query/default issues |
| 4 | `agents/quality_gate.py` | 203 | Deterministic lead quality evaluation | 🟡 SUSPECT — `_parse_date` duplicates `scout.py:_parse_date` with different implementation; not exported from a shared location |
| 5 | `agents/query_gen.py` | 239 | Profile-tailored Google site: query generation | 🟡 SUSPECT — `_india_clause` is India-specific logic that may not belong in general query gen; fallback path may produce unusably broad queries |

---

## 3. Detailed breakdown

### `agents/scout.py`

**Purpose:** Primary job-lead extraction and orchestration engine. Scrapes pages via Playwright, extracts structured leads via LLM, handles specialized sources (RSS, HN Hiring, RemoteOK, Remotive, Jobicy), deduplicates against DB, runs quality gate, and saves leads. The `run()` function is the main entry point called by `services/scanner.py` and `services/ghost.py`. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | yes | 🟢 |
| `hashlib` | stdlib | yes | 🟢 |
| `re` | stdlib | yes | 🟢 — but re-imported inside `_parse_date` (line 81) and `_strip_html_text` (line 766) despite top-level import |
| `sys` | stdlib | no | 🔴 DEAD — unused import |
| `datetime.*` | stdlib | yes | 🟢 |
| `typing.*` | stdlib | yes | 🟢 |
| `urllib.parse.urlparse` | stdlib | yes | 🟢 |
| `httpx` | 3rd-party | yes | 🟢 |
| `tenacity.*` | 3rd-party | yes | 🟢 |
| `pydantic.*` | 3rd-party | yes | 🟢 |
| `agents.browser_runtime.launch_chromium` | local | yes | 🟢 |
| `agents.quality_gate.*` | local | yes | 🟢 |
| `db.client.url_exists, save_lead` | local | yes | 🟢 |
| `logger.get_logger` | local | yes | 🟢 |
| `html` | stdlib | inside `_strip_html_text`, `_is_hn_hiring_story` | 🟡 SUSPECT — local imports inside functions when available at top level |
| `html2text` | 3rd-party | inside `_to_md` | 🟢 — lazy import is appropriate |
| `playwright.async_api` | 3rd-party | inside `_crawl` | 🟢 — lazy import is appropriate |
| `llm.call_llm` | local | inside `_parse`, `_parse_wellfound` | 🟢 — lazy import is appropriate |
| `xml.etree.ElementTree` | stdlib | inside `_scrape_rss` | 🟢 — lazy import is appropriate |
| `agents.free_scout` | local | inside `_scrape_ats_target` | 🟣 COUPLED — circular-ish; `free_scout` also imports from `scout` |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | `get_logger(__name__)` | throughout | 🟢 |
| `_MAX_AGE_DAYS` | int | `7` | `_cutoff()`, `_is_recent()` | 🔵 HARDCODED — should be in config layer (settings.scraping.freshness_days) |
| `LAST_ERRORS` | list[str] | `[]` | `run()` | 🟡 SUSPECT — module-level mutable state, mutated by `run()`, read externally from `services/scout.py` |
| `LAST_USAGE` | dict | `{}` | `run()` | 🟡 SUSPECT — same as above; not exported but accessed via `getattr` externally |
| `_SOURCE_CAPS` | dict | hardcoded source→int map | `_source_cap()` | 🔵 HARDCODED — caps per source baked in, should be configurable |
| `_FRESHER_TERMS` | tuple | 9 terms | `classify_job_seniority()` | 🔵 HARDCODED — should be config taxonomy |
| `_JUNIOR_TERMS` | tuple | 19 terms | `classify_job_seniority()` | 🔵 HARDCODED — should be config taxonomy |
| `_MID_TERMS` | tuple | 12 terms | `classify_job_seniority()` | 🔵 HARDCODED — should be config taxonomy |
| `_SENIOR_TERMS` | tuple | 18 terms | `classify_job_seniority()` | 🔵 HARDCODED — should be config taxonomy |
| `_SCOUT_EXTRACT_SYSTEM` | str | LLM system prompt | `_parse()` | 🟢 — reasonable inline prompt |
| `_WELLFOUND_EXTRACT_SYSTEM` | str | LLM system prompt | `_parse_wellfound()` | 🟢 — reasonable inline prompt |

**Classes:**

#### `_Lead`
- **Inherits from:** `BaseModel`
- **Purpose:** Pydantic model for LLM-structured extraction output
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| (fields) | title, company, url, platform, description, posted_date | — | schema for LLM extraction | 🟢 — duplicate exists; `_Leads` wraps as list container, could be combined |

#### `_Leads`
- **Inherits from:** `BaseModel`
- **Purpose:** Wrapper list for LLM batch extraction
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `leads` | List[`_Lead`] | — | container field | 🟢 |

**Functions:**

#### `_cutoff() -> datetime`
- **Purpose:** Return the UTC datetime threshold for freshness (now - 7 days)
- **Called by:** `_is_recent()`, `_scrape_remoteok()`, `_scrape_hn_hiring()`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** references `_MAX_AGE_DAYS` module constant
- **Flag:** 🟢

#### `_parse_date(s: str) -> datetime | None`
- **Purpose:** Parse various date string formats into UTC datetime
- **Called by:** `_is_recent()`, `_is_strictly_recent()`
- **Calls:** `re` (local import)
- **Side effects:** none
- **Hardcodes:** multiple `strptime` format strings
- **Flag:** 🟡 SUSPECT — duplicate exists in `quality_gate.py:_parse_date` with different implementation; should be shared

#### `_is_recent(date_str: str) -> bool`
- **Purpose:** Return True if date is within freshness window or unknown
- **Called by:** `_parse()`, `_scrape_rss()`, `_scrape_remotive()`, `_scrape_jobicy_api()`, `_scrape_hn_hiring()`, exported to `free_scout.py`
- **Calls:** `_parse_date()`, `_cutoff()`
- **Side effects:** none
- **Flag:** 🟢

#### `_is_strictly_recent(date_str: str) -> bool`
- **Purpose:** Return True only when a parseable date is within freshness window
- **Called by:** `_is_fresh_lead()`
- **Calls:** `_parse_date()`, `_cutoff()`
- **Side effects:** none
- **Flag:** 🟡 SUSPECT — only called by `_is_fresh_lead`; could be inlined

#### `_lead_text(lead: dict) -> str`
- **Purpose:** Build concatenated text from lead dict for classification
- **Called by:** `classify_job_seniority()`
- **Calls:** none
- **Side effects:** none
- **Flag:** 🟡 SUSPECT — duplicate exists in `quality_gate.py:_lead_text` with slightly different field selection

#### `_experience_years(text: str) -> list[int]`
- **Purpose:** Extract experience year requirements from text
- **Called by:** `classify_job_seniority()`
- **Calls:** `re.finditer`
- **Flag:** 🟢

#### `_has_seniority_term(text: str, terms: tuple[str, ...]) -> bool`
- **Purpose:** Check if any seniority term appears word-boundary-delimited in text
- **Called by:** `classify_job_seniority()`
- **Calls:** `re.search`
- **Flag:** 🟢

#### `_is_beginner_role(lead: dict) -> bool`
- **Purpose:** Check if lead is fresher or junior
- **Called by:** `_passes_beginner_job_filter()`
- **Calls:** `classify_job_seniority()`
- **Flag:** 🟡 SUSPECT — thin wrapper; only called by `_passes_beginner_job_filter`, which is only used in tests

#### `classify_job_seniority(lead: dict) -> str`
- **Purpose:** Classify lead seniority from title, description, and years
- **Called by:** `run()`, `free_scout.py`, `x_scout.py`, `routes/leads.py`
- **Calls:** `_lead_text()`, `_experience_years()`, `_has_seniority_term()`
- **Side effects:** none
- **Flag:** 🟢 — heavily reused; exported to other modules

#### `_is_fresh_lead(lead: dict) -> bool`
- **Purpose:** Determine if a lead is fresh based on multiple date fields
- **Called by:** `run()`
- **Calls:** `_is_strictly_recent()`
- **Side effects:** none
- **Flag:** 🟡 SUSPECT — only used for `source_meta.is_fresh` metadata enrichment; not used for filtering

#### `_passes_beginner_job_filter(lead: dict) -> bool`
- **Purpose:** Check if role is beginner-suitable
- **Called by:** unknown within this unit (tests reference it)
- **Calls:** `_is_beginner_role()`
- **Flag:** 🟡 SUSPECT — only used in tests (test_regressions.py:660); possibly dead code since `run()` does not call it

#### `_h(u: str) -> str`
- **Purpose:** Compute MD5 hash prefix for job ID
- **Called by:** `run()`, `free_scout.py:_text_lead()` (via `lead_id`), x_scout.py
- **Calls:** `hashlib.md5`
- **Flag:** 🟢

#### `_to_md(html: str) -> str`
- **Purpose:** Convert HTML to markdown via html2text
- **Called by:** `_crawl()`
- **Calls:** `html2text.HTML2Text`
- **Flag:** 🟢

#### `_crawl(u: str, headed: bool = False) -> str`
- **Purpose:** Launch Playwright browser, navigate to URL, return page content as markdown
- **Called by:** `scrape()`, `run()` (for wellfound, site: targets)
- **Calls:** `launch_chromium()`, `_to_md()`
- **Side effects:** launches browser process; full page load
- **Hardcodes:** `timeout=30000`
- **Flag:** 🟣 COUPLED — `timeout=30000` hardcoded; should be configurable

#### `_parse(md: str, src: str) -> list`
- **Purpose:** Extract structured leads from scraped markdown via LLM, filter to recent
- **Called by:** `scrape()`
- **Calls:** `call_llm()`, `_is_recent()`
- **Side effects:** LLM API call
- **Hardcodes:** `tbs=qdr:w` freshness heuristic for Google search sources
- **Flag:** 🟢

#### `_parse_wellfound(md: str, src: str) -> list`
- **Purpose:** Wellfound-specific LLM extraction variant
- **Called by:** `run()`
- **Calls:** `call_llm()`, `_is_recent()`
- **Side effects:** LLM API call
- **Flag:** 🟡 SUSPECT — nearly identical to `_parse()` with different system prompt; hardcodes `platform = "wellfound"`

#### `apify(actor: str, inp: dict, tok: str) -> list`
- **Purpose:** Run Apify actor and return dataset items
- **Called by:** `run()`
- **Calls:** `httpx.AsyncClient`
- **Side effects:** external API call
- **Hardcodes:** `https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items`
- **Flag:** 🟢 — properly parameterized for actor/token

#### `_ensure_scheme(u: str) -> str` (first definition, line 374)
- **Purpose:** Prepend `https://` if URL has no scheme
- **Called by:** none (superseded by second definition at line 386)
- **Flag:** 🔴 DEAD — defined at line 374, immediately redefined at line 386 with same name but broader logic

#### `_ensure_scheme(u: str) -> str` (second definition, line 386)
- **Purpose:** Prepend `https://` for bare domains but keep pseudo-targets intact (site:, ats:, github:, hn:, reddit:)
- **Called by:** `run()`, `_scrape_ats_target()`
- **Flag:** 🟢 — but the duplicate first definition is dead code

#### `_platform_from_url(u: str, fallback: str = "scout") -> str`
- **Purpose:** Determine platform name from URL hostname
- **Called by:** `_lead_source()`, `_scrape_rss()`, `_is_ats_target()`
- **Hardcodes:** 9 hostname→platform mappings
- **Flag:** 🔵 HARDCODED — platform→host mappings should be in config

#### `_lead_source(item: dict) -> str`
- **Purpose:** Extract source platform from item dict
- **Called by:** `_source_cap()`
- **Flag:** 🟢

#### `_source_cap(item: dict) -> int`
- **Purpose:** Get per-source maximum lead count from `_SOURCE_CAPS`
- **Called by:** unknown within this file — might be unused in run()
- **Flag:** 🟡 SUSPECT — `_SOURCE_CAPS` is defined but `_source_cap()` is never called within `scout.py`; appears to be vestigial

#### `_http_headers(source: str) -> dict`
- **Purpose:** Build HTTP headers with User-Agent per source
- **Called by:** `_scrape_rss()`, `_scrape_remoteok()`, `_scrape_remotive()`, `_scrape_jobicy_api()`
- **Flag:** 🟢

#### `_compact(value) -> str`
- **Purpose:** Convert value to compact string representation
- **Called by:** `_detail()`, `_description()`, `_salary_from_bounds()`
- **Flag:** 🟢

#### `_detail(label: str, value) -> str`
- **Purpose:** Format label: value pair if value exists
- **Called by:** various scrapers
- **Flag:** 🟢

#### `_description(*parts, limit: int = 1600) -> str`
- **Purpose:** Build clean description string from parts with length limit
- **Called by:** various scrapers
- **Flag:** 🟢

#### `_salary_from_bounds(low, high, currency: str = "") -> str`
- **Purpose:** Format salary range string
- **Called by:** `_scrape_remoteok()`, `_scrape_jobicy_api()`
- **Flag:** 🟢

#### `_xml_text(node, *names: str) -> str`
- **Purpose:** Extract text from first child XML element matching any of the given tag names
- **Called by:** `_scrape_rss()`
- **Flag:** 🟢

#### `_xml_all_text(node, name: str) -> list[str]`
- **Purpose:** Extract text from all child XML elements matching a tag name
- **Called by:** `_scrape_rss()`
- **Flag:** 🟢

#### `_looks_role_like(text: str) -> bool`
- **Purpose:** Check if text looks like a technical role title
- **Called by:** `_rss_company_and_role()`, `_hn_company_role()`
- **Hardcodes:** 14 role terms
- **Flag:** 🔵 HARDCODED — role term list should be config taxonomy

#### `_rss_company_and_role(title: str, platform: str) -> tuple[str, str]`
- **Purpose:** Parse company and role from RSS item title using heuristic splitting
- **Called by:** `_scrape_rss()`
- **Flag:** 🟢 — heuristic but well-constructed

#### `_is_ats_target(target: str) -> bool`
- **Purpose:** Check if target is an ATS board URL
- **Called by:** unknown — may be dead
- **Flag:** 🟡 SUSPECT — defined but not called anywhere in the file; `free_scout.py` has its own ATS routing

#### `_scrape_ats_target(target: str) -> list[dict]`
- **Purpose:** Delegate ATS scraping to free_scout
- **Called by:** unknown — may be dead, or called from `run()` path for ATS targets
- **Flag:** 🟡 SUSPECT — delegates to `free_scout._scrape_target`; only called if an ATS target is encountered but `run()` doesn't appear to route ATS: targets before they get to the `else` clause

#### `scrape(u: str, headed: bool = False) -> list`
- **Purpose:** Top-level scrape function: crawl URL and parse leads
- **Called by:** `run()`
- **Calls:** `_ensure_scheme()`, `asyncio.run(_crawl())`, `_parse()`
- **Flag:** 🟢

#### `_scrape_rss(u: str) -> list`
- **Purpose:** Scrape RSS/XML feed and extract items
- **Called by:** `run()`
- **Calls:** `httpx.AsyncClient`, `_is_recent()`, `_rss_company_and_role()`, `_description()`
- **Hardcodes:** `timeout=30`
- **Flag:** 🟢

#### `_scrape_remoteok() -> list`
- **Purpose:** Scrape RemoteOK API
- **Called by:** `run()`
- **Calls:** `httpx.AsyncClient`
- **Hardcodes:** `"https://remoteok.com/api"`, `User-Agent` spoofed as Chrome
- **Flag:** 🔵 HARDCODED — API URL and User-Agent baked in

#### `_scrape_remotive(u: str) -> list`
- **Purpose:** Scrape Remotive API
- **Called by:** `run()`
- **Calls:** `httpx.AsyncClient`
- **Flag:** 🟢 — URL parameterized

#### `_scrape_jobicy_api(u: str) -> list`
- **Purpose:** Scrape Jobicy API
- **Called by:** `run()`
- **Flag:** 🟢 — URL parameterized

#### `_strip_html_text(text: str) -> str`
- **Purpose:** Strip HTML tags and unescape entities
- **Called by:** internal scraper helpers; exported to `free_scout.py` and `x_scout.py`
- **Flag:** 🟢 — reused across unit

#### `_is_hn_hiring_story(story: dict) -> bool`
- **Purpose:** Check if a HN Algolia hit is a "Who is hiring?" story
- **Called by:** `_scrape_hn_hiring()`
- **Flag:** 🟢

#### `_looks_like_hn_job_post(text: str) -> bool`
- **Purpose:** Heuristic check if HN comment looks like a job post
- **Called by:** `_scrape_hn_hiring()`, `free_scout.py:_scrape_hn()`
- **Hardcodes:** role_terms (15) and hiring_terms (12) tuples
- **Flag:** 🔵 HARDCODED — term lists baked in

#### `_hn_company_role(text: str, author: str = "") -> tuple[str, str]`
- **Purpose:** Parse company name and role from HN job post text
- **Called by:** `_scrape_hn_hiring()`, exported to `free_scout.py`
- **Flag:** 🟢 — well-tested heuristic

#### `_scrape_hn_hiring() -> list`
- **Purpose:** Fetch latest HN "Who is hiring?" thread, extract job posts
- **Called by:** `run()`
- **Hardcodes:** `"https://hn.algolia.com/api/v1/search"`, `"https://hn.algolia.com/api/v1/items/{story_id}"`, `timedelta(days=35)` search window, `timedelta(days=7)` for freshness via `_MAX_AGE_DAYS`
- **Flag:** 🔵 HARDCODED — API URLs, 35-day search window baked in

#### `run(...) -> list`
- **Purpose:** Main entry point: orchestrate scraping across all targets, deduplicate, quality-gate, save
- **Called by:** `services/scanner.py`, `services/ghost.py` (both via `asyncio.to_thread`)
- **Calls:** most private functions in file
- **Side effects:** DB writes via `save_lead()`, LLM calls, external HTTP/API calls, browser launch
- **Hardcodes:** Google URL template `"https://www.google.com/search?q={query}&tbs=qdr:w"`, `_fresh_source` tag
- **Flag:** 🟡 SUSPECT — large monolithic function (~90 lines); handles all target types in a single if/elif chain; hard to test individual branches

**Exports (what other modules import from this file):**

| Export | Known importers |
|--------|----------------|
| `scrape` | none external (internal use only) |
| `run` | `services/scanner.py`, `services/ghost.py` |
| `classify_job_seniority` | `free_scout.py`, `x_scout.py`, `routes/leads.py` |
| `_hn_company_role` | `free_scout.py` |
| `_is_recent` | `free_scout.py` |
| `_looks_like_hn_job_post` | `free_scout.py` |
| `_strip_html_text` | `free_scout.py` |
| `_passes_beginner_job_filter` | `tests/test_regressions.py` |
| `_is_rss_target` | `tests/test_regressions.py` |
| `_is_hn_hiring_story` | `tests/test_regressions.py` |

---

### `agents/free_scout.py`

**Purpose:** Free-source signal scanner that scrapes ATS boards (Greenhouse, Lever, Ashby, Workable), GitHub issues, HN comments, Reddit posts, and custom HTTP connectors. Provides "organic" lead discovery outside of structured job boards. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | yes | 🟢 |
| `html` | stdlib | yes | 🟢 |
| `json` | stdlib | yes | 🟢 |
| `re` | stdlib | yes | 🟢 |
| `datetime.*` | stdlib | yes | 🟢 |
| `urllib.parse.*` | stdlib | yes | 🟢 |
| `httpx` | 3rd-party | yes | 🟢 |
| `tenacity.*` | 3rd-party | yes | 🟢 |
| `agents.lead_intel.*` | local | yes | 🟢 |
| `agents.quality_gate.*` | local | yes | 🟢 |
| `agents.scout._hn_company_role, _is_recent, _looks_like_hn_job_post, _strip_html_text, classify_job_seniority` | local | yes | 🟣 COUPLED — imports private (`_`) functions from another module, creating tight coupling |
| `db.client.*` | local | yes | 🟢 |
| `logger.get_logger` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | `get_logger(__name__)` | throughout | 🟢 |
| `LAST_ERRORS` | list[str] | `[]` | `run()` | 🟡 SUSPECT — mutable module state, same pattern as scout.py |
| `LAST_USAGE` | dict | `{}` | `run()` | 🟡 SUSPECT — mutable module state, same pattern as scout.py |
| `DEFAULT_TARGETS` | list | 5 hardcoded pseudo-targets | `targets_from_settings()` | 🔵 HARDCODED — should be in user config or settings defaults |
| `_CONNECTOR_MAX_ITEMS` | int | `60` | `_scrape_custom_connector()` | 🔵 HARDCODED — should be configurable |
| `_JSON_GET_TIMEOUT` | — | not defined as constant; `30` used inline | — | 🔵 HARDCODED — timeout 30s appears in every `AsyncClient()` call |

**Functions:**

#### `split_lines(raw: str | None) -> list[str]`
- **Purpose:** Split newline-separated config text into lines, skipping empties and comments
- **Called by:** `targets_from_settings()`, `_ats_targets_from_watchlist()`
- **Flag:** 🟢

#### `targets_from_settings(raw_targets: str | None, raw_watchlist: str | None) -> list[str]`
- **Purpose:** Combine raw targets with watchlist-derived ATS targets, fall back to defaults
- **Called by:** `run()`
- **Flag:** 🟢

#### `_dot_get(value, path: str, default="")`
- **Purpose:** Navigate nested dicts/lists using dot-separated path
- **Called by:** `_scrape_custom_connector()`
- **Flag:** 🟢

#### `_parse_json_setting(raw: str | None, fallback)`
- **Purpose:** Parse JSON string settings safely
- **Called by:** `_connector_headers()`, `run()`
- **Flag:** 🟢

#### `_connector_headers(raw_headers: str | None, name: str) -> dict`
- **Purpose:** Extract connector-specific headers from JSON blob
- **Called by:** `_scrape_custom_connector()`
- **Flag:** 🟢

#### `_scrape_custom_connector(connector: dict, raw_headers: str | None = None) -> list[dict]`
- **Purpose:** Execute custom HTTP connector: GET JSON endpoint, map fields, return leads
- **Called by:** `run()`
- **Side effects:** HTTP request, external API call
- **Hardcodes:** `timeout=30`, `_CONNECTOR_MAX_ITEMS=60`
- **Flag:** 🟢 — well-designed generic connector system

#### `_ats_targets_from_watchlist(raw: str | None) -> list[str]`
- **Purpose:** Parse company watchlist into ATS target strings
- **Called by:** `targets_from_settings()`, `tests/test_regressions.py`
- **Hardcodes:** provider aliases (gh → greenhouse, etc.)
- **Flag:** 🟢

#### `_text_lead(item: dict, default_kind: str = "job") -> dict`
- **Purpose:** Enrich raw lead dict with computed fields (signal quality, outreach drafts, fit bullets, etc.)
- **Called by:** all ATS/GitHub/HN/Reddit scrapers
- **Calls:** `signal_quality()`, `outreach_drafts()`, `fit_bullets()`, etc. from `lead_intel`
- **Side effects:** none (pure-ish; calls `classify_job_seniority` from scout)
- **Flag:** 🟢 — heavy enrichment function but well-scoped

#### `_json_get(url: str, params: dict | None = None) -> dict | list`
- **Purpose:** Retry-wrapped JSON GET helper
- **Called by:** ATS scrapers, `_scrape_github()`, `_scrape_hn()`, `_scrape_reddit()`
- **Hardcodes:** `timeout=30`
- **Flag:** 🟢

#### `_scrape_greenhouse(slug: str) -> list[dict]`
- **Purpose:** Scrape Greenhouse ATS board via API
- **Called by:** `_scrape_target()`, `_scrape_direct_ats_url()`
- **Hardcodes:** `"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"`
- **Flag:** 🔵 HARDCODED — API endpoint URL baked in

#### `_scrape_lever(slug: str) -> list[dict]`
- **Purpose:** Scrape Lever ATS board via API
- **Called by:** `_scrape_target()`, `_scrape_direct_ats_url()`
- **Hardcodes:** `"https://api.lever.co/v0/postings/{slug}"`
- **Flag:** 🔵 HARDCODED — API endpoint URL baked in

#### `_scrape_ashby(slug: str) -> list[dict]`
- **Purpose:** Scrape Ashby ATS board via API
- **Called by:** `_scrape_target()`, `_scrape_direct_ats_url()`
- **Hardcodes:** `"https://api.ashbyhq.com/posting-api/job-board/{slug}"`
- **Flag:** 🔵 HARDCODED — API endpoint URL baked in

#### `_scrape_workable(slug: str) -> list[dict]`
- **Purpose:** Scrape Workable ATS board via API
- **Called by:** `_scrape_target()`, `_scrape_direct_ats_url()`
- **Hardcodes:** two API URLs: `"https://www.workable.com/api/accounts/{slug}"` and `"https://apply.workable.com/api/v1/widget/accounts/{slug}"`
- **Flag:** 🔵 HARDCODED — API endpoints baked in; try/except fallback is fragile

#### `_github_query(raw: str) -> str`
- **Purpose:** Build GitHub search query from pseudo-target string
- **Called by:** `_scrape_github()`
- **Hardcodes:** `updated:>={30 days ago}` window, `is:issue is:open archived:false`
- **Flag:** 🔵 HARDCODED — 30-day search window baked in

#### `_scrape_github(raw: str) -> list[dict]`
- **Purpose:** Search GitHub issues for hiring/help-wanted posts
- **Called by:** `_scrape_target()`
- **Hardcodes:** `"https://api.github.com/search/issues"`, `per_page: 25`
- **Flag:** 🔵 HARDCODED — API endpoint and pagination baked in

#### `_scrape_hn(raw: str) -> list[dict]`
- **Purpose:** Search HN Algolia for hiring comments
- **Called by:** `_scrape_target()`
- **Hardcodes:** `"https://hn.algolia.com/api/v1/search_by_date"`, 30-day cutoff, `hitsPerPage: 30`
- **Flag:** 🔵 HARDCODED — API URL and limits baked in

#### `_scrape_reddit(raw: str) -> list[dict]`
- **Purpose:** Search Reddit subreddit for hiring posts
- **Called by:** `_scrape_target()`
- **Hardcodes:** `"https://www.reddit.com/r/{subreddit}/search.json"`, `limit: 25`, `t: month`
- **Flag:** 🔵 HARDCODED — API URL and limits baked in; no Reddit API auth (uses public JSON endpoint — rate limits may hit)

#### `_scrape_direct_ats_url(url: str) -> list[dict]`
- **Purpose:** Parse a direct ATS URL and dispatch to the right scraper
- **Called by:** `_scrape_target()`
- **Flag:** 🟢

#### `_scrape_target(target: str) -> list[dict]`
- **Purpose:** Route pseudo-target string to the appropriate scraper
- **Called by:** `run()`, `scout.py:_scrape_ats_target()`
- **Flag:** 🟢

#### `run(...) -> list[dict]`
- **Purpose:** Main entry point: orchestrate free-source scanning, custom connectors, quality gate, save
- **Called by:** `services/scout.py` (via `asyncio.to_thread`)
- **Side effects:** DB writes, HTTP requests
- **Flag:** 🟡 SUSPECT — ~170 lines; near-duplicate save logic for batch vs. custom connectors (~40 lines repeated identically); large function

**Exports:**

| Export | Known importers |
|--------|----------------|
| `run` | `services/scout.py` |
| `split_lines` | unknown — potential export |
| `targets_from_settings` | unknown — potential export |
| `_ats_targets_from_watchlist` | `tests/test_regressions.py` |
| `_scrape_target` | `scout.py:_scrape_ats_target()` |

---

### `agents/x_scout.py`

**Purpose:** X/Twitter API v2 job-signal scanner. Searches for hiring-related tweets using configurable queries and a watchlist of X handles. Classifies posts, computes signal quality scores, enriches with outreach drafts, and saves leads. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `asyncio` | stdlib | yes | 🟢 |
| `hashlib` | stdlib | yes | 🟢 |
| `os` | stdlib | yes | 🟢 |
| `re` | stdlib | yes | 🟢 |
| `urllib.parse.urlencode` | stdlib | yes | 🟢 |
| `agents.lead_intel.*` | local | yes | 🟢 |
| `db.client.*` | local | yes | 🟢 |
| `httpx` | 3rd-party | inside `_search_recent` | 🟢 — lazy import is appropriate |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `X_API_BASE` | str | `"https://api.x.com/2/tweets/search/recent"` | `_search_recent()` | 🔵 HARDCODED — should be in config |
| `LAST_ERRORS` | list[str] | `[]` | `run()` | 🟡 SUSPECT — mutable module state |
| `LAST_USAGE` | dict | `{}` | `run()` | 🟡 SUSPECT — mutable module state |
| `DEFAULT_QUERIES` | tuple | 3 hardcoded X search queries | `split_queries()` | 🔵 HARDCODED — default queries baked in |
| `WATCHLIST_QUERY` | str | hardcoded search expression | `build_watchlist_queries()` | 🔵 HARDCODED |
| `TECH_TERMS` | tuple | 18 terms | `classify_post()`, `signal_quality()` | 🔵 HARDCODED |
| `ROLE_TERMS` | tuple | 24 terms | `classify_post()`, `signal_quality()` | 🔵 HARDCODED |
| `INTENT_TERMS` | tuple | 13 terms | `classify_post()`, `signal_quality()` | 🔵 HARDCODED |
| `JOB_TERMS` | tuple | 11 terms | `classify_post()` | 🔵 HARDCODED |
| `URGENCY_TERMS` | tuple | 10 terms | `signal_quality()` | 🔵 HARDCODED |
| `BUYER_TERMS` | tuple | 10 terms | `signal_quality()` | 🔵 HARDCODED |
| `NOISE_TERMS` | tuple | 12 terms | `classify_post()`, `signal_quality()` | 🔵 HARDCODED |

**Functions:**

#### `_h(value: str) -> str`
- **Purpose:** MD5 hash prefix for job IDs (duplicate of scout.py:_h)
- **Called by:** `_lead_from_tweet()`
- **Flag:** 🟡 SUSPECT — duplicate of `scout.py:_h`; should import from shared location

#### `_int_setting(value, default, min_value, max_value) -> int`
- **Purpose:** Safely parse and clamp integer settings
- **Called by:** `run()`
- **Flag:** 🟢

#### `split_queries(raw: str | None) -> list[str]`
- **Purpose:** Parse newline-separated query text, fallback to defaults
- **Called by:** `build_queries()`
- **Flag:** 🟢

#### `split_watchlist(raw: str | None) -> list[str]`
- **Purpose:** Parse watchlist text (handles URLs, @mentions, bare handles)
- **Called by:** `build_watchlist_queries()`
- **Flag:** 🟢

#### `build_watchlist_queries(raw_watchlist: str | None) -> list[str]`
- **Purpose:** Build `from:handle <WATCHLIST_QUERY>` for each watchlist handle
- **Called by:** `build_queries()`
- **Flag:** 🟢

#### `build_queries(raw_queries: str | None = None, raw_watchlist: str | None = None) -> list[str]`
- **Purpose:** Combine explicit queries with watchlist queries
- **Called by:** `run()`
- **Flag:** 🟢

#### `_clean_text(text: str) -> str`
- **Purpose:** Normalize whitespace
- **Called by:** most functions in file
- **Flag:** 🟢

#### `_has_any(text: str, terms: tuple[str, ...]) -> bool`
- **Purpose:** Check if any term appears in text
- **Called by:** `classify_post()`
- **Flag:** 🟢

#### `_matched_terms(text: str, terms: tuple[str, ...], limit: int = 4) -> list[str]`
- **Purpose:** Return up to `limit` matched terms
- **Called by:** `signal_quality()`
- **Flag:** 🟢

#### `classify_post(text: str) -> str | None`
- **Purpose:** Classify a tweet as "job" or None based on term matching
- **Called by:** `run()`
- **Flag:** 🟢

#### `signal_quality(text: str, user: dict | None = None, kind: str | None = None) -> dict`
- **Purpose:** Compute signal quality score (0-100) with explanation
- **Called by:** `_lead_from_tweet()`
- **Flag:** 🟢 — well-structured scoring with penalties

#### `_budget_from_text(text: str) -> str`
- **Purpose:** Extract budget/salary amount from text via regex
- **Called by:** `_lead_from_tweet()` (indirectly via `signal_quality`)
- **Flag:** 🟢

#### `_title_from_text(text: str, kind: str) -> str`
- **Purpose:** Derive a title from tweet text
- **Called by:** `_lead_from_tweet()`
- **Flag:** 🟢

#### `_tweet_url(tweet: dict, user: dict | None) -> str`
- **Purpose:** Build canonical tweet URL
- **Called by:** `_lead_from_tweet()`
- **Flag:** 🟢

#### `_profile_url(user: dict | None) -> str`
- **Purpose:** Build user profile URL
- **Called by:** `_lead_from_tweet()`
- **Flag:** 🟢

#### `_outreach_from_lead(text: str, user: dict | None, kind: str, budget: str) -> dict`
- **Purpose:** Generate reply and DM draft for X lead
- **Called by:** `_lead_from_tweet()`
- **Hardcodes:** outreach templates with hardcoded tech terms
- **Flag:** 🟡 SUSPECT — hardcoded outreach templates may not fit all contexts

#### `_lead_from_tweet(tweet: dict, user: dict | None, kind: str, query: str) -> dict`
- **Purpose:** Convert a classified tweet into a full lead dict with all enrichment
- **Called by:** `run()`
- **Calls:** `classify_job_seniority` from scout (lazy import at line 345)
- **Flag:** 🟡 SUSPECT — lazy import inside function body; duplicates outreach generation between `_outreach_from_lead` and `_lead_outreach_drafts`

#### `_search_recent(bearer_token, query, max_results=50)`
- **Purpose:** Execute X API v2 recent search
- **Called by:** `run()`
- **Hardcodes:** `"https://api.x.com/2/tweets/search/recent"` (via `X_API_BASE`), `tweet.fields` and `user.fields` parameter strings
- **Flag:** 🔵 HARDCODED — API base URL, field lists

#### `run(...) -> list[dict]`
- **Purpose:** Main entry point: search X, classify, score, save leads
- **Called by:** `services/scout.py`
- **Side effects:** X API calls, DB writes
- **Flag:** 🟢 — clean orchestration, single responsibility

**Exports:**

| Export | Known importers |
|--------|----------------|
| `run` | `services/scout.py` |
| `build_watchlist_queries` | `tests/test_regressions.py` |
| `split_queries` | unknown |
| `split_watchlist` | unknown |
| `build_queries` | unknown |

---

### `agents/quality_gate.py`

**Purpose:** Deterministic lead quality filter. Checks freshness, seniority, red flags, missing fields, and applies penalties to compute a score. Shared by scout.py, free_scout.py, and mcp_server.py. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `__future__.annotations` | stdlib | — | 🟢 |
| `re` | stdlib | yes | 🟢 |
| `datetime.*` | stdlib | yes | 🟢 |
| `email.utils.parsedate_to_datetime` | stdlib | yes | 🟢 |
| `agents.lead_intel.clean_text, signal_quality` | local | yes | 🟢 |
| `logger.get_logger` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `MIN_DEFAULT_QUALITY` | int | `60` | `evaluate_lead_quality()`, exported | 🟢 — reasonable default |
| `HOT_LEAD_THRESHOLD` | int | `80` | (not used in this file — may be used by importers) | 🟡 SUSPECT — defined here but used elsewhere |
| `_RED_FLAGS` | tuple | 10 strings | `evaluate_lead_quality()` | 🔵 HARDCODED — should be config |
| `_SENIOR_FLAGS` | tuple | 11 strings | `_seniority()` | 🔵 HARDCODED — should be config taxonomy |
| `_BEGINNER_FLAGS` | tuple | 12 strings | `_seniority()` | 🔵 HARDCODED — should be config taxonomy |

**Functions:**

#### `_lead_text(lead: dict) -> str`
- **Purpose:** Build concatenated lead text for evaluation (duplicate of scout.py:_lead_text)
- **Called by:** `evaluate_lead_quality()`
- **Flag:** 🟡 SUSPECT — duplicate of `scout.py:_lead_text()` with different field set (includes `location`)

#### `_parse_date(value: str) -> datetime | None`
- **Purpose:** Parse date string (duplicate of scout.py:_parse_date but different implementation)
- **Called by:** `_freshness()`
- **Flag:** 🟡 SUSPECT — duplicate implementation with scout.py; uses `email.utils.parsedate_to_datetime` instead of `strptime`; not shared

#### `_freshness(lead: dict, max_age_days: int = 7) -> tuple[bool, str]`
- **Purpose:** Evaluate lead freshness from multiple date fields
- **Called by:** `evaluate_lead_quality()`
- **Flag:** 🟢

#### `_seniority(text: str, source_level: str = "") -> str`
- **Purpose:** Determine seniority level from text or source-provided level
- **Called by:** `evaluate_lead_quality()`
- **Flag:** 🟢

#### `evaluate_lead_quality(lead: dict, ...) -> dict`
- **Purpose:** Main evaluation: compute score, check thresholds, return verdict
- **Called by:** `scout.py:run()`, `free_scout.py:run()`, `mcp_server.py`
- **Side effects:** none
- **Flag:** 🟢 — clean deterministic function, well-documented

#### `attach_quality_metadata(lead: dict, quality: dict) -> dict`
- **Purpose:** Attach quality score/reason to lead's source_meta
- **Called by:** `scout.py:run()`, `free_scout.py:run()`
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `MIN_DEFAULT_QUALITY` | `scout.py`, `free_scout.py` |
| `evaluate_lead_quality` | `scout.py`, `free_scout.py`, `mcp_server.py` |
| `attach_quality_metadata` | `scout.py`, `free_scout.py` |
| `_parse_date` | `tests/test_observability.py` |

---

### `agents/query_gen.py`

**Purpose:** Generates profile-tailored Google `site:` search queries for job boards. Uses LLM to produce focused queries based on candidate profile (skills, experience, target role). Also handles India market focus. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `re` | stdlib | yes | 🟢 |
| `urllib.parse.*` | stdlib | yes | 🟢 |
| `pydantic.BaseModel` | 3rd-party | yes | 🟢 |
| `typing.List` | stdlib | yes | 🟢 |
| `logger.get_logger` | local | yes | 🟢 |

**Classes:**

#### `_Plan`
- **Inherits from:** `BaseModel`
- **Purpose:** LLM output schema for generated queries
- **Still needed:** yes
- **Flag:** 🟢

**Functions:**

#### `_extract_domains(urls: list[str]) -> tuple[list[str], list[str]]`
- **Purpose:** Split URLs into site: domains and passthrough URLs
- **Called by:** `generate()`
- **Flag:** 🟢

#### `_detect_experience_level(profile: dict) -> str`
- **Purpose:** Infer candidate experience level from profile
- **Called by:** `generate()`
- **Calls:** `agents.scoring_engine.infer_experience_level`
- **Flag:** 🟡 SUSPECT — import inside function body; try/except catches all and falls back to "junior"/"fresher" guess

#### `_seniority_hint(level: str) -> str`
- **Purpose:** Map experience level to OR-query seniority terms
- **Called by:** `generate()`
- **Hardcodes:** 4 level→term mappings
- **Flag:** 🔵 HARDCODED — term lists baked in

#### `_role_terms(profile: dict) -> list[str]`
- **Purpose:** Detect role categories from profile text
- **Called by:** `generate()`, `_profile_search_terms()`
- **Hardcodes:** 10 category→alias mappings
- **Flag:** 🔵 HARDCODED — role catalog baked in

#### `_profile_search_terms(profile: dict) -> list[str]`
- **Purpose:** Build deduplicated list of search terms from profile
- **Called by:** `generate()`, `_enrich_passthrough_targets()`
- **Flag:** 🟢

#### `_set_query_param(url: str, key: str, value: str) -> str`
- **Purpose:** Set a query parameter on a URL
- **Called by:** `_enrich_passthrough_targets()`
- **Flag:** 🟢

#### `_enrich_passthrough_targets(urls: list[str], profile: dict) -> list[str]`
- **Purpose:** Add search parameters to known API URLs (Remotive, Jobicy)
- **Called by:** `generate()`
- **Hardcodes:** Remotive (`search=`), Jobicy (`tag=`) parameter names and host checks
- **Flag:** 🔵 HARDCODED — board-specific enrichment baked in

#### `_market_focus(value) -> str`
- **Purpose:** Normalize market focus value to "india" or "global"
- **Called by:** `generate()`
- **Flag:** 🟢

#### `_india_clause(query: str) -> str`
- **Purpose:** Append India location terms to query if not already present
- **Called by:** `generate()`
- **Hardcodes:** India city names list
- **Flag:** 🔵 HARDCODED — India-specific logic baked into general query gen; should be config-driven or moved

#### `generate(profile: dict, urls: list[str], market_focus: str = "global") -> list[str]`
- **Purpose:** Main entry point: generate profile-tailored site: queries
- **Called by:** `services/scanner.py`, `services/ghost.py`
- **Side effects:** LLM API call
- **Flag:** 🟡 SUSPECT — LLM call with fallback to heuristic; `_india_clause` is applied after LLM output; large prompt constructed in function body

**Exports:**

| Export | Known importers |
|--------|----------------|
| `generate` | `services/scanner.py`, `services/ghost.py` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 DEAD | `import sys` | `scout.py:4` | Never used anywhere in file |
| P0 | 🔴 DEAD | `_ensure_scheme` (first def) | `scout.py:374` | Immediately redefined at line 386, first def unreachable |
| P0 | 🔴 DEAD | `_source_cap()` | `scout.py:431` | Never called within the unit; `_SOURCE_CAPS` defined but unused |
| P0 | 🔴 DEAD | `_is_ats_target()` | `scout.py:531` | Defined but never called; ATS routing is in free_scout.py |
| P1 | 🟣 COUPLED | `free_scout.py` imports `_`-prefixed from `scout.py` | `free_scout.py:26` | Imports 5 private functions; creates tight cross-module coupling |
| P1 | 🟣 COUPLED | `scout.py:_scrape_ats_target` imports `free_scout` | `scout.py:541` | Circular-ish dependency; scout and free_scout import each other |
| P1 | 🟣 COUPLED | `x_scout.py` lazy-imports `scout.classify_job_seniority` inside function body | `x_scout.py:345` | Inline lazy import hidden in a function |
| P1 | 🔵 HARDCODED | `_MAX_AGE_DAYS = 7` | `scout.py:20` | Should be in config/settings, not hardcoded |
| P1 | 🔵 HARDCODED | `_SOURCE_CAPS` | `scout.py:25` | Per-source lead caps baked in, should be configurable |
| P1 | 🔵 HARDCODED | Seniority term tuples (`_FRESHER_TERMS`, etc.) | `scout.py:35-64` | Taxonomies baked in, should be in config/scoring.py |
| P1 | 🔵 HARDCODED | `_SENIOR_FLAGS`, `_BEGINNER_FLAGS`, `_RED_FLAGS` | `quality_gate.py:22-59` | Flag lists baked in, should be in config/scoring.py |
| P1 | 🔵 HARDCODED | ATS API endpoints | `free_scout.py:260-344` | 4 ATS board API URLs baked in (Greenhouse, Lever, Ashby, Workable) |
| P1 | 🔵 HARDCODED | HN Algolia API URLs | `scout.py:870-892` | `hn.algolia.com` URLs and 35-day search window baked in |
| P1 | 🔵 HARDCODED | X API base URL | `x_scout.py:19` | `https://api.x.com/2/tweets/search/recent` should be in config |
| P1 | 🔵 HARDCODED | Default X queries | `x_scout.py:23-27` | 3 search queries hardcoded as fallback |
| P1 | 🔵 HARDCODED | X term tuples (TECH_TERMS, ROLE_TERMS, etc.) | `x_scout.py:35-76` | 7 hardcoded term tuples for classification |
| P1 | 🔵 HARDCODED | `DEFAULT_TARGETS` | `free_scout.py:35` | 5 hardcoded default targets (Greenhouse OpenAI, Anthropic, etc.) |
| P1 | 🔵 HARDCODED | `_india_clause` | `query_gen.py:142` | India-specific location appending logic baked into general query gen |
| P1 | 🔵 HARDCODED | `_scrape_remoteok` User-Agent spoof | `scout.py:606` | Hardcoded Chrome UA string for scraping |
| P2 | 🟡 SUSPECT | `_passes_beginner_job_filter` | `scout.py:229` | Only called from tests; `run()` does not invoke it — potential dead code |
| P2 | 🟡 SUSPECT | `_is_beginner_role` | `scout.py:182` | Only called by `_passes_beginner_job_filter` (which is DEAD) |
| P2 | 🟡 SUSPECT | `_is_strictly_recent` | `scout.py:145` | Only called by `_is_fresh_lead`; thin wrapper |
| P2 | 🟡 SUSPECT | `LAST_ERRORS` / `LAST_USAGE` module state | All 3 run files | Mutable module-level state accessed via `getattr` — fragile |
| P2 | 🟡 SUSPECT | `_parse_date` duplicate | `scout.py:71` vs `quality_gate.py:77` | Two different implementations of the same date parser; not shared |
| P2 | 🟡 SUSPECT | `_lead_text` duplicate | `scout.py:153` vs `quality_gate.py:62` | Nearly identical; different field set (quality_gate includes `location`) |
| P2 | 🟡 SUSPECT | `free_scout.py:run()` duplicated save logic | `free_scout.py:618-644` and `684-710` | ~40 lines of save code repeated identically for targets vs connectors |
| P2 | 🟡 SUSPECT | `HOT_LEAD_THRESHOLD` defined but unused in file | `quality_gate.py:20` | Defined in quality_gate but not referenced there; used by callers directly |
| P2 | 🟡 SUSPECT | `_scrape_reddit` no auth | `free_scout.py:470` | Uses public Reddit JSON endpoint without API key — rate limits may hit |
| P2 | 🔵 HARDCODED | `_CONNECTOR_MAX_ITEMS = 60` | `free_scout.py:44` | Custom connector item cap baked in |
| P2 | 🔵 HARDCODED | Timeout values (30s) in HTTP clients | Multiple | At least 10 hardcoded `timeout=30` occurrences across 3 files |
| P3 | 🔵 HARDCODED | `_role_terms` catalog | `query_gen.py:74-85` | 10 role category→alias mappings baked in |
| P3 | 🔵 HARDCODED | `_looks_role_like` terms | `scout.py:494-504` | 14 role indicator terms baked in |
| P3 | 🟢 CLEAN | `quality_gate.py:evaluate_lead_quality` | `quality_gate.py:139` | Well-structured, documented, deterministic, single-purpose |
| P3 | 🟢 CLEAN | `x_scout.py:signal_quality` | `x_scout.py:154` | Well-scoped scoring function with penalties |
| P3 | 🟢 CLEAN | `query_gen.py:_extract_domains` | `query_gen.py:22` | Clean helper, single responsibility |
| P3 | 🟢 CLEAN | `free_scout.py:_scrape_custom_connector` | `free_scout.py:99` | Well-designed generic connector pattern |

---

## 5. Dependencies

**Inbound (other units depend on this):**

| Consumer | What it imports | From |
|----------|----------------|------|
| `services/scanner.py` | `scout.run`, `query_gen.generate` | scout, query_gen |
| `services/ghost.py` | `query_gen.generate`, `scout.run` | query_gen, scout |
| `services/scout.py` | `x_scout.run`, `free_scout.run` | x_scout, free_scout |
| `routes/leads.py` | `scout.classify_job_seniority` | scout |
| `mcp_server.py` | `quality_gate.evaluate_lead_quality` | quality_gate |
| `tests/test_regressions.py` | Multiple private functions from all files | All 5 |
| `tests/test_observability.py` | `quality_gate._parse_date` | quality_gate |

**Outbound (this unit depends on others):**

| Dependency | What's used |
|------------|-------------|
| `agents/lead_intel` | signal_quality, outreach_drafts, fit_bullets, followup_sequence, etc. |
| `agents/browser_runtime` | launch_chromium |
| `agents/scoring_engine` | infer_experience_level (in query_gen.py) |
| `llm` | call_llm |
| `db/client` | url_exists, save_lead, rank_lead_by_feedback |
| `config` | settings |
| `config/secrets` | resolve_secret |
| `logger` | get_logger |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `httpx` | Async HTTP client | via pyproject.toml | 🟢 |
| `tenacity` | Retry decorators | via pyproject.toml | 🟢 |
| `pydantic` | Data models | via pyproject.toml | 🟢 |
| `playwright` | Headless browser | via pyproject.toml | 🟢 |
| `html2text` | HTML→Markdown conversion | via pyproject.toml | 🟢 |

---

## 6. First principles assessment

### `agents/scout.py`

1. **Does this file need to exist?** Yes — it's the primary job board scraper and orchestrator.
2. **Does it do what it claims?** Partially — name says "scout" but also handles HN, RSS, API sources, LLM extraction, dedup, saving; it's an orchestrator, not just a scraper.
3. **Is it the right place for this logic?** Partially — the `run()` function is a monolith. Source-specific scrapers could be extracted. Quality gate logic belongs in `quality_gate.py` (already refactored). Date parsing is duplicated there.
4. **What would break if deleted?** `services/scanner.py`, `services/ghost.py`, `routes/leads.py` (classify_job_seniority), `free_scout.py` (5 imports), `x_scout.py` (1 import).

### `agents/free_scout.py`

1. **Does this file need to exist?** Yes — organic source discovery is distinct from structured job board scraping.
2. **Does it do what it claims?** Yes — "free source scout" accurately describes its purpose.
3. **Is it the right place for this logic?** Yes — ATS, GitHub, HN, Reddit scraping naturally group together.
4. **What would break if deleted?** `services/scout.py` (_run_free_source_scan), `scout.py:_scrape_ats_target`, `tests/test_regressions.py`.

### `agents/x_scout.py`

1. **Does this file need to exist?** Yes — X/Twitter is a distinct signal source with unique API and classification needs.
2. **Does it do what it claims?** Yes — X/Twitter scout.
3. **Is it the right place for this logic?** Yes — self-contained module with single responsibility.
4. **What would break if deleted?** `services/scout.py` (_run_x_signal_scan), `tests/test_regressions.py`.

### `agents/quality_gate.py`

1. **Does this file need to exist?** Yes — shared quality gate used by 3 modules (scout, free_scout, mcp_server).
2. **Does it do what it claims?** Yes — lead quality gate.
3. **Is it the right place for this logic?** Yes — this is the right abstraction boundary.
4. **What would break if deleted?** `scout.py:run()`, `free_scout.py:run()`, `mcp_server.py`.

### `agents/query_gen.py`

1. **Does this file need to exist?** Yes — profile-tailored query generation is a distinct concern.
2. **Does it do what it claims?** Yes — generates search queries for job discovery.
3. **Is it the right place for this logic?** Partially — `_india_clause` and `_enrich_passthrough_targets` are board-specific hacks that could be pushed to config.
4. **What would break if deleted?** `services/scanner.py`, `services/ghost.py`.
