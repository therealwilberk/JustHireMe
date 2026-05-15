# Map: backend-main
**File:** `docs/maps/backend-main.md`
**Codebase path(s):** `backend/main.py`, `backend/llm.py`, `backend/mcp_server.py`, `backend/logger.py`, `backend/log_context.py`
**Files in scope:** 5
**Total lines:** ~974
**Generated:** 2026-05-15

---

## 1. Unit summary

The **backend-main** unit owns the FastAPI application lifecycle (startup config validation, auth, CORS, scheduler, router registration), the LLM provider abstraction layer (17 providers, per-step config resolution, structured + raw calling), a minimal MCP stdio server exposing three job-intelligence tools, and the structured logging pipeline (contextvar-based correlation IDs, log enrichment filter, logger factory with file rotation). It is consumed by every agent, route, and service in the backend — `get_logger()` is the single most imported symbol across the entire codebase. It depends on `config/` for all its Pydantic-schema'd settings and on `core/config_constants` for the API token, scheduler singleton, bearer scheme, and CORS regex.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `backend/main.py` | 181 | FastAPI entrypoint: lifespan, middleware, CORS, auth, router registration | 🟢 CLEAN — no stale re-exports; ghost interval driven from config |
| 2 | `backend/llm.py` | 355 | LLM provider abstraction: 17 providers, per-step config resolution, structured + raw calling | 🟢 CLEAN — all URLs, tokens, and timeouts driven from config; monolithic if/elif is 🟣 COUPLED but values are no longer hardcoded |
| 3 | `backend/mcp_server.py` | 201 | Minimal MCP stdio server (no SDK): 3 tools, JSON-RPC 2.0 | 🟢 CLEAN — focused, minimal, stdin-limited, config-driven defaults |
| 4 | `backend/logger.py` | 93 | Logging setup: CorrelationFilter, get_logger factory | 🟢 CLEAN — dead ContextFormatter removed |
| 5 | `backend/log_context.py` | 103 | contextvar-based correlation context propagation | 🟢 CLEAN — single responsibility, well-typed |

---

## 3. Detailed breakdown

### `backend/main.py`

**Purpose:** FastAPI application entrypoint. Binds an ephemeral port and emits token/port to stdout before slow imports load (sidecar bootstrap), then starts uvicorn. Defines lifespan callbacks (config validation, secret diagnostics, ghost scheduler), HTTP middleware (correlation ID, bearer token auth), CORS setup, and router registration.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `secrets` | stdlib | no (re-exported from core.config_constants) | 🟢 — standard |
| `socket` | stdlib | `_bind_port` | 🟢 |
| `sys` | stdlib | stdout write, exit | 🟢 |
| `core.config_constants._API_TOKEN` | local | first `__main__`, `require_http_token` | 🟢 |
| `config.validate_all` | local | `_validate_config_on_startup` | 🟢 |
| `config.secrets.resolve_secret` | local | `_log_startup_secret_diagnostics` | 🟢 |
| `contextlib.asynccontextmanager` | stdlib | `lifespan` | 🟢 |
| `fastapi.FastAPI`, `Request`, `status` | 3rd-party | app, middleware, response | 🟢 |
| `fastapi.middleware.cors.CORSMiddleware` | 3rd-party | CORS setup | 🟢 |
| `fastapi.responses.JSONResponse` | 3rd-party | 401 response | 🟢 |
| `config.settings` | local | `_log_startup_secret_diagnostics`, `lifespan` | 🟢 |
| `log_context.new_context`, `set_context`, `reset_context` | local | `correlation_context_middleware` | 🟢 |
| `core.config_constants._log`, `_sched`, `_LOCAL_ORIGIN_RE`, `_bearer` | local | lifespan, CORS, auth middleware | 🟢 |
| `routes.*` (8 routers) | local | `app.include_router` | 🟢 |
| `services.ghost._ghost_tick` | local | `lifespan` | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| (none beyond imports) | | | | |

**Functions:**

#### `_bind_port() -> int`
- **Purpose:** Bind an ephemeral TCP socket on 127.0.0.1 and return the socket (kept open to prevent TOCTOU races on port reuse).
- **Called by:** first `__main__` block
- **Calls:** `socket.socket`, `s.bind`
- **Side effects:** Opens a socket (stays open as `_sock`)
- **Hardcodes:** `127.0.0.1`, `0` (ephemeral port)
- **Flag:** 🟢 CLEAN

#### `_validate_config_on_startup()`
- **Purpose:** Run `validate_all()` and `sys.exit(1)` on failure.
- **Called by:** `lifespan`
- **Calls:** `validate_all`, `_log.critical`, `sys.exit`
- **Side effects:** Exits process on config failure
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_log_startup_secret_diagnostics()`
- **Purpose:** Log which secrets are configured at DEBUG level.
- **Called by:** `lifespan`
- **Calls:** `resolve_secret`, `_log.debug`
- **Side effects:** None
- **Flag:** 🟢 CLEAN — all env/settings key pairs are read from config schema objects

**Classes:**

None.

#### `lifespan(app: FastAPI)` [async context manager]
- **Purpose:** Startup: validate config, log secret diag, start ghost scheduler. Shutdown: stop scheduler.
- **Called by:** FastAPI framework (via `app = FastAPI(lifespan=lifespan)`)
- **Calls:** `_validate_config_on_startup`, `_log_startup_secret_diagnostics`, `_sched.*`, `_ghost_tick`
- **Side effects:** Scheduler start/stop
- **Flag:** 🟢 CLEAN — ghost interval driven from `settings.app.ghost_mode.interval_hours`

**Middleware:**

#### `correlation_context_middleware(request, call_next)` [HTTP middleware]
- **Purpose:** Attach/extract X-Correlation-ID header and propagate via contextvar.
- **Flag:** 🟢 CLEAN

#### `require_http_token(request, call_next)` [HTTP middleware]
- **Purpose:** Bearer token auth, skipping OPTIONS and /health.
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `app` | `tests/test_api.py`, `tests/test_response_contracts.py`, `tests/test_log_context.py` |
| `_bind_port` | `tests/test_startup.py` |

---

### `backend/llm.py`

**Purpose:** LLM provider abstraction layer. Resolves provider/api-key/model per pipeline step via a 4-tier priority chain (step setting → global setting → env var → hardcoded default). Provides `call_llm()` for structured Pydantic output and `call_raw()` for free-form text. Supports 17 providers: anthropic, groq, gemini, nvidia, openai, deepseek, xai, kimi, mistral, openrouter, together, fireworks, cerebras, perplexity, huggingface, custom, ollama. The monolithic if/elif chain duplicates provider-specific logic across both functions.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `os` | stdlib | `_provider_base_url` (env var fallback) | 🟢 — single-use stdlib import |
| `httpx` | 3rd-party | `_TIMEOUT` (only uses `httpx.Timeout`) | 🟢 |
| `anthropic` | 3rd-party | `call_llm`, `call_raw` (anthropic branch) | 🟢 |
| `instructor` | 3rd-party | `_client_nvidia`, `call_llm` (groq, gemini, openai, deepseek, openai-compat branches) | 🟢 |
| `openai.OpenAI` | 3rd-party | client constructors throughout | 🟢 |
| `pydantic.BaseModel` | 3rd-party | `call_llm` type hint, `_parse_fallback` | 🟢 |
| `config.settings` | local | module-level dicts, `_provider_base_url` | 🟢 |
| `db.client.get_setting` | local | `_provider_base_url`, `_resolve`, `call_llm` (ollama branch) | 🟢 |
| `logger.get_logger` | local | `_log` | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | `get_logger(__name__)` | `_resolve`, `call_llm`, `call_raw` | 🟢 |
| `_TIMEOUT` | `httpx.Timeout` | from `settings.llm.timeout_seconds` / `connect_timeout_seconds` | All `OpenAI(... timeout=...)` calls | 🟢 — config-driven |
| `_KEY_NAMES` | dict[str,str] | from `settings.llm.settings_key_names` | `_resolve` | 🟢 |
| `_ENV_NAMES` | dict[str,str] | from `settings.llm.env_key_names` | `_resolve` | 🟢 |
| `_DEFAULT_MODELS` | dict[str,str] | from `settings.llm.default_models` | `_resolve` | 🟢 |
| `_OPENAI_COMPAT_BASE_URLS` | dict[str,str] | from `settings.llm.compat_endpoints` | `_provider_base_url`, `_OPENAI_COMPAT_PROVIDERS`; also imported by `services/provider_probe.py` and `routes/settings.py` | 🟢 |
| `_OPENAI_COMPAT_PROVIDERS` | set[str] | `set(_OPENAI_COMPAT_BASE_URLS) \| {"custom"}` | `call_llm`, `call_raw` (dispatch to compat branch) | 🟢 |

**Functions:**

#### `_provider_base_url(provider: str) -> str`
- **Purpose:** Resolve base URL for OpenAI-compatible providers. Custom provider has 3-tier fallback (db setting → env var → hardcoded).
- **Called by:** `_client_openai_compat`
- **Calls:** `get_setting`, `os.environ.get`
- **Hardcodes:** `custom` provider fallback chain values from `settings.llm.provider_specific`
- **Flag:** 🟢 CLEAN — config-driven, with explicit fallback

#### `_resolve(step: str | None = None) -> tuple[str, str, str]`
- **Purpose:** Resolve (provider, api_key, model) for a pipeline step. 4-tier priority.
- **Called by:** `resolve_config`, `call_llm`, `call_raw`
- **Calls:** `get_setting`, `resolve_secret` (lazy import inside fn)
- **Side effects:** Logs debug line when step is set
- **Flag:** 🟢 CLEAN — well-documented priority chain

#### `resolve_config(step: str | None = None) -> tuple[str, str, str]`
- **Purpose:** Public wrapper around `_resolve` for agents that need provider-specific request shapes.
- **Called by:** `agents/ingestor.py`, `agents/actuator.py`, `agents/help_agent.py`
- **Flag:** 🟢 CLEAN

#### `_client_nvidia(k: str)`
- **Purpose:** Build instructor-wrapped OpenAI client for NVIDIA.
- **Called by:** `call_llm` (nvidia branch)
- **Calls:** `instructor.from_openai`, `OpenAI`
- **Flag:** 🟢 CLEAN — base URL driven from `settings.llm.provider_specific.nvidia_base_url`

#### `_client_gemini(k: str)`
- **Purpose:** Build OpenAI-compatible client for Gemini.
- **Called by:** `call_llm`, `call_raw` (gemini branches)
- **Flag:** 🟢 CLEAN — base URL driven from `settings.llm.provider_specific.gemini_base_url`

#### `_client_openai_compat(provider: str, key: str)`
- **Purpose:** Build OpenAI client for any compat provider using `_provider_base_url`.
- **Called by:** `call_llm`, `call_raw` (compat branches)
- **Flag:** 🟢 CLEAN

#### `call_llm(s: str, u: str, m: type[BaseModel], step: str | None = None)`
- **Purpose:** Call LLM with structured output. Dispatches to provider-specific branch based on resolved provider.
- **Called by:** `agents/evaluator.py`, `agents/scout.py`, `agents/ingestor.py`, `agents/portfolio_ingestor.py`, `agents/query_gen.py`, `agents/github_ingestor.py`, `agents/generator.py`
- **Calls:** `_resolve`, `_parse_fallback`, `_client_nvidia`, `_client_gemini`, `_client_openai_compat`, `call_raw` (perplexity branch)
- **Flag:** 🟣 COUPLED — monolithic if/elif for 17 providers, every addition touches this function. All values (URLs, tokens, timeouts) now driven from `settings.llm`.

#### `call_raw(s: str, u: str, step: str | None = None) -> str`
- **Purpose:** Call LLM for free-form text output. Mirrors `call_llm` structure.
- **Called by:** `agents/generator.py`, `agents/help_agent.py`
- **Calls:** `_resolve`, `_client_gemini`, `_client_openai_compat`
- **Flag:** 🟣 COUPLED — mirrors `call_llm` pattern, double maintenance surface. All values now driven from `settings.llm`.

#### `_parse_fallback(u: str, m: type[BaseModel])`
- **Purpose:** Minimal local fallback — returns empty structured output when no API key is configured.
- **Called by:** `call_llm` (all branches on missing key)
- **Flag:** 🟢 CLEAN — well-scoped, handles `model_validate` vs `model_construct` gracefully

**Exports:**

| Export | Known importers |
|--------|----------------|
| `call_llm` | `agents/evaluator.py`, `agents/scout.py`, `agents/ingestor.py`, `agents/portfolio_ingestor.py`, `agents/query_gen.py`, `agents/github_ingestor.py`, `agents/generator.py` |
| `call_raw` | `agents/generator.py`, `agents/help_agent.py` |
| `resolve_config` | `agents/ingestor.py`, `agents/actuator.py`, `agents/help_agent.py` |
| `_resolve` | `agents/portfolio_ingestor.py` |
| `_OPENAI_COMPAT_BASE_URLS` | `services/provider_probe.py`, `routes/settings.py`, `tests/test_regressions.py` |
| `_KEY_NAMES` | `routes/settings.py` |
| `_DEFAULT_MODELS` | `tests/test_regressions.py` |
| `_ENV_NAMES` | `tests/test_regressions.py` |

---

### `backend/mcp_server.py`

**Purpose:** Minimal MCP (Model Context Protocol) stdio server that exposes three JustHireMe tools (score_job_fit, evaluate_lead_quality, extract_lead_intel) via JSON-RPC 2.0 over stdin/stdout. Deliberately avoids an SDK dependency. Implements the three MCP methods: `initialize`, `tools/list`, `tools/call`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `json` | stdlib | `_handle`, `_tool_result`, `main` | 🟢 |
| `sys` | stdlib | `main` (stdin/stdout loop) | 🟢 |
| `typing.Any`, `Callable` | stdlib | type hints | 🟢 |
| `agents.evaluator.score` | local | `_score_job_fit` | 🟣 COUPLED — direct import from agent module |
| `agents.lead_intel.*` (5 fns) | local | `_extract_lead_intel` | 🟣 COUPLED — direct imports from agent module |
| `agents.quality_gate.evaluate_lead_quality` | local | `_evaluate_lead` | 🟣 COUPLED |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `Json` | TypeAlias | `dict[str, Any]` | type hints throughout | 🟢 |
| `TOOLS` | dict | `{name: callable}` | `_handle` | 🟣 COUPLED — manual sync with `TOOL_DEFINITIONS` |
| `TOOL_DEFINITIONS` | list[Json] | 3 tool schemas | `_handle` (tools/list) | 🟣 COUPLED — manual sync with `TOOLS` dict |

**Functions:**

#### `_text(value: Any) -> str`
- **Purpose:** Safe string coercion with strip.
- **Called by:** `_score_job_fit`, `_evaluate_lead`, `_extract_lead_intel`
- **Flag:** 🟢 CLEAN

#### `_tool_result(data: Any) -> Json`
- **Purpose:** Wrap result in MCP content response format.
- **Called by:** handlers
- **Flag:** 🟢 CLEAN

#### `_error_result(message: str) -> Json`
- **Purpose:** Wrap error in MCP error response format.
- **Called by:** handlers on validation failure
- **Flag:** 🟢 CLEAN

#### `_score_job_fit(args: Json) -> Json`
- **Purpose:** Validate args and delegate to `agents.evaluator.score`.
- **Called by:** `_handle` (via TOOLS dispatch)
- **Flag:** 🟢 CLEAN

#### `_evaluate_lead(args: Json) -> Json`
- **Purpose:** Validate args and delegate to `agents.quality_gate.evaluate_lead_quality`.
- **Called by:** `_handle` (via TOOLS dispatch)
- **Flag:** 🟢 CLEAN — all defaults driven from `settings.scoring.quality_gate` and `settings.scraping.lead_max_age_days`

#### `_extract_lead_intel(args: Json) -> Json`
- **Purpose:** Validate text arg and delegate to 6 `agents.lead_intel` functions.
- **Called by:** `_handle` (via TOOLS dispatch)
- **Flag:** 🟢 CLEAN

#### `_handle(request: Json) -> Json | None`
- **Purpose:** JSON-RPC method dispatcher (initialize, notifications/initialized, tools/list, tools/call).
- **Called by:** `main`
- **Flag:** 🟢 CLEAN — well-structured dispatch

#### `main() -> None`
- **Purpose:** Stdin read loop with 64KB line limit; reads JSON-RPC requests line by line, dispatches via `_handle`, writes responses to stdout.
- **Called by:** `if __name__ == "__main__"`
- **Flag:** 🟢 CLEAN — stdin limited to 64KB per line to prevent OOM

**Exports:**

| Export | Known importers |
|--------|----------------|
| `_handle` | `tests/test_mcp_server.py` |

---

### `backend/logger.py`

**Purpose:** Logging setup. Defines `CorrelationFilter` (injects context fields from `CorrelationContext` onto log records) and `get_logger()` (factory that sets up stderr handler + optional rotating file handler with once-per-name semantics).

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `logging` | stdlib | throughout | 🟢 |
| `os` | stdlib | `get_logger` (env var lookups) | 🟢 |
| `sys` | stdlib | `get_logger` (stderr handler) | 🟢 |
| `logging.handlers.RotatingFileHandler` | stdlib | `get_logger` (file handler) | 🟢 |
| `config.settings` | local | `get_logger` (format, level, file config) | 🟢 |

**Classes:**

#### `CorrelationFilter(logging.Filter)`
- **Inherits from:** `logging.Filter`
- **Purpose:** Inject correlation context fields (correlation_id, subsystem, workflow, lead, job, node, degraded, retrying) onto log records.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `filter` | record: LogRecord | bool | Enrich record with ctx fields | 🟢 |


**Functions:**

#### `get_logger(name: str) -> logging.Logger`
- **Purpose:** Get/create a configured logger with once-per-name handler setup. Creates stderr StreamHandler with CorrelationFilter, optional RotatingFileHandler from env/config.
- **Called by:** Nearly every module in the backend (30+ call sites)
- **Calls:** `CorrelationFilter` (addFilter on handlers)
- **Side effects:** Adds handlers to logger, sets `propagate = False`
- **Hardcodes:** none — all values from settings + env vars
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `get_logger` | ~30 modules across entire backend |
| `CorrelationFilter` | `test_log_context.py` |

---

### `backend/log_context.py`

**Purpose:** Correlation context propagation via `contextvars`. Defines `CorrelationContext` dataclass (8 fields) and 5 functions: `new_context`, `get_context`, `set_context`, `reset_context`, `enrich`. Used by the logging system to enrich log records with workflow state across async boundaries.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `contextvars` | stdlib | `_context_var` | 🟢 |
| `uuid` | stdlib | `new_context` | 🟢 |
| `dataclasses.dataclass`, `replace` | stdlib | `CorrelationContext`, `enrich` | 🟢 |
| `typing.Optional` | stdlib | type hints | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_context_var` | `ContextVar[Optional[CorrelationContext]]` | default=None | `get_context`, `set_context`, `reset_context` | 🟢 |

**Classes:**

#### `CorrelationContext`
- **Inherits from:** dataclass
- **Purpose:** Contextual metadata (correlation_id, workflow_type, lead_id, job_id, node, subsystem, degraded, retrying) propagated across async boundaries.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| (dataclass-generated) | | | | 🟢 |

**Functions:**

#### `new_context(**overrides) -> CorrelationContext`
- **Purpose:** Create a new context with auto-generated UUID correlation_id (unless overridden).
- **Called by:** `main.py` (correlation middleware), `services/scout.py`, `services/ghost.py`, `routes/leads.py`
- **Flag:** 🟢 CLEAN

#### `get_context() -> Optional[CorrelationContext]`
- **Purpose:** Retrieve current context from contextvar.
- **Called by:** `logger.py` (CorrelationFilter.filter)
- **Flag:** 🟢 CLEAN

#### `set_context(ctx: CorrelationContext) -> contextvars.Token`
- **Purpose:** Set current context, return reset token.
- **Called by:** `main.py`, `services/scout.py`, `services/ghost.py`, `routes/leads.py`
- **Flag:** 🟢 CLEAN

#### `reset_context(token: contextvars.Token) -> None`
- **Purpose:** Restore previous context via token.
- **Called by:** `main.py`, `services/scout.py`, `services/ghost.py`, `routes/leads.py`
- **Flag:** 🟢 CLEAN

#### `enrich(**fields) -> contextvars.Token`
- **Purpose:** Merge fields into current context (immutable replace).
- **Called by:** unknown within this unit — check cross-refs
- **Raises:** RuntimeError if no context is active
- **Flag:** 🟡 SUSPECT — purpose is clear but no callers found within this unit; may be used by agents/services outside scope

**Exports:**

| Export | Known importers |
|--------|----------------|
| `CorrelationContext` | `logger.py` (lazy import), `test_log_context.py` |
| `new_context` | `main.py`, `services/scout.py`, `services/ghost.py`, `routes/leads.py` |
| `get_context` | `logger.py` (lazy import inside CorrelationFilter) |
| `set_context` | `main.py`, `services/scout.py`, `services/ghost.py`, `routes/leads.py` |
| `reset_context` | `main.py`, `services/scout.py`, `services/ghost.py`, `routes/leads.py` |
| `enrich` | unknown — cross-ref needed |

---

## 4. Flags summary

| Priority | Status | Item | File:Line | Resolution |
|----------|--------|------|-----------|------------|
| P0 | ✅ RESOLVED | `ContextFormatter` class | `logger.py` | Deleted — dead code, never wired |
| P1 | ✅ RESOLVED | NVIDIA base URL | `llm.py` | Now reads from `settings.llm.provider_specific.nvidia_base_url` |
| P1 | ✅ RESOLVED | Gemini base URL | `llm.py` | Now reads from `settings.llm.provider_specific.gemini_base_url` |
| P1 | ✅ RESOLVED | Groq base URL | `llm.py` | Now reads from `settings.llm.provider_specific.groq_base_url` |
| P1 | ✅ RESOLVED | Deepseek base URL | `llm.py` | Now reads from `settings.llm.provider_specific.deepseek_base_url` |
| P1 | ✅ RESOLVED | `max_tokens=4096` (anthropic) | `llm.py` | Now reads from `settings.llm.max_tokens` |
| P1 | ✅ RESOLVED | `max_tokens=16384` (nvidia) | `llm.py` | Now reads from `settings.llm.nvidia_max_tokens` |
| P1 | ✅ RESOLVED | `timeout=120.0` (anthropic) | `llm.py` | Now reads from `settings.llm.timeout_seconds` |
| P1 | ✅ RESOLVED | `hours=6` (ghost interval) | `main.py` | Now reads from `settings.app.ghost_mode.interval_hours` |
| P1 | ✅ RESOLVED | Secret diagnostic key list | `main.py` | Values already driven from config objects; manual enumeration acceptable |
| P1 | ✅ RESOLVED | MCP default values | `mcp_server.py` | Now read from `settings.scoring.quality_gate`, `settings.scraping.lead_max_age_days` |
| P2 | ✅ RESOLVED | Backward-compat re-exports | `main.py` | Removed; `ghost.py` imports `_fire_blocker` directly from `services.generator` |
| P2 | 🔄 NOTED | `TOOLS` / `TOOL_DEFINITIONS` manual sync | `mcp_server.py` | Structural coupling — needs architectural refactor to DRY |
| P2 | 🔄 NOTED | Monolithic if/elif in `call_llm` / `call_raw` | `llm.py` | 17 providers in single function; needs provider subpackage refactor |
| P2 | ✅ RESOLVED | `enrich()` no callers found | `log_context.py` | Investigated — zero production callers; function is tested, left in place |
| P2 | ✅ RESOLVED | `os` import in `llm.py` | `llm.py` | Single-use stdlib import, acceptable |
| P2 | ✅ RESOLVED | `get_logger` unused in `main.py` | `main.py` | Import removed |
| P2 | ✅ RESOLVED | No stdin read limit in MCP | `mcp_server.py` | Added 64KB `readline(65536)` limit |
| P3 | 🟢 CLEAN | `_bind_port`, middleware | `main.py` | Unchanged |
| P3 | 🟢 CLEAN | `_resolve` priority chain | `llm.py` | Unchanged |
| P3 | 🟢 CLEAN | `log_context.py` | `log_context.py` | Unchanged |
| P3 | 🟢 CLEAN | MCP _handle dispatch | `mcp_server.py` | Unchanged |
| P3 | 🟢 CLEAN | `get_logger` factory | `logger.py` | Unchanged |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- Every agent module depends on `get_logger` from `logger.py` (30+ modules)
- Agent modules depend on `call_llm`, `call_raw`, `resolve_config` from `llm.py`
- `services/provider_probe.py` imports `_OPENAI_COMPAT_BASE_URLS` from `llm.py`
- `routes/settings.py` imports `_KEY_NAMES`, `_OPENAI_COMPAT_BASE_URLS` from `llm.py`
- `routes/leads.py`, `services/scout.py`, `services/ghost.py` depend on `log_context.py`
- `services/ghost.py` imports `_fire_blocker` from `services.generator`
- All API tests import `app` from `main.py`
- `test_mcp_server.py` imports `_handle` from `mcp_server.py`

**Outbound (this unit depends on others):**
- `config/` — settings schemas for all 5 files (llm config, logging config, app config, etc.)
- `core/config_constants` — `_API_TOKEN`, `_sched`, `_log`, `_LOCAL_ORIGIN_RE`, `_bearer`
- `services/ghost` — `_ghost_tick` for scheduler
- `routes/` — 8 router modules
- `db/client` — `get_setting` for LLM resolution and provider URL lookup
- `agents/evaluator`, `agents/lead_intel`, `agents/quality_gate` — MCP tool implementations

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| fastapi | HTTP server, middleware, routing | pyproject.toml | 🟢 |
| uvicorn | ASGI server (main.py `__main__`) | pyproject.toml | 🟢 |
| anthropic | Claude API client | pyproject.toml | 🟢 |
| openai | OpenAI + compat provider clients | pyproject.toml | 🟢 |
| instructor | Structured output wrapper | pyproject.toml | 🟢 |
| httpx | Timeout config for OpenAI clients | pyproject.toml | 🟢 |
| pydantic | BaseModel for structured output | pyproject.toml | 🟢 |
| apscheduler | Ghost mode interval scheduler | pyproject.toml | 🟢 |

---

## 6. First principles assessment

### `backend/main.py`
1. **Does this file need to exist?** Yes — it is the application entrypoint.
2. **Does it do what it claims?** Yes — docstring accurately describes the dual-`__main__` bootstrap pattern.
3. **Is it the right place for this logic?** Yes — entrypoint, middleware, and router registration belong here.
4. **What would break if deleted?** The entire application — no FastAPI app, no server startup, no router registration, no auth middleware.

### `backend/llm.py`
1. **Does this file need to exist?** Yes — LLM provider abstraction is a core concern.
2. **Does it do what it claims?** Partially — the docstring doesn't mention the URL/config duplication issue or the monolithic provider chain.
3. **Is it the right place for this logic?** Mostly yes, but provider-specific client construction (`_client_nvidia`, `_client_gemini`) could live in a providers/ subpackage if the provider count grows further.
4. **What would break if deleted?** Every agent that calls `call_llm` or `call_raw` (~10 modules), plus `services/provider_probe.py` and `routes/settings.py` that import `_OPENAI_COMPAT_BASE_URLS`.

### `backend/mcp_server.py`
1. **Does this file need to exist?** Yes — exposes LLM-agent tools via MCP protocol without SDK dependency.
2. **Does it do what it claims?** Yes — implements initialize, tools/list, tools/call correctly.
3. **Is it the right place for this logic?** Yes — standalone protocol adapter, belongs as its own module.
4. **What would break if deleted?** MCP integration (external AI assistants that use JustHireMe tools) would be unavailable; `test_mcp_server.py` would fail. Application itself would still function.

### `backend/logger.py`
1. **Does this file need to exist?** Yes — centralized logging configuration.
2. **Does it do what it claims?** Yes — `CorrelationFilter` + standard `Formatter` enrich logs with correlation context.
3. **Is it the right place for this logic?** Yes — logging setup belongs in its own module.
4. **What would break if deleted?** Every module in the backend would lose its logger setup — ~30 modules would fail on `from logger import get_logger`.

### `backend/log_context.py`
1. **Does this file need to exist?** Yes — contextvar-based correlation propagation is a cross-cutting concern.
2. **Does it do what it claims?** Yes — docstring accurately describes thread-safe async context propagation.
3. **Is it the right place for this logic?** Yes — separated from logger.py to avoid circular imports (logger.py lazy-imports `get_context`).
4. **What would break if deleted?** `logger.py` (lazy import), `main.py` (middleware), `services/scout.py`, `services/ghost.py`, `routes/leads.py` — all depend on context functions.
