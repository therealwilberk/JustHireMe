# Map: Backend Tests
**File:** `docs/maps/backend-tests.md`
**Codebase path(s):** `backend/tests/`
**Files in scope:** 20
**Total lines:** ~6,676
**Generated:** 2026-05-15

---

## 1. Unit summary

The backend test suite lives entirely in `backend/tests/` and contains 328 deterministic tests designed to run in CI without external service dependencies. It covers the FastAPI HTTP routes (`test_api.py`), WebSocket connection manager concurrency (`test_websocket.py`), LangGraph evaluation graph happy-path and fault-tolerant failure modes (`test_graph.py`, `test_graph_failures.py`), MCP JSON-RPC protocol (`test_mcp_server.py`), SQLite pragma application and multi-connection contention (`test_sqlite.py`, `test_sqlite_reliability.py`), path/platform resolution (`test_paths.py`), secret resolution priority (`test_secrets.py`), structured logging observability (`test_observability.py`, `test_log_context.py`), domain logic regressions (`test_regressions.py`), startup smoke tests (`test_startup.py`), ScanManager state machine (`test_scan_manager.py`), GhostService phase contracts (`test_ghost_service.py`), and response-model completeness (`test_response_contracts.py`). Shared infrastructure lives in `conftest.py` (assertion helpers), `fakes.py` (storage backends), and `api_contracts.py` (per-endpoint contract schemas). `TEST_DOCS.md` is documentation, not code.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `TEST_DOCS.md` | 358 | Test suite documentation — overview, pyramid, markers, contracts philosophy | 🟢 Comprehensive docs |
| 2 | `conftest.py` | 273 | Shared assertion helpers (API + MCP contracts), path setup, ignore glob | 🟢 Clean, well-organized |
| 3 | `api_contracts.py` | 214 | Per-endpoint response contract schemas (TypedDict-style classes) | 🟢 Single source of truth |
| 4 | `fakes.py` | 128 | In-memory fakes for Kuzu, SQLite, LanceDB; `_install_storage_fakes()` | 🟢 Clean, well-factored |
| 5 | `test_api.py` | 551 | FastAPI route behavior: auth, health, leads CRUD, settings, ingest | 🟢 Strong coverage |
| 6 | `test_graph.py` | 142 | LangGraph happy path: compiles, invokes, score range, skip logic | 🟢 Adequate |
| 7 | `test_graph_failures.py` | 1290 | Graph fault-tolerant failure modes: 16 guarantee-classes | 🟢 Excellent coverage |
| 8 | `test_mcp_server.py` | 166 | JSON-RPC MCP protocol: initialize, tools/list, tools/call, errors | 🟢 Clean coverage |
| 9 | `test_paths.py` | 135 | Cross-platform path resolution, browser binary detection | 🟢 Good edge case coverage |
| 10 | `test_regressions.py` | 1205 | Domain logic regression prevention — scoring, quality, HN, targets | 🟠 Largest file, mixes concerns |
| 11 | `test_secrets.py` | 80 | Secret resolution priority chain, warning deduplication | 🟢 Focused |
| 12 | `test_websocket.py` | 515 | _CM concurrency: async-safety, controlled/deterministic tests | 🟢 Excellent |
| 13 | `test_sqlite.py` | 123 | SQLite pragma verification (WAL, FK, busy_timeout) | 🟢 Focused |
| 14 | `test_sqlite_reliability.py` | 539 | SQLite contention, WAL isolation, FK enforcement, AST audit | 🟢 Thorough |
| 15 | `test_observability.py` | 429 | except:pass replacement verification — severity, context | 🟢 Strong |
| 16 | `test_log_context.py` | 287 | Correlation context API, filter, formatter, middleware | 🟢 Clean |
| 17 | `test_startup.py` | 55 | Smoke tests: token/port emission, port binding | 🟢 Minimal but adequate |
| 18 | `test_scan_manager.py` | 43 | ScanManager lifecycle: start/stop/idle, ghost lock guard | 🟢 Concise |
| 19 | `test_ghost_service.py` | 30 | GhostService phase contract: preflight skip/return | 🟢 Concise |
| 20 | `test_response_contracts.py` | 113 | response_model= completeness + job target CRUD | 🟢 Important cross-check |

---

## 3. Detailed breakdown

### `TEST_DOCS.md`

**Purpose:** Comprehensive test suite documentation. Covers overview, test pyramid, commands, API contract philosophy (why status-only is insufficient, stable vs flexible fields, assertion principles, breaking change definition), orchestration semantics for the fault-tolerant graph pipeline, pytest markers, fakes infrastructure, Phase C coverage counts, and classification guide.

**Still needed:** Yes.

**Flag:** 🟢 — valuable living doc, though could drift from reality if not maintained.

### `conftest.py`

**Purpose:** Root test configuration. Adds `backend/` to `sys.path`, configures `collect_ignore_glob` for temp files. Provides reusable API contract assertion helpers and MCP (JSON-RPC) contract assertion helpers used across test files.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `sys` | stdlib | path setup | 🟢 |
| `Path` from `pathlib` | stdlib | path setup | 🟢 |
| `Any` from `typing` | stdlib | type hint for `_assert_body_type` | 🟢 |

**Functions:**

#### `assert_error_response(resp, status: int) -> dict`
- **Purpose:** Assert FastAPI error response has `{"detail": str | list}` shape.
- **Called by:** `test_api.py`, `test_response_contracts.py`, and indirectly via wrappers
- **Flag:** 🟢

#### `assert_detail_error(resp, status, detail_contains) -> dict`
- **Purpose:** Assert `{"detail": str}` error with optional substring match.

#### `assert_validation_error(resp, field_loc, error_type) -> dict`
- **Purpose:** Assert 422 Pydantic validation error with loc/msg/type structure.

#### `assert_success_response(resp, status, required_keys) -> dict`
- **Purpose:** Assert successful JSON response with optional field presence.

#### `assert_list_response(resp, status) -> list`
- **Purpose:** Assert JSON list response.

#### `assert_csv_response(resp, expected_header_fields) -> str`
- **Purpose:** Assert CSV response (200, text/csv, optional header check).

#### `assert_ok_response(resp, status) -> dict`
- **Purpose:** Assert `{"ok": true}` response.

#### `assert_detail_exactly`, `assert_detail_contains`
- **Purpose:** Finer-grained detail assertions.

#### `assert_mcp_response_structure(response, expected_id)`
- **Purpose:** Assert JSON-RPC shape: jsonrpc, id, error/result mutual exclusivity.

#### `assert_mcp_protocol_error(response, expected_code, message_contains, expected_id)`
- **Purpose:** Assert JSON-RPC protocol error with code+message structure.

#### `assert_mcp_tool_error(response, message_contains, expected_id)`
- **Purpose:** Assert MCP tool-level error with isError, content structure.

#### `assert_timestamp_iso8601`, `assert_all_str_items`, `assert_all_dict_items`, `_assert_body_type`
- **Purpose:** Generic shape helpers.

**Flag:** 🟢 CLEAN — well-factored, single-responsibility helpers.

### `api_contracts.py`

**Purpose:** Single source of truth for API response shapes. Each endpoint's contract is a class with constants (expected keys, types, statuses) so tests import schema knowledge rather than duplicating it.

**Imports:** `Any` from `typing`

**Classes:**

#### `HealthContract`, `AuthContract`, `NotFoundContract`, `ValidationContract`, `OkContract`, `LeadsListContract`, `ExportCsvContract`, `TemplateContract`, `SettingsValidateContract`, `SettingsSaveContract`, `FollowupsContract`, `PipelineRunContract`, `GenerateContract`, `FormReadContract`, `IdentityContract`, `SelectorsContract`, `LinkedInIngestContract`, `GithubIngestContract`, `ProfileImportContract`, `ProfileTemplateContract`, `PortfolioIngestContract`, `ScanContract`, `ManualLeadContract`
- **Purpose:** Each defines expected status codes, required keys, types, and valid enum values for its endpoint.
- **Still needed:** Yes.
- **Flag:** 🟢 CLEAN — though many classes are referenced only by TEST_DOCS.md, not directly by tests. `test_response_contracts.py` duplicates the key sets inline.

**Functions:**

#### `error_detail_fields_ok(body) -> bool`, `validation_error_detail_ok(body) -> bool`
- **Purpose:** Predicate-style contract checks.
- **Flag:** 🟡 SUSPECT — only used by TEST_DOCS.md examples, not by actual test code.

### `fakes.py`

**Purpose:** In-memory fakes for Kuzu graph DB, SQLite, and LanceDB vector store. The key entry point is `_install_storage_fakes()` which patches `sys.modules` so that imports of `kuzu`, `sqlite3`, and `lancedb` resolve to fakes. Must be called before importing any backend module that uses these stores.

**Classes:**

#### `_FakeResult` — stub with `has_next()` / `get_next()` returning sentinels.

#### `_FakeConnection` — Kuzu connection stub; `execute()` returns `_FakeResult`.

#### `_FakeSqlConnection` — SQLite connection stub; `execute()`, `executescript()`, `fetchone()`, `fetchall()`, `commit()`, `close()` all no-op.

#### `_FakeVectorStore` — LanceDB table stub; `list_tables()`, `create_table()`, `open_table()`, `add()` all no-op.

#### `_FakeSemanticSearch` / `_FakeSemanticTable` / `_FakeSemanticStore` — Minimal semantic search chain with filtering and limiting.

**Functions:**

#### `_install_storage_fakes(*, use_real_sqlite: bool = False)`
- **Purpose:** Patch storage modules into sys.modules.
- **Called by:** All test files that import backend modules.
- **Flag:** 🟢 CLEAN — well-designed. The `use_real_sqlite` parameter is critical for tests that need real SQLite semantics.

**Exports:** `_install_storage_fakes`, `_FakeSemanticStore`, `_FakeConnection`, `_FakeSqlConnection`, `_FakeVectorStore`

### `test_api.py`

**Purpose:** Tests FastAPI route behavior — auth gate, CRUD, validation, ingest endpoints. Uses real SQLite via `use_real_sqlite=True` with a temp directory. Seeds test data via direct SQLite queries.

**Imports:** `json`, `os`, `sys`, `tempfile`, `types`, `unittest`, `Path`, `mock`, `pytest`, fakes, `TestClient`, `main`, `app`, conftest helpers.

**Key patterns:**
- Module-level setup: creates temp dir, sets `JHM_APP_DATA_DIR`, installs fakes with real SQLite, overrides `_API_TOKEN`
- Helper functions: `get()`, `post()`, `put()`, `delete()` with auto-auth
- Seed helpers: `_seed_lead()`, `_seed_setting()` insert directly into DB

**Classes:**

#### `TestAuthGate` (7 tests)
- health is 200 without token, protected routes 401 without/wrong token, websocket token handling
- Flag: 🟢

#### `TestHealthEndpoint` (2 tests)
- Response structure (status, uptime, timestamp, log_level, dependencies + sub-keys)
- Flag: 🟢

#### `TestLeadsEndpoints` (8 tests)
- GET list, seniority filter, 404, PUT invalid status, round-trip delete, manual lead missing fields/too long
- Flag: 🟢

#### `TestExportEndpoint` (3 tests)
- CSV contract: content-type, headers, structure
- 🟢

#### `TestSettingsEndpoints` (7 tests)
- Template CRUD, settings round-trip, too-long validation, provider validation, sensitive key deprecation warning
- 🟢

#### `TestFollowupsEndpoint` (1 test)
- Due followups returns list
- 🟢

#### `TestFormReaderEndpoints` (4 tests)
- Form read 404, no-url case, identity endpoint, selectors refresh
- 🟢

#### `TestPipelineRunEndpoint` (2 tests)
- Pipeline run 404, valid start
- 🟢

#### `TestGenerateEndpoint` (1 test)
- Generate with mocked generator
- 🟢

#### `TestIngestionEndpoints` (9 tests)
- LinkedIn (non-zip, invalid zip, valid zip), GitHub (unknown user, missing username), Profile (empty, valid, too-long name), profile template, portfolio (invalid URL, valid URL)
- 🟢

**Flag:** 🟢 CLEAN — strong contract assertions (shape + type + content). Total 44 tests.

### `test_graph.py`

**Purpose:** Happy-path tests for the evaluation graph. Verifies compilation, node presence, invoke returns state, score range, error field type, and generate-skip when score below threshold.

**Imports:** `os`, `sys`, `types`, `unittest`, `Path`, `mock`, `pytest`, fakes, `build_eval_graph`, `PipelineState`

**Classes:**

#### `TestGraphStructure` (2 tests)
- Compiles, has evaluate node
- 🟢

#### `TestGraphInvoke` (5 tests)
- Returns dict, has required keys, score in range, error is None/str, generate skipped when score < 60
- 🟢

**Flag:** 🟢 CLEAN — adequate coverage for happy path.

### `test_graph_failures.py`

**Purpose:** The largest test file (1290 lines, ~27 tests). Characterizes every failure mode of the fault-tolerant eval graph pipeline. Organized into guarantee-classes, each with a docstring stating the operational contract. Tests cover: persist crash, evaluate crash, generate crash, timeout, threshold gate, missing fields, topology, and invoke-never-raises.

**Imports:** `os`, `sys`, `types`, `unittest`, `Path`, `mock`, `pytest`, fakes, `build_eval_graph`, `PipelineState`

**Classes (16 guarantee-classes):**

| Class | Tests | Guarantee |
|-------|-------|-----------|
| `TestPersistCrashDoesNotCrashGraph` | 3 | invoke returns dict on DB crash |
| `TestPersistCrashSurfacesStructuredError` | 3 | error + error_stage in result |
| `TestPersistCrashPreservesUpstreamState` | 2 | score/paths survive DB crash |
| `TestPersistGatesAssetSave` | 3 | empty paths suppress save_asset_package |
| `TestPersistReturnsEmptyOnSuccess` | 1 | empty dict on success |
| `TestEvaluateCrashProducesStructuredFailure` | 4 | error matches, stage=evaluate, score=0, reason="eval failed" |
| `TestEvaluateCrashBlocksGenerate` | 1 | empty asset paths after evaluate crash |
| `TestEvaluateCrashPersistsDegradedScore` | 2 | update_lead_score called with 0 |
| `TestEvaluateCatchesAllExceptions` | 1 | all Exception types set score=0 |
| `TestEvaluateNodeTimeout` / `TestGenerateNodeTimeout` | 3+3 | timeout sets stage, timed out message, zero score / preserve score |
| `TestGenerateCrashReturnsEmptyPaths` | 2 | asset/cover empty after generate crash |
| `TestGenerateCrashSurfacesStructuredError` | 2 | error + stage=generate |
| `TestGenerateCrashPreservesEvaluateOutput` | 2 | score/reason survive |
| `TestGenerateCrashPersistsScore` | 2 | update_lead_score still called |
| `TestGenerateCatchesAllExceptions` | 1 | all Exception types set error |
| `TestGenerateSkipPreservesUpstreamError` | 1 | skip does NOT clear error fields |
| `TestLowScoreIsNotAnError` | 1 | no error fields for legit low score |
| `TestThresholdGate` | 6 | strict-less-than threshold, 60 default, 0 runs all, 100 skips all, cfg at runtime |
| `TestMissingLeadDescription` | 1 | no crash when description missing |
| `TestEmptyProfile` | 1 | profile={} doesn't crash |
| `TestMissingCfgKey` | 1 | cfg absent defaults threshold to 60 |
| `TestMissingJobId` | 1 | "?" fallback, no KeyError |
| `TestScoreStringCoercion` | 2 | string "75" → int 75 |
| `TestReasonPassthrough` | 1 | graph doesn't truncate reason |
| `TestGraphTopology` | 1 | exactly 3 user nodes + __start__ |
| `TestInvokeNeverRaises` | 3 | no Exception from invoke on any failure |
| `TestInvokeReturnsActionableError` | 1 | error + error_stage + score + asset_path |

**Flag:** 🟢 CLEAN — excellent characterization. One potential concern: the mock set-up boilerplate is high (4+ mocks per test). Consider extracting a setUp helper.

### `test_mcp_server.py`

**Purpose:** Tests the MCP JSON-RPC handler function directly (no HTTP stack). Covers initialize, tools/list, tools/call for all three tools, protocol error handling (unknown method, unknown tool), tool-level errors (missing args, wrong types), notification handling.

**Imports:** `json`, `unittest`, conftest MCP helpers, `_handle` from `mcp_server`

**Classes:**

#### `MCPServerTests` (13 tests)
- Initialize, tools/list, tool calls, protocol errors, tool errors, notifications
- 🟢

**Flag:** 🟢 CLEAN — compact, well-structured, uses conftest helpers.

### `test_paths.py`

**Purpose:** Tests cross-platform path resolution (`data_base()`) and browser binary detection (`chromium_executable()`). Uses `mock.patch.dict(os.environ)` to simulate various OS environments.

**Imports:** `os`, `sys`, `unittest`, `Path`, `mock`, fakes, `data_base` from `db.client`

**Classes:**

#### `DataBaseTests` (5 tests)
- JHM_APP_DATA_DIR priority, XDG on Linux, LOCALAPPDATA on Windows, fallback to home, XDG default
- 🟢

#### `EnsureDirTests` (1 test)
- Fallback to _store suffix on PermissionError
- 🟢

#### `ChromiumExecutableTests` (6 tests)
- BROWSER env var, PLAYWRIGHT_CHROMIUM_EXECUTABLE, Linux candidates, None when not found
- 🟢

**Flag:** 🟢 CLEAN.

### `test_regressions.py`

**Purpose:** The second-largest file (1205 lines, ~50 tests). A mixed bag of domain logic regression tests covering the scoring engine, quality gate, seniority classification, HN parsing, feedback ranker, job target validation/splitting, query generation, X/twitter scout, browser runtime, and various Pydantic model validations. Also contains the `@pytest.mark.external` tests (generator PDF render, local LLM fallback) that write to disk.

**Imports:** extensive — `json`, `os`, `Path`, `sys`, `tempfile`, `types`, `unittest`, `mock`, `pytest`

**Key functions/classes:**

#### `RegressionTests` (35+ tests)
- Unstructured class covering: LLM provider catalog, help agent, model guardrails, evaluator determinism, scoring caps, semantic search, feedback ranker, job targets, HN parsing, actuator gate, etc.
- **Flag:** 🟠 STALE — this class is too large and mixes too many concerns. Should be split into domain-specific test classes.

#### `TestScoringEngineCaps` (6 tests)
- Senior role + zero experience cap, junior role strong match, experienced candidate, wrong domain, valid range, semantic unavailable fallback
- 🟢

#### `TestLeadQualityGate` (5 tests)
- Valid junior accepted, senior-only rejected, stale rejected, thin penalized, red flags rejected
- 🟢

#### `TestBrowserRuntimePackaging` (2 tests)
- Platform-specific asset names, Chromium payload detection
- 🟢

**Flag:** 🟠 STALE — `RegressionTests` class is a grab-bag of unrelated tests (435 lines, 35+ tests). Should be split into separate files or classes by domain area (targets, HN, feedback, evaluator, etc.).

### `test_secrets.py`

**Purpose:** Tests `resolve_secret()` priority chain: env var → SQLite → None. Verifies warning emission and deduplication via `@lru_cache`.

**Imports:** `os`, `logging`, `mock.patch`, `pytest`, `resolve_secret`, `_warn_sqlite_fallback`

**Style:** pytest function-style (no classes). 7 tests.

**Flag:** 🟢 CLEAN — focused, thorough.

### `test_websocket.py`

**Purpose:** Tests the `_CM` WebSocket connection manager class for async-safety under concurrency. Contains increasingly sophisticated fake WebSocket objects for deterministic concurrency testing.

**Imports:** `asyncio`, `json`, `unittest`, `AsyncMock`

**Mock classes:**

#### `_MockWebSocket`, `_BrokenWebSocket`, `_ControlledWebSocket`, `_DisconnectingWebSocket`
- **Flag:** 🟢 — well-designed, progressively complex fakes for different scenarios.

**Test classes:**

#### `TestCMAddRemoveBroadcast` (7 tests)
- Basic single-coroutine: add+broadcast, remove, empty registry, dead removal, identity comparison
- 🟢

#### `TestCMConcurrency` (8 tests)
- Concurrent add/remove/broadcast: gather duplicates, race conditions, dead removal, order preservation
- 🟢

#### `TestCMControlledConcurrency` (9 tests)
- Event-controlled deterministic concurrency: add during blocked broadcast, remove during send, snapshot independence, high contention stress, three-way race
- 🟢

**Flag:** 🟢 CLEAN — excellent concurrency test design with deterministic event control.

### `test_sqlite.py`

**Purpose:** Low-level SQLite pragma verification. Restores real `sqlite3` module (other test files may have faked it). Tests WAL, foreign_keys, busy_timeout behavior on temp file databases.

**Imports:** `os`, `sys`, `tempfile`, `unittest`, `sqlite3`

**Classes:**

#### `TestSqlitePragmasOnFile` (8 tests)
- Journal mode defaults, WAL persistence across connections, FK off/on/violation/allowed, busy timeout, all three together
- 🟢

#### `TestGetSqlConnection` (1 test)
- Importable and callable
- 🟢

**Flag:** 🟢 CLEAN.

### `test_sqlite_reliability.py`

**Purpose:** Tests `get_sql_connection()` pragma application, WAL snapshot isolation for readers, writer contention with busy_timeout, FK enforcement under concurrency, transaction rollback/atomicity, and an AST-level audit to catch direct `_sq.connect()` calls outside `get_sql_connection()`.

**Imports:** `os`, `sys`, `tempfile`, `threading`, `time`, `unittest`, `sqlite3`, `ast`, `inspect`

**Classes:**

#### `TestGetSqlConnectionPragmas` (5 tests)
- Verifies each pragma and all together on every call
- 🟢

#### `TestSqliteContentionBase` (base class)
- Sets up temp file DB with standard pragmas
- 🟢

#### `TestWALSnapshotIsolation` (5 tests)
- Uncommitted writes invisible, committed visible, snapshot from first read, concurrent readers, reader not blocked by writer
- 🟢

#### `TestWriterContention` (6 tests)
- busy_timeout=0 raises immediate, default 5000, wait-then-succeed, short timeout expires, ROLLBACK atomicity, auto-rollback on disconnect
- 🟢

#### `TestConnectionConsistency` (1 test)
- AST audit: no `_sq.connect()` calls outside `get_sql_connection()`
- 🟢 — this is a clever architectural enforcement pattern.

#### `TestForeignKeyEnforcement` (2 tests)
- FK violation rolled back, concurrent FK write with busy_timeout succeeds
- 🟢

**Flag:** 🟢 CLEAN — thorough, well-structured. The AST audit test is notable.

### `test_observability.py`

**Purpose:** Tests that every `except:pass` replacement logs with correct severity (WARNING/DEBUG/INFO), entity identifiers in messages, and degraded-vs-successful discrimination.

**Imports:** `io`, `json`, `logging`, `os`, `sys`, `time`, `tempfile`, `datetime`, `Path`, `mock`, `pytest`

**Pattern:** Uses direct `StringIO` handler capture (not caplog) because `get_logger()` sets `propagate=False`.

**Custom assertion helpers:** `assert_log_contains`, `assert_warning_emitted`, `assert_debug_emitted`, `assert_info_emitted`, `assert_no_logs_at_level` — all file-local.

**Flag:** 🟢 CLEAN — well-engineered. The `_attach_handler()` pattern is correct and necessary.

### `test_log_context.py`

**Purpose:** Tests the correlation context system: `CorrelationContext` creation, set/get/reset/enrich, task isolation, `CorrelationFilter`, `ContextFormatter`, file handler configuration, and middleware integration.

**Imports:** `asyncio`, `io`, `logging`, `os`, `tempfile`, `uuid`, `Path`, `pytest`, log_context and logger modules.

**Classes:**

#### `TestContextBasics` (8 tests)
- UUID4 format, get returns None when unset, set/get, reset, enrich creates new, enrich raises without context, fields default to None
- 🟢

#### `TestContextIsolation` (2 tests)
- Task isolation with asyncio.gather
- 🟢

#### `TestCorrelationFilter` (3 tests)
- Injects correlation_id, uses "-" when no context, appends contextual fields
- 🟢

#### `TestContextFormatter` (2 tests)
- Format with and without context
- 🟢

#### `TestFileHandler` (2 tests)
- Creates RotatingFileHandler when configured, skips when not configured
- 🟢

#### `TestMiddlewareIntegration` (2 tests)
- Sets X-Correlation-ID header, accepts client-provided ID
- 🟢

**Flag:** 🟢 CLEAN.

### `test_startup.py`

**Purpose:** Two smoke tests: (1) runs `main.py` as subprocess and verifies JHM_TOKEN= (64 hex chars) and PORT: (1-65535) appear in stdout, (2) verifies `_bind_port()` holds the port (TOCTOU race prevention).

**Imports:** `socket`, `subprocess`, `sys`, `unittest`, `Path`

**Flag:** 🟢 CLEAN — minimal, focused.

### `test_scan_manager.py`

**Purpose:** Tests `ScanManager` lifecycle state machine: start returns status, double-start raises 409, stop when idle returns idle, is_scanning false initially, ghost lock blocks scan and reevaluate.

**Imports:** `IsolatedAsyncioTestCase` from `unittest`, `ScanManager`

**7 tests.** 43 lines.

**Flag:** 🟢 CLEAN — concise.

### `test_ghost_service.py`

**Purpose:** Tests GhostService phase input/output contracts: preflight returns None when ghost mode disabled, returns (cfg, profile, boards) tuple when active.

**Imports:** `IsolatedAsyncioTestCase`, `mock`, `GhostService`, `ScanManager`

**2 tests.** 30 lines — the smallest test file.

**Flag:** 🟢 CLEAN — minimal but appropriate for the scope.

### `test_response_contracts.py`

**Purpose:** Verifies every route's `response_model=` is a superset of actual response payload (catches silent field dropping). Also verifies job target CRUD GET/PUT/DELETE contract compliance.

**Imports:** `os`, `tempfile`, fakes, `TestClient`, `main`, `app`

**Style:** pytest module-level functions (no classes). 8 tests.

**Flag:** 🟢 CLEAN — important cross-check that many teams skip. Re-serialization approach is sound.

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P2 | 🟠 STALE | `RegressionTests` monolithic class | `test_regressions.py:62` | 435 lines, 35+ unrelated tests in one class — should be split by domain |
| P2 | 🟡 SUSPECT | `api_contracts.py` predicate functions | `api_contracts.py:18-39` | Defined but only referenced by TEST_DOCS.md, not actual tests |
| P2 | 🟡 SUSPECT | `_has_x_token` import from ghost service test | `test_ghost_service.py:22` | Mocked but never actually called in `_phase_preflight` — verify if code path still exists |
| P3 | 🟢 CLEAN | Conftest assertion helpers | `conftest.py` | Well-factored, single-responsibility, used across test files |
| P3 | 🟢 CLEAN | `fakes.py` design | `fakes.py` | Clean abstraction with `use_real_sqlite` toggle |
| P3 | 🟢 CLEAN | `test_websocket.py` controlled concurrency | `test_websocket.py:257-515` | Best-practice deterministic concurrency testing |
| P3 | 🟢 CLEAN | `test_graph_failures.py` guarantee-classes | `test_graph_failures.py` | Excellent structured failure characterization |
| P3 | 🟢 CLEAN | `test_sqlite_reliability.py` AST audit | `test_sqlite_reliability.py:435` | Clever architectural enforcement |
| P3 | 🟢 CLEAN | `test_observability.py` logger capture | `test_observability.py:32-48` | Correct pattern for propagate=False loggers |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- None — this is a leaf unit providing test coverage for all other units.

**Outbound (this unit depends on others):**

| Unit | Used by | Nature |
|------|---------|--------|
| `backend/config/` | `test_secrets.py`, `test_log_context.py` | Import config schemas |
| `backend/db/client.py` | `test_api.py`, `test_sqlite.py`, `test_sqlite_reliability.py`, `test_regressions.py`, `test_observability.py`, `test_paths.py` | DB access, path resolution |
| `backend/graph/` | `test_graph.py`, `test_graph_failures.py` | LangGraph pipeline |
| `backend/mcp_server.py` | `test_mcp_server.py` | Direct function testing |
| `backend/main.py` | `test_api.py`, `test_startup.py`, `test_response_contracts.py`, `test_regressions.py` | FastAPI app |
| `backend/agents/` | `test_regressions.py`, `test_observability.py` | Evaluator, generator, ingestor, semantic, scout, etc. |
| `backend/services/` | `test_scan_manager.py`, `test_ghost_service.py`, `test_regressions.py` | Scanner, ghost, job targets |
| `backend/core/ws_manager.py` | `test_websocket.py` | _CM class |
| `backend/log_context.py` | `test_log_context.py` | Correlation context |
| `backend/logger.py` | `test_log_context.py` | Logger, CorrelationFilter, ContextFormatter |
| `backend/llm.py` | `test_regressions.py` | Provider catalog |
| `backend/config/secrets.py` | `test_secrets.py` | resolve_secret |
| `backend/routes/ws.py` | `test_api.py` | WebSocket token check |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| pytest | Test framework | indirect via `pyproject.toml` | 🟢 |
| fastapi | TestClient | indirect | 🟢 |
| pypdf | External PDF page test (1 test) | indirect | 🟢 |

---

## 6. First principles assessment

| File | Need to exist? | Does what it claims? | Right place? | Breaks if deleted? |
|------|---------------|---------------------|-------------|-------------------|
| `TEST_DOCS.md` | Yes | Yes — comprehensive documentation | Yes | No code breaks, but team loses reference |
| `conftest.py` | Yes | Yes | Yes | Every test file breaks — assertion helpers gone |
| `api_contracts.py` | Partially — tests mostly inline key sets | Yes | Yes | Minor — tests would inline contracts |
| `fakes.py` | Yes | Yes | Yes | Every integration test breaks — storage fakes gone |
| `test_api.py` | Yes | Yes | Yes | No API route coverage |
| `test_graph.py` | Yes | Yes | Yes | No graph happy-path coverage |
| `test_graph_failures.py` | Yes | Yes | Yes | No graph fault-tolerance coverage |
| `test_mcp_server.py` | Yes | Yes | Yes | No MCP protocol coverage |
| `test_paths.py` | Yes | Yes | Yes | No path resolution tests |
| `test_regressions.py` | Yes — but should be split | Yes | Partially — too many concerns in one file | Many domain regression tests lost |
| `test_secrets.py` | Yes | Yes | Yes | No secret resolution tests |
| `test_websocket.py` | Yes | Yes | Yes | No WS concurrency tests |
| `test_sqlite.py` | Yes | Yes | Yes | No SQLite pragma tests |
| `test_sqlite_reliability.py` | Yes | Yes | Yes | No contention/AST audit tests |
| `test_observability.py` | Yes | Yes | Yes | No observability regression tests |
| `test_log_context.py` | Yes | Yes | Yes | No correlation context tests |
| `test_startup.py` | Yes | Yes | Yes | Minor — startup smoke tests lost |
| `test_scan_manager.py` | Yes | Yes | Yes | No ScanManager lifecycle tests |
| `test_ghost_service.py` | Yes | Yes | Yes | No GhostService phase tests |
| `test_response_contracts.py` | Yes | Yes | Yes | Silent field dropping goes undetected |
