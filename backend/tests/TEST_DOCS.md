# Test Suite Documentation — JustHireMe Backend

## Overview

This directory contains the deterministic test suite for the JustHireMe backend.
All tests in this directory are designed to run in CI, produce consistent results,
and avoid external service dependencies.

**Test count:** 150  
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

| Status | Adequate |
|--------|----------|
| **What it tests** | FastAPI route behaviour, auth gate, CRUD, validation |
| **Key behaviours** | 401 on missing/wrong token, 404 on missing lead, 422 on invalid input, WS heartbeat |
| **Dependencies** | Uses `_install_storage_fakes()` to avoid real DB connections |
| **Note** | Uses `TestClient` with fake storage backends |

### `test_mcp_server.py` — MCP Server

| Status | Adequate |
|--------|----------|
| **What it tests** | JSON-RPC MCP protocol: initialize, tools/list, tools/call |
| **Key behaviours** | Tool discovery, parameter validation, error handling |
| **Dependencies** | None (tests the `_handle` function directly with mock requests) |

### `test_paths.py` — Path & Runtime Resolution

| Status | Strong |
|--------|--------|
| **What it tests** | Cross-platform app data directory resolution, browser binary detection |
| **Key behaviours** | JHM_APP_DATA_DIR → XDG → LOCALAPPDATA → fallback priority chain, Chromium executable discovery on Linux/Windows/macOS |
| **Dependencies** | None (patches env vars, mocks filesystem) |

### `test_graph.py` — LangGraph Evaluation Graph

| Status | Adequate |
|--------|----------|
| **What it tests** | Eval graph structure: compiles, has expected nodes, returns valid state |
| **Key behaviours** | Score range validation, threshold-based generation skipping, error field types |
| **Dependencies** | Mocks evaluator and generator agents |

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
  │   Integration     │  test_api.py, test_graph.py
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

## Pytest Markers

| Marker | Meaning | Default | Tests |
|--------|---------|---------|-------|
| `integration` | Crosses component boundaries (routing, graph orchestration) | Included | `test_api.py`, `test_graph.py` |
| `external` | Writes to filesystem or has side effects | Excluded | `test_generator_render_keeps_pdf_to_one_page`, `test_generator_uses_local_fallback_when_llm_is_unavailable` |
| `requires_browser` | Requires Playwright/Chromium automation | Excluded | (none currently) |

**Integration tests** use fakes for external storage but exercise the real FastAPI routing and LangGraph orchestration layers. They are CI-safe.

**External tests** write PDF files to disk. They are excluded from the default run and must be opted into with `-m "external"`.

---

## Fakes & Test Infrastructure

### `conftest.py`
- Adds `backend/` to `sys.path`
- Ignores `tmp*` files from test collection

### `fakes.py`
- `_install_storage_fakes()` — replaces Kuzu, SQLite, LanceDB with in-memory fakes
- Must be called **before** importing any backend module that uses these stores
- Provides `_FakeConnection`, `_FakeSqlConnection`, `_FakeVectorStore`, `_FakeSemanticStore`

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
