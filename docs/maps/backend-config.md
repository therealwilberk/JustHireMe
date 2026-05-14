# Map: backend-config
**File:** `docs/maps/backend-config.md`
**Codebase path(s):** `backend/config/`
**Files in scope:** 10
**Total lines:** ~1176
**Generated:** 2026-05-15

---

## 1. Unit summary

The `backend/config/` package is the typed configuration layer for the JustHireMe backend. It owns all hardcoded constants extracted from `main.py`, agent modules, and LLM glue — organized into domain-aligned Pydantic `BaseModel` schemas. It exposes a `settings` `SimpleNamespace` (the primary consumer interface), a `validate_all()` startup validator called by `main.py`, config-directory resolution via `resolver.py`, and a `resolve_secret()` helper that resolves secrets with env-var-first / SQLite-fallback semantics. Every domain module (`llm`, `scraping`, `scoring`, `generator`, `contact`, `app`, `logging`) exports a module-level `config` instance. The package depends on `pydantic` (schemas), `db.client` (secrets fallback), and the standard library. It is consumed by virtually every backend module: `main.py`, `llm.py`, `logger.py`, all agents, all services, and the settings route.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `config/__init__.py` | 51 | Package init: exports `settings`, `validate_all()`, `init_config_dir()`, `get_config_dir()` | 🟢 CLEAN |
| 2 | `config/app.py` | 227 | Application-domain settings (ports, CORS, tokens, scan limits, env key names, ghost mode, etc.) | 🟢 CLEAN |
| 3 | `config/contact.py` | 93 | Hunter.io / Proxycurl API settings, ATS host list, contact priority roles, manager name regexes | 🟢 CLEAN |
| 4 | `config/generator.py` | 102 | PDF generator defaults (colors, sizing, word limits, font sizes, scale values) | 🟢 CLEAN |
| 5 | `config/llm.py` | 114 | LLM provider models, endpoints, key names, timeouts, probe URLs | 🟢 CLEAN |
| 6 | `config/logging.py` | 25 | Log level, format string, output stream, file rotation | 🟢 CLEAN |
| 7 | `config/resolver.py` | 61 | Config directory resolution (CLI → env → XDG → local fallback) | 🟢 CLEAN |
| 8 | `config/scoring.py` | 294 | Rubric weights, quality-gate thresholds, seniority config, full tech taxonomy & categories | 🟢 CLEAN |
| 9 | `config/scraping.py` | 156 | Scraper timeouts, retry config, per-source caps, API URLs, ATS endpoints, user agents | 🟢 CLEAN |
| 10 | `config/secrets.py` | 53 | `resolve_secret()` — env var with SQLite deprecation fallback | 🟢 CLEAN |

---

## 3. Detailed breakdown

### `config/__init__.py`

**Purpose:** Package entry point. Imports all domain configs, exposes the `settings` aggregate, the `validate_all()` startup validator, and lazy config-directory resolution. Name matches content precisely.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from types import SimpleNamespace` | stdlib | yes — `settings` aggregate | 🟢 CLEAN |
| `from pathlib import Path` | stdlib | yes — `_config_dir` and return types | 🟢 CLEAN |
| `from . import llm, scraping, scoring, generator, contact, app, logging as cfg_logging` | local | yes — all referenced in `validate_all()` and `settings` | 🟢 CLEAN |
| `from .resolver import resolve_config_dir` | local | yes — used in `init_config_dir()` | 🟢 CLEAN |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_config_dir` | `Path \| None` | `None` | `init_config_dir()`, `get_config_dir()` | 🟢 CLEAN — module-scoped lazy init |

**Classes:** None.

**Functions:**

#### `init_config_dir(argv: list[str] | None = None) -> Path`
- **Purpose:** One-time lazy initialization of the config directory path.
- **Called by:** `get_config_dir()` within this file; potentially externally (no cross-unit references found — only called within this file)
- **Calls:** `resolve_config_dir(argv)`
- **Side effects:** Mutates module global `_config_dir`
- **Hardcodes:** None
- **Flag:** 🟡 SUSPECT — `init_config_dir` and `get_config_dir` are only referenced within this file. No external caller found. May be dead code or called dynamically.

#### `get_config_dir() -> Path`
- **Purpose:** Lazily returns the resolved config directory path.
- **Called by:** unknown within this unit — check cross-refs (no external references found)
- **Calls:** `init_config_dir()` (on miss)
- **Side effects:** Triggers `init_config_dir()` on first call
- **Hardcodes:** None
- **Flag:** 🟡 SUSPECT — same as `init_config_dir`; no external callers found. Possibly dead.

#### `validate_all() -> list[str]`
- **Purpose:** Rebuilds and validates all Pydantic domain configs, collecting errors.
- **Called by:** `backend/main.py:70`
- **Calls:** `cfg.model_rebuild()`, `cfg.model_dump()`, `cfg.model_validate()` for each domain
- **Side effects:** None
- **Hardcodes:** Hardcodes the domain list `dict` literal (acceptable — it's the domain registry)
- **Flag:** 🟢 CLEAN — actively used at startup, well-structured

**Exports:**

| Export | Known importers |
|--------|----------------|
| `settings` | `main.py`, `llm.py`, `logger.py`, `routes/*`, `services/*`, `agents/*`, `db/client.py`, tests |
| `validate_all` | `main.py` |
| `init_config_dir` | No external references found |
| `get_config_dir` | No external references found |

---

### `config/app.py`

**Purpose:** Application-wide settings — ports, CORS, ghost-mode scheduler, lead freshness, auto-approve thresholds, job target defaults, discovery limits, identity/sensitive key patterns, evaluator profile keys, scan limits, env variable names for app data / browser / auto-apply / bearer tokens. Cleanly organized.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 CLEAN |
| `from typing import Literal` | stdlib | no — imported but `Literal` is not used in this file | 🟡 SUSPECT — unused import |

**Module-level constants & state:** None.

**Classes:**

#### `GhostModeConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Background ghost-mode scheduler interval and job ID.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| (none defined — Pydantic data class) | | | 🟢 |

#### `WebSocketConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** WebSocket heartbeat timeout.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `PortConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Dev server port, bind host, uvicorn log level.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `TokenConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** API bearer token entropy size.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `CORSConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** CORS local origin regex.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `LeadFreshnessConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Max age for leads to be considered fresh.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `AutoApproveConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Score threshold for auto-approval.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `JobTargetDefaults(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Default job board target URLs and blocked-marker keywords.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN — but note: `global_targets` is a list of mixed types (named sources like `"hn-hiring"`, site-scoped searches like `"site:linkedin.com/jobs"`, API URLs). The mixing of URL and non-URL entries is by design per `services/job_targets.py` which interprets them differently.

#### `MarketFocusConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Regional targeting settings.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN — but limited: only `"global"` supported

#### `DiscoveryConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Lead-discovery term/hint limits.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `IdentityKeys(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Settings key names for identity/profile fields.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `SensitiveKeys(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Key patterns for masking in output.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `EvaluatorProfileKeys(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Ordered profile keys used by the evaluator agent.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `ReEvaluationConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Status values that lock a lead from re-evaluation.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `ScanConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Limits for scanning runs.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `AppDataEnvConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Environment variable names for app data directory resolution.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `BrowserEnvConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Environment variable names for browser runtime configuration.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `AutoApplyEnvConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Env var name for enabling auto-apply mode.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `BearerTokenEnvConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Env var names for X/Twitter bearer tokens.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `AppSettingsKeyNames(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Settings key names for app-level secrets.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

#### `AppConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Aggregate root containing all app sub-configs.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `AppConfig`) | `config/__init__.py` as `app.config` |

---

### `config/contact.py`

**Purpose:** Contact lookup API configuration — Hunter.io and Proxycurl endpoints, ATS host list, priority hiring roles, manager name regex patterns, API key env/settings key names, skills detection pattern for emails. Clean.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes (`Field` used in `ContactConfig`) | 🟢 CLEAN |

**Module-level constants & state:** None.

**Classes:**

#### `HunterConfig(BaseModel)` — 🟢 CLEAN
#### `ProxycurlConfig(BaseModel)` — 🟢 CLEAN
#### `ATSHosts(BaseModel)` — 🟢 CLEAN
#### `ContactPriority(BaseModel)` — 🟢 CLEAN
#### `ManagerNamePatterns(BaseModel)` — 🟢 CLEAN
#### `ContactAPIKeyNames(BaseModel)` — 🟢 CLEAN
#### `ContactSettingsKeyNames(BaseModel)` — 🟢 CLEAN
#### `SkillsDetection(BaseModel)` — 🟢 CLEAN
#### `ContactConfig(BaseModel)` — 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `ContactConfig`) | `config/__init__.py` as `contact.config` |

---

### `config/generator.py`

**Purpose:** PDF generator configuration — colors, sizing/scaling, font sizes, document word limits, outreach text defaults, asset subdirectory. Maps from `backend/agents/generator.py`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 CLEAN |
| `from typing import Literal` | stdlib | yes — used in `PDFSizing.page_format` | 🟢 CLEAN |

**Module-level constants & state:** None.

**Classes:**

#### `PDFColors(BaseModel)` — 🟢 CLEAN
#### `PDFSizing(BaseModel)` — 🟢 CLEAN
#### `PDFSizes(BaseModel)` — 🟢 CLEAN
#### `DocumentWordLimits(BaseModel)` — 🟢 CLEAN
#### `OutreachDefaults(BaseModel)` — 🟢 CLEAN
#### `AssetsConfig(BaseModel)` — 🟢 CLEAN
#### `GeneratorConfig(BaseModel)` — 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `GeneratorConfig`) | `config/__init__.py` as `generator.config` |

---

### `config/llm.py`

**Purpose:** LLM provider configuration — default model IDs, OpenAI-compatible base URLs, env var key names, settings key names, provider-specific URLs (Anthropic, Gemini, Groq, DeepSeek, Ollama), probe URLs, timeouts.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 CLEAN |
| `from typing import Literal` | stdlib | no — `Literal` is not used in this file | 🟡 SUSPECT — unused import |

**Module-level constants & state:** None.

**Classes:**

#### `LLMProviderDefaults(BaseModel)` — 🟢 CLEAN
#### `LLMProviderEndpoints(BaseModel)` — 🟢 CLEAN
#### `LLMKeyNames(BaseModel)` — 🟢 CLEAN
#### `LLMSettingsKeyNames(BaseModel)` — 🟢 CLEAN
#### `LLMProviderSpecific(BaseModel)` — 🟢 CLEAN
#### `LLMConfig(BaseModel)` — 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `LLMConfig`) | `config/__init__.py` as `llm.config`; `llm.py` reads `settings.llm.*` heavily |

---

### `config/logging.py`

**Purpose:** Logging configuration — env var for level override, default level, format string, date format, output stream, propagate flag, file-rotation settings.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 CLEAN |
| `from typing import Literal` | stdlib | no — `Literal` is not used in this file | 🟡 SUSPECT — unused import |

**Module-level constants & state:** None.

**Classes:**

#### `LoggingConfig(BaseModel)` — 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `LoggingConfig`) | `config/__init__.py` as `cfg_logging.config`; `logger.py` uses `settings.logging.*` |

---

### `config/resolver.py`

**Purpose:** Config directory resolution with a 5-level priority hierarchy: CLI `--config-dir` → `JHM_CONFIG_DIR` env → `$XDG_CONFIG_HOME/JustHireMe/` → `~/.config/JustHireMe/` → `./data/config/`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import os` | stdlib | yes — `_from_env()`, `_from_xdg()` | 🟢 CLEAN |
| `import sys` | stdlib | yes — `resolve_config_dir()` default arg | 🟢 CLEAN |
| `from pathlib import Path` | stdlib | yes | 🟢 CLEAN |
| `from typing import Optional` | stdlib | yes — return types | 🟢 CLEAN (could use `\|` syntax but consistent with rest of codebase) |

**Module-level constants & state:** None.

**Classes:** None.

**Functions:**

#### `resolve_config_dir(argv: list[str] | None = None) -> Path`
- **Purpose:** Entry point: tries CLI → env → XDG → local fallback.
- **Called by:** `config/__init__.py:init_config_dir()`
- **Calls:** `_from_cli()`, `_from_env()`, `_from_xdg()`, `_local_fallback()`
- **Side effects:** None (reads env, filesystem stat checks)
- **Hardcodes:** `"JustHireMe"` subdirectory name, `"./data/config/"` fallback path
- **Flag:** 🟢 CLEAN — well-structured with clear priority hierarchy

#### `_from_cli(argv: list[str]) -> Optional[Path]`
- **Purpose:** Parse `--config-dir PATH` from CLI args.
- **Called by:** `resolve_config_dir()`
- **Flag:** 🟢 CLEAN

#### `_from_env() -> Optional[Path]`
- **Purpose:** Read `JHM_CONFIG_DIR` env var.
- **Called by:** `resolve_config_dir()`
- **Flag:** 🟢 CLEAN

#### `_from_xdg() -> Optional[Path]`
- **Purpose:** Check XDG config home and `~/.config` fallback.
- **Called by:** `resolve_config_dir()`
- **Flag:** 🟢 CLEAN

#### `_local_fallback() -> Path`
- **Purpose:** Return `./data/config/` as development fallback.
- **Called by:** `resolve_config_dir()`
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `resolve_config_dir` | `config/__init__.py` |

---

### `config/scoring.py`

**Purpose:** Scoring/rubric configuration — rubric weights (basic and semantic), quality-gate thresholds and penalties, seniority level definitions and caps, evaluator prompt limits, full tech taxonomy (field → alias tuples), and tech category mapping (field → category string). Largest file in the unit.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes — deferred evaluation | 🟢 CLEAN |
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 CLEAN |
| `from typing import Literal` | stdlib | no — `Literal` is not used in this file | 🟡 SUSPECT — unused import |

**Module-level constants & state:** None.

**Classes:**

#### `RubricWeights(BaseModel)` — 🟢 CLEAN
#### `SemanticRubricWeights(BaseModel)` — 🟢 CLEAN
#### `QualityGateThresholds(BaseModel)` — 🟢 CLEAN
#### `QualityGatePenalties(BaseModel)` — 🟢 CLEAN
#### `SeniorityLevelConfig(BaseModel)` — 🟢 CLEAN
#### `EvaluatorConfig(BaseModel)` — 🟢 CLEAN
#### `TechTaxonomy(BaseModel)` — 🟢 CLEAN — massive but well-structured; field names use Python-safe aliases (e.g., `C__plusplus`)
#### `TechCategory(BaseModel)` — 🟢 CLEAN — mirrors `TechTaxonomy` field set 1:1, maps each to a category string

#### `ScoringConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Aggregate root for scoring configs.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `ScoringConfig`) | `config/__init__.py` as `scoring.config` |

---

### `config/scraping.py`

**Purpose:** Scraping/scout configuration — per-source timeouts (HTTP, Apify, Playwright, RSS, HN, X, custom connectors), retry/exponential-backoff settings, per-source result caps, source API URLs (HN Algolia, RemoteOK, Reddit, GitHub, Google, Apify, X), HN-specific query/title regexes, ATS endpoint URL templates, description-length limits per source, and user-agent strings.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 CLEAN |
| `from typing import Literal` | stdlib | no — not used in this file | 🟡 SUSPECT — unused import |

**Module-level constants & state:** None.

**Classes:**

#### `ScraperTimeouts(BaseModel)` — 🟢 CLEAN — well-typed with `ge`/`le` bounds
#### `RetryConfig(BaseModel)` — 🟢 CLEAN
#### `ScraperLimits(BaseModel)` — 🟢 CLEAN — extensive but well-organized
#### `SourceCaps(BaseModel)` — 🟢 CLEAN
#### `APISourceURLs(BaseModel)` — 🟢 CLEAN
#### `ApifyKeyNames(BaseModel)` — 🟢 CLEAN
#### `ApifySettingsKeyNames(BaseModel)` — 🟢 CLEAN
#### `HNConfig(BaseModel)` — 🟢 CLEAN
#### `ATSEndpoints(BaseModel)` — 🟢 CLEAN
#### `DescriptionLimits(BaseModel)` — 🟢 CLEAN
#### `UserAgentConfig(BaseModel)` — 🟢 CLEAN

#### `ScrapingConfig(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Aggregate root for all scraping configs.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

**Functions:** None.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `config` (instance of `ScrapingConfig`) | `config/__init__.py` as `scraping.config` |

---

### `config/secrets.py`

**Purpose:** Single-purpose module providing `resolve_secret()` — resolves secrets with env var priority and SQLite deprecation fallback. Includes `_warn_sqlite_fallback()` with `lru_cache` for one-shot warnings.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import os` | stdlib | yes — `os.environ.get()` | 🟢 CLEAN |
| `import logging` | stdlib | yes — `_log` | 🟢 CLEAN |
| `from functools import lru_cache` | stdlib | yes — `_warn_sqlite_fallback` | 🟢 CLEAN |
| `from db.client import get_setting` | local | yes — `resolve_secret()` fallback path | 🟣 COUPLED — imports from `db.client` which is a separate unit; creates a circular-ish dependency (config depends on db; db depends on config for settings) |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | `logging.Logger` | `getLogger(__name__)` | `resolve_secret()`, `_warn_sqlite_fallback()` | 🟢 CLEAN |

**Classes:** None.

**Functions:**

#### `resolve_secret(env_var_name: str, settings_key: str | None = None, warn_once: bool = True) -> str | None`
- **Purpose:** Resolve a secret: check env var first, then SQLite (deprecated), return `None` if neither found.
- **Called by:** `main.py`, `llm.py`, `services/scout.py`, `services/scanner.py`, `services/job_targets.py`, `services/ghost.py`, `routes/settings.py`, `agents/x_scout.py`, `agents/free_scout.py`, `agents/contact_lookup.py`
- **Calls:** `os.environ.get()`, `get_setting()`, `_warn_sqlite_fallback()`
- **Side effects:** Logs warnings via `_log.warning()`; `_warn_sqlite_fallback()` mutates `lru_cache`
- **Hardcodes:** None
- **Flag:** 🟢 CLEAN — well-designed, tested, widely used

#### `_warn_sqlite_fallback(env_var_name: str, settings_key: str) -> None`
- **Purpose:** Warn exactly once per `(env_var, settings_key)` pair to avoid log spam.
- **Called by:** `resolve_secret()` (when `warn_once=True`); also directly imported and called by `tests/test_secrets.py`
- **Calls:** `_log.warning()`
- **Side effects:** Logs warning; `lru_cache` caches calls
- **Flag:** 🟢 CLEAN — correctly uses `lru_cache` for one-shot dedup

**Exports:**

| Export | Known importers |
|--------|----------------|
| `resolve_secret` | `main.py`, `llm.py`, `services/scout.py`, `services/scanner.py`, `services/job_targets.py`, `services/ghost.py`, `routes/settings.py`, `agents/x_scout.py`, `agents/free_scout.py`, `agents/contact_lookup.py`, `tests/test_secrets.py` |
| `_warn_sqlite_fallback` | `tests/test_secrets.py` (for cache manipulation) |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P3 | 🟢 CLEAN | All files and structures | various | Well-structured, typed, documented with source comments, actively used |
| P2 | 🟡 SUSPECT | `Literal` import | `app.py:10` | Imported but never used in the file |
| P2 | 🟡 SUSPECT | `Literal` import | `llm.py:2` | Imported but never used in the file |
| P2 | 🟡 SUSPECT | `Literal` import | `logging.py:2` | Imported but never used in the file |
| P2 | 🟡 SUSPECT | `Literal` import | `scoring.py:4` | Imported but never used in the file |
| P2 | 🟡 SUSPECT | `Literal` import | `scraping.py:2` | Imported but never used in the file |
| P2 | 🟡 SUSPECT | `init_config_dir` | `__init__.py:10` | No external callers found in codebase — may be dead |
| P2 | 🟡 SUSPECT | `get_config_dir` | `__init__.py:17` | No external callers found in codebase — may be dead |
| P2 | 🟣 COUPLED | `from db.client import get_setting` | `secrets.py:6` | Config module depends on `db.client`; `db.client` depends on `config` for settings — potential circular dependency |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `main.py` — imports `validate_all`, `resolve_secret`, and the `settings` namespace extensively
- `llm.py` — imports `settings` and `resolve_secret`; reads `settings.llm.*` heavily
- `logger.py` — imports `settings`; reads `settings.logging.*`
- `services/scout.py` — imports `settings` and `resolve_secret`
- `services/scanner.py` — imports `settings` and `resolve_secret`
- `services/job_targets.py` — imports `settings` and `resolve_secret`
- `services/ghost.py` — imports `settings` and `resolve_secret`
- `services/provider_probe.py` — imports `settings`
- `routes/settings.py` — imports `settings` and `resolve_secret`
- `routes/misc.py` — imports `settings`
- `agents/actuator.py` — imports `settings`
- `agents/x_scout.py` — imports `settings` and `resolve_secret`
- `agents/free_scout.py` — imports `settings` and `resolve_secret`
- `agents/contact_lookup.py` — imports `config` (whole module) and `resolve_secret`
- `agents/browser_runtime.py` — imports `settings`
- `db/client.py` — imports `settings` (lazy, inside function)
- `tests/test_secrets.py` — imports `resolve_secret`, `_warn_sqlite_fallback`
- `tests/test_log_context.py` — imports `settings`

**Outbound (this unit depends on others):**
- `db.client` — `secrets.py` imports `get_setting` for SQLite fallback

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| pydantic | Schema definition and validation (v2) | Not pinned in this file (in project's pyproject.toml) | 🟢 CLEAN |

---

## 6. First principles assessment

### `config/__init__.py`
1. **Does this file need to exist?** Yes — it's the package entry point.
2. **Does it do what it claims?** Yes — imports and re-exports domain configs, provides validation and config-dir resolution.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** Everything — every backend module imports from here.

### `config/app.py`
1. **Does this file need to exist?** Yes — application-domain configs.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes — well-separated from scraping, scoring, etc.
4. **What would break if deleted?** `config/__init__.py` import fails; any code using `settings.app.*`.

### `config/contact.py`
1. **Does this file need to exist?** Yes — contact lookup config.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** `config/__init__.py` import fails; `contact_lookup.py` references.

### `config/generator.py`
1. **Does this file need to exist?** Yes — PDF generator config.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** `config/__init__.py` import fails; `generator.py` references.

### `config/llm.py`
1. **Does this file need to exist?** Yes — LLM provider config.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** `config/__init__.py` import fails; `llm.py` heavily references.

### `config/logging.py`
1. **Does this file need to exist?** Yes — logging config.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** `config/__init__.py` import fails; `logger.py` references.

### `config/resolver.py`
1. **Does this file need to exist?** Yes — separate concern from config schemas.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes — but note: it's currently only consumed internally by `__init__.py`, and `get_config_dir`/`init_config_dir` have no external callers.
4. **What would break if deleted?** `config/__init__.py` import fails; config directory resolution would be impossible.

### `config/scoring.py`
1. **Does this file need to exist?** Yes — scoring/rubric config.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes — the tech taxonomy and category mapping are well-placed here.
4. **What would break if deleted?** `config/__init__.py` import fails; scoring engine and quality gate references.

### `config/scraping.py`
1. **Does this file need to exist?** Yes — scraping config.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** `config/__init__.py` import fails; scout/scanner references.

### `config/secrets.py`
1. **Does this file need to exist?** Yes — critical for secure secret resolution.
2. **Does it do what it claims?** Yes — name matches content.
3. **Is it the right place for this logic?** Partially — the `db.client` dependency creates a potential circular dependency. Consider moving to a lower-level utility or using an injected resolver.
4. **What would break if deleted?** Secret resolution across the entire backend; `test_secrets.py` tests.
