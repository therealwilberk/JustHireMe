# Test Suite Documentation — JustHireMe Backend

## Overview

This directory contains the deterministic test suite for the JustHireMe backend.
All tests in this directory are designed to run in CI, produce consistent results,
and avoid external service dependencies.

**Test count:** 204  
**Framework:** pytest (via `unittest.TestCase`)  
**Runner:** `uv run python -m pytest tests/`

---

## Test Files

### `test_secrets.py` — Config/Secret Resolution

| Status | Strong |
|--------|--------|
| **What it tests** | Secret resolution priority chain: env var → SQLite → None |
| **Key behaviours** | Warning deduplication on SQLite fallback, env var precedence |
| **Dependencies** | None (patches `os.environ`, mocks `get_setting`) |

### `test_api.py` — API Endpoints

| Status | Strong |
|--------|--------|
| **What it tests** | FastAPI route behaviour, auth gate, CRUD, validation |
| **Key behaviours** | 401 on missing/wrong token, 404 on missing lead with error detail, 422 Pydantic validation shape (loc/msg/type), CSV contract (headers+content-type), health response structure, ingest response schemas, type guarantees on all fields |
| **Dependencies** | Uses `_install_storage_fakes()` to avoid real DB connections |
| **Note** | Uses `TestClient` with fake storage backends. All error responses assert payload structure (not just status code). All success responses assert field presence and types. Uses shared assertion helpers from `conftest.py`. |

### `test_mcp_server.py` — MCP Server

| Status | Strong |
|--------|--------|
| **What it tests** | JSON-RPC MCP protocol: initialize, tools/list, tools/call |
| **Key behaviours** | Tool discovery, parameter validation, protocol error handling (unknown method, unknown tool), tool-level error handling (missing args, wrong types), structured response shape |
| **Dependencies** | None (tests the `_handle` function directly with mock requests) |
| **Note** | Every test verifies JSON-RPC contract: `jsonrpc: "2.0"`, stable ids, error/result mutual exclusivity. Protocol errors assert error.code and message structure; tool errors assert isError, content[0].type, and semantic error messages. |

### `test_paths.py` — Path & Runtime Resolution

| Status | Strong |
|--------|--------|
| **What it tests** | Cross-platform app data directory resolution, browser binary detection |
| **Key behaviours** | JHM_APP_DATA_DIR → XDG → LOCALAPPDATA → fallback priority chain, Chromium executable discovery on Linux/Windows/macOS |
| **Dependencies** | None (patches env vars, mocks filesystem) |

### `test_graph.py` — LangGraph Evaluation Graph (happy path)

| Status | Adequate |
|--------|----------|
| **What it tests** | Eval graph structure: compiles, has expected nodes, returns valid state |
| **Key behaviours** | Score range validation, threshold-based generation skipping, error field types |
| **Dependencies** | Mocks evaluator and generator agents |

### `test_graph_failures.py` — Graph Failure-Path Characterization

| Status | Strong |
|--------|--------|
| **What it tests** | Orchestration failure modes: persist crash, evaluate exception, generate exception, threshold boundaries, state consistency, malformed input, silent API failure, node timeout |
| **Key behaviours** | Linear 3-node fault-tolerant pipeline, error+error_stage structured failure metadata, error is append-only (never cleared by downstream nodes), persist catches DB exceptions instead of crashing, threshold defaults to 60, missing job_id handled defensively, deterministic node-level timeout (default 600s) |
| **Dependencies** | Mocks evaluator, generator, and DB calls |
| **Note** | Orchestration hardening — fault-tolerant semantics with structured error metadata. Previously started as characterization tests; behavior was then corrected (persist crash → structured error, error now append-only, missing job_id handled defensively). Do not revert these semantics. |

### `test_regressions.py` — Domain Logic & Regression Prevention

| Status | Strong |
|--------|--------|
| **What it tests** | Scoring engine caps, quality gate, seniority filters, HN parsing, feedback ranker, job targets, query generation, X/twitter scout, browser runtime |
| **Key behaviours** | Zero-experience senior cap, wrong-field penalty, stale lead rejection, HN job post filtering, feedback learning boost/penalty, India/global job target fallback |
| **Sub-classes** | `TestScoringEngineCaps`, `TestLeadQualityGate`, `TestBrowserRuntimePackaging` |
| **Dependencies** | Mocks external agents, uses `_install_storage_fakes()` |

---

## Test Pyramid

```
  ┌──────────────────┐
  │   E2E (manual)    │  scripts/run_ingestion_pipeline.py
  │                   │  e2e/manval/run_live_fire.py
  ├──────────────────┤
  │   Integration     │  test_api.py, test_graph.py,
  │                   │  test_graph_failures.py
  │                   │  test_mcp_server.py (boundary)
  ├──────────────────┤
  │   Domain/Unit     │  test_regressions.py, test_secrets.py
  │                   │  test_paths.py
  └──────────────────┘
```

---

## Test Commands

```bash
# Run default suite (excludes external tests)
uv run python -m pytest tests/

# Run all tests including external
uv run python -m pytest tests/ -m ""

# Run only integration tests
uv run python -m pytest tests/ -m "integration"

# Run only external tests (filesystem side effects)
uv run python -m pytest tests/ -m "external"

# Run with verbose output
uv run python -m pytest tests/ -v

# Run a specific test file
uv run python -m pytest tests/test_regressions.py -v

# Run a specific test class
uv run python -m pytest tests/test_regressions.py::TestLeadQualityGate -v

# Run a specific test
uv run python -m pytest tests/test_regressions.py::TestLeadQualityGate::test_valid_junior_job_is_accepted -v

# Run with coverage
uv run python -m pytest tests/ --cov=.
```

## API Contract Philosophy

### Why Status-Only Tests Are Insufficient

An API is a contract. Clients depend on:
- **Payload structure** — which fields exist, their nesting, their types
- **Error schema** — consistent shape for 4xx/5xx responses
- **Field types** — string vs int vs list vs null
- **Validation messaging** — Pydantic error structure (`loc`, `msg`, `type`)
- **Enum guarantees** — exact allowed values for status, feedback, etc.
- **Semantic identifiers** — stable keys like `status`, `error`, `stats`

Status-only tests (`assert response.status_code == 400`) allow silent schema breakage: a field can be renamed, removed, or change type without any test noticing.

### Stable API Guarantees vs. Flexible Fields

| Classification | Rule | Examples |
|---------------|------|----------|
| **Stable contract** | Must be asserted in tests | Field presence, types, nesting, enum values, error `detail` type, 422 `detail[].loc[]` + `detail[].type`, pagination keys, response `status` keys |
| **Flexible presentation** | NOT asserted — avoid brittleness | Human-readable prose in `detail` messages, wording in error descriptions, non-semantic description text, `uptime_seconds` exact value, `latency_ms` exact value |
| **Framework-generated** | Assert shape, not content | Pydantic validation errors: assert `loc` + `type`, NOT exact `msg` wording |
| **Business/domain errors** | Assert error code pattern + field presence | `{"detail": str}` for 400/404 errors; assert `detail` exists and is a string, NOT exact wording |
| **Transport-layer** | Status code + content-type | Status line, headers (Content-Type, Content-Disposition) |

### Contract Assertion Principles

1. **Assert shape, not exact wording** — Prefer `assert "username" in body["detail"].lower()` over `assert body["detail"] == "Username is required"`.
2. **Assert types** — `assert isinstance(body["stats"], dict)`, not just `assert "stats" in body`.
3. **Assert structural invariants** — 422 errors MUST have `detail` as a `list` with items containing `loc`, `msg`, `type`.
4. **Error responses MUST have a `detail` key** of type `str` (FastAPI convention). Assert this.
5. **Success responses MUST use the expected top-level keys** (e.g., `{"ok": true}`, `{"status": "started"}`).

### What Constitutes a Breaking API Change

- Removing or renaming a stable field
- Changing the type of a stable field (e.g., `str` → `int`)
- Changing enum allowed values without notice
- Restructuring error response shape
- Changing response nesting level
- Adding `null` to a previously non-nullable field
- Changing timestamp format

### How Strict Assertions Should Be Written

Use `assert_error_response`, `assert_validation_error`, and `assert_success_response` helpers from test infrastructure. These enforce:

```python
def assert_error_response(resp, expected_status, detail_type=str):
    assert resp.status_code == expected_status
    body = resp.json()
    assert "detail" in body
    assert isinstance(body["detail"], detail_type)

def assert_validation_error(resp):
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    for err in body["detail"]:
        assert "loc" in err and isinstance(err["loc"], list)
        assert "msg" in err and isinstance(err["msg"], str)
        assert "type" in err and isinstance(err["type"], str)

def assert_success_response(resp, expected_status=200, required_keys=None):
    assert resp.status_code == expected_status
    if required_keys:
        body = resp.json()
        for key in required_keys:
            assert key in body, f"Missing expected key: {key}"
```

### Per-Endpoint Contract Schemas

Defined in `api_contracts.py` as TypedDicts/dataclasses with per-field classification. Tests import these and validate response payloads against them, avoiding duplicate schema knowledge.

## Orchestration Semantics

The graph pipeline (`graph/__init__.py`) follows **fault-tolerant workflow semantics**:

| Property | Contract |
|----------|----------|
| Node failure behavior | Each node catches its own `Exception`, sets `error` + `error_stage`, and returns normally. Graph never crashes on node failure. |
| Error field | Append-only. Once set by a node, downstream nodes NEVER clear it. Only a later node's own error overwrites it. |
| `error_stage` | Identifies which node set the error: `"evaluate"`, `"generate"`, or `"persist"`. `None` means no error occurred. |
| Timeout behavior | Each node wraps its main callable in `_with_timeout` (daemon thread + `threading.Event`). Default: 600s. Override via `cfg.evaluate_timeout` / `cfg.generate_timeout`. A timed-out node raises `TimeoutError` → caught by `except Exception` → structured failure. Deterministic: same timeout always produces same error structure. |
| `persist_node` | Has try/except. DB write failures return structured error instead of crashing the graph. |
| State access | All nodes use defensive `.get()` with defaults. No bare subscript access (`state["key"]`). |
| `generate_node` skip path | Returns only `asset_path`/`cover_letter_path`. Does NOT touch `error` or `error_stage` — preserving upstream failure info. |
| API layer | `invoke()` never raises on node failure. The result dict contains `error`/`error_stage`. |

This is intentionally NOT strict transactional (no rollback, no abort on partial failure). Degraded execution is observable via `error`, `error_stage`, and `reason` fields.

## Pytest Markers

| Marker | Meaning | Default | Tests |
|--------|---------|---------|-------|
| `integration` | Crosses component boundaries (routing, graph orchestration) | Included | `test_api.py`, `test_graph.py`, `test_graph_failures.py` |
| `external` | Writes to filesystem or has side effects | Excluded | `test_generator_render_keeps_pdf_to_one_page`, `test_generator_uses_local_fallback_when_llm_is_unavailable` |
| `requires_browser` | Requires Playwright/Chromium automation | Excluded | (none currently) |

**Integration tests** use fakes for external storage but exercise the real FastAPI routing and LangGraph orchestration layers. They are CI-safe.

**External tests** write PDF files to disk. They are excluded from the default run and must be opted into with `-m "external"`.

---

## Fakes & Test Infrastructure

### `conftest.py`
- Adds `backend/` to `sys.path`
- Ignores `tmp*` files from test collection
- Provides API contract assertion helpers: `assert_error_response`, `assert_detail_error`, `assert_detail_exactly`, `assert_detail_contains`, `assert_validation_error`, `assert_success_response`, `assert_list_response`, `assert_csv_response`, `assert_ok_response`
- Provides MCP (JSON-RPC) contract assertion helpers: `assert_mcp_response_structure`, `assert_mcp_protocol_error`, `assert_mcp_tool_error`
- Helpers enforce payload structure (field presence, types, nesting, error shape) in addition to status codes
- MCP helpers verify: `jsonrpc: "2.0"`, stable error codes, error/result mutual exclusivity, `isError` flag, `content[0].type == "text"`

### `api_contracts.py`
- Typed contract definitions per endpoint (required keys, expected types, valid enum values)
- Single source of truth for API response shapes — tests import contracts, not duplicate knowledge
- Covers all endpoints tested in `test_api.py`

### `fakes.py`
- `_install_storage_fakes()` — replaces Kuzu, SQLite, LanceDB with in-memory fakes
- Must be called **before** importing any backend module that uses these stores
- Provides `_FakeConnection`, `_FakeSqlConnection`, `_FakeVectorStore`, `_FakeSemanticStore`

---

---

## Phase C Coverage (Reliability, Observability & Concurrency)

As of Phase C activation, these areas have **no or minimal** test coverage:

| Area | Tests | Needed |
|------|-------|--------|
| Logging infrastructure | 8 partial refs (health `log_level`, secret warning dedup, agent log format) | Config-level tests (`config/logging.py`), env var override, format consistency |
| WebSocket behavior | 2 auth-only (token connect, missing token) | Message contracts, concurrent mutation, `_CM` async-safety |
| SQLite WAL/pragmas | None | Pragma verification on connection, busy timeout behavior |
| Frontend error handling | None | SettingsModal/ProfileView save failure display |
| `except: pass` replacement | None | Error paths produce expected log output |

Tests for Phase C work belong in:
- `test_secrets.py` — existing, for logging-related secret resolution tests
- `test_logging.py` — new, for logging infrastructure and config
- `test_websocket.py` — new, for WebSocket `_CM` concurrency and message contracts
- `test_sqlite.py` — new, for WAL mode and connection pragmas

---

## Classification Guide

When adding a new test, classify it:

| Category | Characteristics | Goes In |
|----------|----------------|---------|
| **Deterministic test** | No external services, mocks/stubs for all I/O, fast, repeatable | `backend/tests/test_*.py` |
| **Integration test** | Tests boundary between components, may use real DB or test client | `backend/tests/test_*.py` (with fakes) |
| **Operational script** | Requires live APIs, browser, secrets, or network | `scripts/` or `e2e/manval/` |
| **Smoke test** | Quick manual validation of critical path | `scripts/` |

Operational scripts MUST:
- Live outside `backend/tests/`
- NOT use the `test_` prefix in their filename
- Have a docstring warning about non-determinism
- Be excluded from `pytest` collection
