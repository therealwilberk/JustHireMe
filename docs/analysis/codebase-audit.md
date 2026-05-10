# JustHireMe Codebase Audit

> Generated 2026-05-10 from `feature/codebase-audit` branch
> Based on thorough analysis of every source file

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Repository Structure](#2-repository-structure)
3. [SWOT Analysis](#3-swot-analysis)
4. [Module-by-Module Breakdown](#4-module-by-module-breakdown)
5. [Cross-Cutting Concerns](#5-cross-cutting-concerns)
6. [Error Handling Quality](#6-error-handling-quality)
7. [Hardcoded Values Registry](#7-hardcoded-values-registry)
8. [Security Assessment](#8-security-assessment)
9. [Dependency Analysis](#9-dependency-analysis)
10. [Test Coverage Analysis](#10-test-coverage-analysis)
11. [Configuration Audit](#11-configuration-audit)
12. [Recommendations](#12-recommendations)

---

## 1. Executive Summary

JustHireMe is a local-first AI-powered job intelligence desktop app (v0.1.25, alpha). It scrapes jobs from 15+ sources, ranks them against your profile using LLM + deterministic scoring, and generates tailored application materials. Built as a Tauri 2 desktop shell (Rust) wrapping a Python FastAPI backend with a React 19 frontend.

### By the Numbers

| Metric | Value |
|--------|-------|
| Total source files | ~70 |
| Backend Python lines | ~9,500 (across 25+ modules) |
| Frontend TSX/TS lines | ~4,500 (across 25+ files) |
| Rust sidecar lines | ~400 |
| Tests | ~100 (backend), 6 assertions (frontend) |
| LLM providers supported | 17 |
| Databases | 3 (SQLite, Kuzu graph, LanceDB vectors) |
| Critical issues found | 8 |
| Hardcoded values counted | 150+ |

---

## 2. Repository Structure

```
JustHireMe/
├── src/                          # React 19 + TypeScript frontend
│   ├── App.tsx                   # Main shell, view routing, WebSocket bridge
│   ├── main.tsx                  # React entry point
│   ├── index.css                 # Tailwind v4 + custom styles
│   ├── types.ts                  # Core data models (40+ fields on Lead)
│   ├── App.css                   # Legacy styles
│   ├── components/               # 11 reusable components
│   │   ├── Sidebar.tsx           # Navigation + snapshot stats
│   │   ├── ApprovalDrawer.tsx    # Lead detail panel (642 lines, 18 useState)
│   │   ├── JobCard.tsx           # Lead card components
│   │   ├── LeadFilterBar.tsx     # Pipeline filter controls
│   │   ├── OnboardingWizard.tsx  # 4-step first-run wizard
│   │   ├── SettingsModal.tsx     # Settings container
│   │   ├── HelpChat.tsx          # In-app AI support chat
│   │   ├── FormReader.tsx        # ATS form reader
│   │   ├── ErrorBoundary.tsx     # Per-view error boundary
│   │   ├── Icon.tsx              # SVG icon library (28 icons)
│   │   ├── UpdatePrompt.tsx      # Tauri updater prompt
│   │   └── Topbar.tsx            # View header
│   ├── hooks/                    # 5 custom hooks
│   │   ├── useWS.ts              # WebSocket + sidecar lifecycle
│   │   ├── useLeads.ts           # Lead polling + real-time updates
│   │   ├── useDueFollowups.ts    # Followups polling
│   │   ├── useGraphStats.ts      # Graph stats polling
│   │   └── useKeyboardShortcuts.ts
│   ├── views/                    # 8 workspace views
│   │   ├── DashboardView.tsx     # Home screen, stats, scan controls
│   │   ├── ApplyJobView.tsx      # One-shot job customization
│   │   ├── LeadInboxView.tsx     # Manual lead entry
│   │   ├── PipelineView.tsx      # Full lead table with filters
│   │   ├── GraphView.tsx         # Kuzu entity radar chart
│   │   ├── ActivityView.tsx      # Real-time log viewer
│   │   ├── ProfileView.tsx       # Identity graph viewer/editor
│   │   └── IngestionView.tsx     # Multi-tab profile ingestion (553 lines)
│   ├── settings/                 # 5 settings panels
│   │   ├── shared.tsx            # Cfg interface (74 keys), EMPTY defaults, UI components
│   │   ├── GlobalSettings.tsx    # LLM provider, API key, model selection
│   │   ├── StepSettings.tsx      # Per-pipeline-step provider overrides
│   │   ├── DiscoverySettings.tsx # Scraping config, sources, connectors
│   │   └── AutomationSettings.tsx# Ghost mode, auto-apply toggles
│   └── lib/
│       ├── leadUtils.ts          # Lead helpers (sort, filter, parse, format)
│       └── leadUtils.test.ts     # 6 test functions
├── backend/                      # Python 3.13 FastAPI sidecar
│   ├── main.py                   # FastAPI app + 45+ routes (2036 lines)
│   ├── llm.py                    # LLM provider abstraction (17 providers, 411 lines)
│   ├── logger.py                 # Logging setup (stderr, %H:%M:%S)
│   ├── mcp_server.py             # MCP stdio JSON-RPC server (191 lines)
│   ├── pyproject.toml            # Python deps (all >=, no upper bound)
│   ├── agents/                   # 21 agent modules
│   │   ├── scout.py              # Main scraper — ATS, RSS, APIs, Google dorks
│   │   ├── free_scout.py         # Free source scraper — ATS boards, GitHub, HN, Reddit
│   │   ├── x_scout.py            # X/Twitter API v2 job search
│   │   ├── quality_gate.py       # Deterministic lead filter (201 lines, clean)
│   │   ├── evaluator.py          # LLM-led job scorer with deterministic baseline
│   │   ├── scoring_engine.py     # Deterministic rubric (84-entry tech taxonomy)
│   │   ├── generator.py          # Resume/cover letter PDF generator (1216 lines)
│   │   ├── ingestor.py           # Profile parser → Kuzu + LanceDB (564 lines)
│   │   ├── semantic.py           # Vector similarity search (278 lines, fail-soft)
│   │   ├── feedback_ranker.py    # Feature-weight feedback learning (176 lines)
│   │   ├── lead_intel.py         # Regex text extraction (314 lines)
│   │   ├── contact_lookup.py     # Hunter.io + Proxycurl API (234 lines)
│   │   ├── help_agent.py         # In-app support chat (466 lines)
│   │   ├── actuator.py           # Playwright browser auto-apply (454 lines, experimental)
│   │   ├── browser_runtime.py    # Chromium discovery (158 lines)
│   │   ├── query_gen.py          # LLM-led search query generation (239 lines)
│   │   ├── github_ingestor.py    # GitHub profile import (189 lines)
│   │   ├── linkedin_parser.py    # LinkedIn ZIP parser (131 lines)
│   │   ├── portfolio_ingestor.py # Portfolio URL scraper (165 lines)
│   │   └── selectors.py          # OTA form selectors (84 lines, clean)
│   ├── db/
│   │   └── client.py             # SQLite + Kuzu + LanceDB (1628 lines)
│   ├── graph/
│   │   └── __init__.py           # LangGraph eval→generate→persist pipeline (111 lines)
│   ├── models/
│   │   └── schema.py             # Pydantic models (S, E, P, C — 34 lines)
│   └── tests/                    # Backend tests (~100 total)
│       ├── conftest.py, fakes.py
│       ├── test_api.py, test_graph.py, test_mcp_server.py
│       ├── test_paths.py, test_regressions.py
├── src-tauri/                    # Tauri 2 Rust shell
│   ├── src/lib.rs                # Sidecar lifecycle, commands, plugins (393 lines)
│   ├── src/main.rs               # Entry point (6 lines)
│   ├── tauri.conf.json           # App config, bundle, updater, CSP
│   ├── Cargo.toml                # Rust deps
│   └── capabilities/             # Tauri 2 permissions
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md, MCP.md, ...
│   ├── linux-release.md, windows-release.md
│   ├── specs/                    # Feature specs, roadmap, audit
│   └── linux-migration/          # 11-file migration guide
├── scripts/
│   ├── build-sidecar.sh          # Linux/macOS PyInstaller build
│   └── build-sidecar.ps1         # Windows PyInstaller build
├── resources/
│   └── JustHireMe.desktop        # Linux desktop entry (reference)
├── .github/
│   ├── workflows/ci.yml          # PR CI (audits, frontend, backend, rust)
│   ├── workflows/release.yml     # Release CI (multi-platform build + publish)
│   └── dependabot.yml            # Weekly update checks
├── package.json                  # Node deps + build scripts
├── vite.config.ts                # Vite config (port 1420)
├── .env.example                  # Optional API keys docs
└── index.html                    # HTML entry (Google Fonts CDN)
```

---

## 3. SWOT Analysis

### Strengths

| # | Strength | Evidence |
|---|----------|----------|
| S1 | **Spec-first discipline** | All features have written specs before code, with validation checklists and decisions logs |
| S2 | **Excellent test isolation** | Storage backends fully faked (Kuzu, LanceDB, SQLite replaced with sys.modules injection), no real DB/network in tests |
| S3 | **Deterministic scoring engine** | 84-entry tech taxonomy with alias normalization, seniority classification, and 6-criterion weighted rubric — no LLM dependency for core ranking |
| S4 | **Comprehensive documentation** | 15+ doc files including architecture, migration guides, release checklists, specs, and audit reports — all living documents |
| S5 | **17 LLM providers** | Unified abstraction with per-step override, env var fallback, and Ollama default (free, local) |
| S6 | **Fail-soft semantic layer** | `semantic.py` returns `None` on every failure — callers degrade gracefully without crashing |
| S7 | **Multi-platform release CI** | Windows/Linux/macOS builds with signing, updater artifacts, and SHA256 checksums |
| S8 | **Ghost mode concurrency lock** | `asyncio.Lock` prevents ghost ticks from racing with manual scans |
| S9 | **Sidecar startup timeout** | 15s tokio timeout in Rust prevents infinite hang on Python boot |

### Weaknesses

| # | Weakness | Impact |
|---|----------|--------|
| W1 | **Monolithic core files** | `main.py` (2036 lines), `db/client.py` (1628 lines) — all routes, business logic, auth, WebSocket in one file |
| W2 | **Pervasive silent error swallowing** | 50+ instances of `except Exception: pass` across backend. Failures vanish without trace |
| W3 | **Plaintext API key storage** | All 17 provider keys, tokens, cookies stored in SQLite `settings(key,val)` as plaintext. No encryption at rest |
| W4 | **No global state management** | 15 `useState` in `App.tsx`, leads drilled through 3+ component layers. Every lead change re-renders all views |
| W5 | **CI only runs regression tests** | `test_api.py` (30 tests), `test_graph.py`, `test_paths.py`, `test_mcp_server.py` — never executed in CI |
| W6 | **Frontend test coverage near zero** | 1 file with 6 tests. Entire React UI is untested |
| W7 | **No connection pooling** | SQLite → new open/close per operation (~70x). Kuzu → new Connection per operation (~30x). Massively wasteful |
| W8 | **Race condition in WebSocket manager** | `_CM` class modifies list without lock — concurrent broadcasts can corrupt the client list |
| W9 | **Overly-large component** | `ApprovalDrawer.tsx` (642 lines, 18 useState variables) — re-render storm waiting to happen |
| W10 | **`except Exception: pass` in DB migrations** | `ALTER TABLE` failures silently ignored — schema drift invisible |

### Opportunities

| # | Opportunity | Effort | Gain |
|---|-------------|--------|------|
| O1 | **Split `main.py` into routes/** package | Moderate | Maintainability, testability, parallel development |
| O2 | **Implement OS keychain for API keys** | Moderate | Closes the only real security hole |
| O3 | **Add pre-commit hooks (ruff + typecheck)** | Low | Catches errors before CI |
| O4 | **Switch to pytest fixtures** | Low | Cleaner tests, better parametrization |
| O5 | **Run full test suite in CI** | Trivial | Catches auth/path/pipeline regressions immediately |
| O6 | **Pin critical deps** (`langgraph`, `anthropic`, `openai`) | Low | Prevents surprise breakage on `uv sync` |
| O7 | **Add WAL mode to SQLite** | Trivial | Better concurrent read performance |
| O8 | **Self-host Google Fonts** | Low | True offline-first operation |

### Threats

| # | Threat | Likelihood | Impact |
|---|--------|------------|--------|
| T1 | **LLM provider API breakage** | Medium | 17 providers, all with loose pins — any could break on update |
| T2 | **Upstream divergence** | Medium | `linux-base` will drift from `main` over time. Merge complexity grows |
| T3 | **Sidecar stdout protocol fragility** | Low-Medium | Rust parses `PORT:` and `JHM_TOKEN=` from stdout. Python warning/deprecation early in boot breaks discovery |
| T4 | **Apify token in URL logs** | Low | Scout.py passes Apify token as `?token=` URL query param — leaks to any logging middleware |
| T5 | **Hunter.io key in URL logs** | Low | Same pattern in `contact_lookup.py` — API key in URL query param |
| T6 | **PyTorch/sentence-transformers bloat** | Medium | ~2GB dependency for embedding. If model path changes or download fails, app loses semantic matching |
| T7 | **Linux kernel strip incompatibility** | Low | `NO_STRIP=1` required on modern Arch for AppImage — if linuxdeploy gets updated, this breaks |

---

## 4. Module-by-Module Breakdown

### 4.1 Frontend Modules

| Module | Lines | State Mgmt | API Calls | Error Handling | Risk |
|--------|-------|------------|-----------|----------------|------|
| **App.tsx** | 320 | 15 useState, no context | POST scan/reevaluate/cleanup | Good (try/catch on actions) | Low |
| **DashboardView** | 297 | None (pure presentational) | None directly | N/A | Low |
| **ApplyJobView** | 346 | Local form state | POST manual, generate, GET pdf | Good (try/catch, error display) | Medium (1.8s polling) |
| **PipelineView** | 269 | Local filter state | GET export.csv | Minimal | Low |
| **ApprovalDrawer** | 642 | 18 useState | 7 distinct endpoints | Good (per-action error state) | Medium (re-renders) |
| **IngestionView** | 553 | Extensive form state | 8 endpoints | Poor (catch→setStatus("error"), no message) | Medium |
| **OnboardingWizard** | 345 | 10 useState | POST ingest, settings | Minimal | Low |
| **useWS** | 133 | useRefs + useState | WebSocket | Good (try/catch, reconnect) | Low |
| **useLeads** | 95 | leads + loading | GET /leads, GET /events | Good (alive flag, try/catch) | Low |
| **SettingsModal** | 75 | cfg + saving | GET/POST settings | **Poor** (no catch on save — "Saving?" forever) | **High** |
| **ProfileView** | 356 | profile + edit state | GET/DELETE/PUT profile | **Poor** (saveEdit/saveCandidate have no try/catch) | **High** |

### 4.2 Backend Core Modules

| Module | Lines | Complexity | Error Handling | Key Risk |
|--------|-------|------------|----------------|----------|
| **main.py** | 2036 | **Very High** (45+ routes, ghost mode, WS mgmt, CORS, auth) | **Poor** (50+ `except: pass`, race conditions in `_CM`) | Plaintext API keys, stdout token leak, `_CM` race |
| **llm.py** | 411 | Medium (17 providers, 3-tier key lookup) | **Medium** (silent `_parse_fallback` returns empty models) | Hardcoded models/URLs, no cross-provider fallback |
| **db/client.py** | 1628 | **High** (3 DB backends, 40+ CRUD functions) | **Poor** (35+ `except: pass`, no connection pooling) | Plaintext secrets, no WAL, connection thrash |
| **logger.py** | 25 | Low | Good | No date in timestamp, no file output |
| **mcp_server.py** | 191 | Low | Medium | `min_quality: 0` bug (falsy → defaults to 60) |

### 4.3 Backend Agent Modules

| Agent | Lines | Hardcoded Values | Error Handling | Security | Risk |
|-------|-------|------------------|----------------|----------|------|
| **scout.py** | 1027 | 30+ (timeouts, URLs, limits, API endpoints, terms) | Medium (broad except, tenacity retry) | **HIGH** — Apify token in URL query | **High** |
| **free_scout.py** | 711 | 25+ (ATS API endpoints, source defaults, limits) | Medium (tenacity retry, broad except) | Low (custom connector headers) | Medium |
| **x_scout.py** | 472 | 25+ (X API endpoint, queries, terms, score weights) | Medium-Low (no retry, per-tweet exceptions not caught) | Medium (bearer token) | Medium |
| **quality_gate.py** | 201 | 8+ (flags, penalties, thresholds) | **Good** (clean boolean returns, no raises) | None | **Low** |
| **evaluator.py** | 321 | 20+ (rubric weights, caps, dead system prompt copy) | **Good** (LLM fallback to deterministic) | None | Low |
| **scoring_engine.py** | 1097 | 200+ (taxonomy, keywords, weights, caps) | Medium (no try/except in main path) | None | Low |
| **generator.py** | 1216 | 30+ (templates, word limits, PDF scales, colors) | Medium (LLM fallback, dead `_draft()` code) | Medium (job_id path traversal risk) | Medium |
| **ingestor.py** | 564 | 15+ (model name, graph schema, section numbers) | Medium (thread-safe model loading, nested try/except) | Low (PII stored locally) | Low |
| **semantic.py** | 278 | 8+ (weights, stretch params) | **Excellent** (every fn returns None on failure) | None | **Low** |
| **feedback_ranker.py** | 176 | 20+ (label/feature weights, delta caps) | **Good** (empty data → 0 delta) | None | Low |
| **lead_intel.py** | 314 | 30+ (terms, weights, templates, city regex) | **None** (no try/except anywhere) | None | Low |
| **contact_lookup.py** | 234 | 15+ (API endpoints, priority, timeout) | **Good** (structured status per failure) | **HIGH** — Hunter key in URL | **High** |
| **help_agent.py** | 466 | 200+ (full guides, fallback answers) | Good (LLM→fallback chain) | Low | Low |
| **actuator.py** | 454 | 30+ (selectors, delays, vision prompts) | Medium (broad try/except, per-field skip) | Medium (env-gated submission) | Medium |
| **browser_runtime.py** | 158 | 10+ (URLs, binary paths) | Good (multi-level fallback) | Low | Low |
| **query_gen.py** | 239 | 15+ (hints, role catalog, LLM rules) | Good (LLM→deterministic fallback) | Low | Low |
| **github_ingestor.py** | 189 | 8+ (API endpoint, headers, limits) | Good (returns None on failure) | Low (optional token) | Low |
| **linkedin_parser.py** | 131 | 10+ (CSV filenames, column names) | Medium (no try/except, assumes well-formed ZIP) | Low (user PII) | Low |
| **portfolio_ingestor.py** | 165 | 8+ (timeouts, text limits) | Good (Playwright→HTTP→raw fallback chain) | Low | Low |
| **selectors.py** | 84 | 5+ (cache TTL, bundled path) | **Good** (remote→cache→bundled fallback) | None | **Low** |
| **graph/__init__.py** | 111 | 2+ (threshold defaults) | Medium (per-node try/except, but persist_node unguarded) | None | Low |

### 4.4 Rust/Tauri Sidecar

| Module | Lines | Complexity | Risk |
|--------|-------|------------|------|
| **lib.rs** | 393 | Medium (state mgmt, sidecar lifecycle, stdout parsing, process kill) | **Critical** — updater misconfig, bundle target locked to appimage, no sidecar restart, PLAYWRIGHT_BROWSERS_PATH dead code |
| **main.rs** | 6 | Trivial | None |
| **tauri.conf.json** | 78 | Medium | **Critical** — `createUpdaterArtifacts: false`, `targets: ["appimage"]` breaks Windows/macOS |

### 4.5 Build / Config / CI

| Module | Lines | Key Findings |
|--------|-------|-------------|
| **package.json** | 55 | Clean scripts. `package:linux:all` = `appimage,deb` only |
| **pyproject.toml** | 38 | All 22 deps use `>=`. No upper bounds. No linting/formatters |
| **ci.yml** | ~100 | Only runs `test_regressions.py` — 52% of tests never run |
| **release.yml** | ~200 | Multi-platform. Requires `TAURI_SIGNING_PRIVATE_KEY` secret |
| **build-sidecar.sh** | 45 | Minimal error handling. Assumes PyInstaller + rustc always succeed |

---

## 5. Cross-Cutting Concerns

### 5.1 Monoliths & Technical Debt

| File | Lines | What's Inside | Why It Matters |
|------|-------|---------------|----------------|
| `backend/main.py` | 2036 | Routes, auth, WebSocket, ghost mode, settings, validation, background tasks, CORS, API models | One change anywhere risks breaking everything. Cannot test routing without full app boot |
| `backend/db/client.py` | 1628 | SQLite, Kuzu, LanceDB — all interleaved. CRUD for leads, profile, settings, events, graph, vectors | Violates single responsibility. A schema change in any DB touches this file |
| `src/App.tsx` | 320 | 15 useState, 8 action handlers, view routing, WebSocket bridge, API factory | Every lead change re-renders all 8 views |
| `src/components/ApprovalDrawer.tsx` | 642 | PDF viewer, version history, feedback, follow-ups, pipeline runner, auto-apply, 18 useState | Mounted/unmounted with every lead selection. 18 state vars = re-render cascade |

### 5.2 `except: pass` Pattern

50+ instances across the backend. This is the single biggest code quality issue:

```python
# Common patterns found:
try:
    # something that might fail
    ...
except Exception:
    pass  # Failure silently disappears
```

| Location | What's Swallowed | Impact |
|----------|------------------|--------|
| `main.py:162,168` | WebSocket broadcast failures | Dead clients not cleaned up promptly |
| `main.py:569-570` | Ghost mode scout failures | Silent skip of entire scout stage |
| `db/client.py:219-225` | SQLite ALTER TABLE failures | Schema drift — invisible |
| `db/client.py:1272-1273, 1287-1289` | Kuzu profile reads | Empty profile returned, no error logged |
| `generator.py` (multiple) | DB write failures | Package not persisted, user sees success |

**Recommendation:** Replace every `except: pass` with at minimum `except Exception as e: _log.warning(...)`.

### 5.3 Race Conditions

| Location | Problem | Severity |
|----------|---------|----------|
| `main.py:152-171` (`_CM` class) | `add()` appends to list; `remove()` creates new list; `broadcast()` iterates + mutates. No lock. | **High** — concurrent broadcasts can corrupt client list |
| `main.py:1204` (`_scan_task` global) | Mutated without lock. Two concurrent `POST /scan` can race. | **Medium** — unlikely but possible |
| `main.py:1112` (`_ghost_lock` used for manual scans) | Ghost lock = processing lock. Ghost and manual scans block each other. | **Low** — intentional |
| `main.py:2017-2027` (heartbeat loop) | `receive_text()` with 2s timeout vs `broadcast()` iterating clients. No coordination. | **Medium** |

### 5.4 Dead Code

| Location | Code | Status |
|----------|------|--------|
| `evaluator.py:34-82` | First `_SYSTEM_PROMPT` — overwritten by second copy | Dead — remove |
| `generator.py:662` | `_draft()` function — never called | Dead — remove |
| `lead_intel.py:238` | `classify_kind()` always returns "job" | Bug — `default` parameter unused |
| `src-tauri/lib.rs:232-243` | Bundled PLAYWRIGHT_BROWSERS_PATH logic — unconditionally overwritten | Dead — remove |
| `run_diagnostics.py`, `test_ingestion.py`, `test_live_fire.py`, `force_model.py`, `update_settings.py` | Standalone scripts in backend root | Probably dead — not imported anywhere |

---

## 6. Error Handling Quality

### 6.1 Good Patterns

| Pattern | Where | Why It Works |
|---------|-------|--------------|
| Fail-soft return None | `semantic.py` — every function | Callers can check for None and degrade gracefully |
| Structured error statuses | `contact_lookup.py` — returns `{"status": "no_domain"}` | Callers know exactly what happened |
| Multi-level fallback | `browser_runtime.py`, `portfolio_ingestor.py`, `selectors.py` | Progressive degradation instead of crash |
| Per-action error state | Frontend `ApprovalDrawer.tsx` — each action has its own `err` state | User sees which action failed |
| LLM → deterministic fallback | `evaluator.py`, `query_gen.py` | Core functionality works without AI |
| Alive flag pattern | `useLeads.ts` — `alive` boolean prevents setState after unmount | No memory leaks from in-flight requests |

### 6.2 Bad Patterns

| Pattern | Where | Why Dangerous |
|---------|-------|---------------|
| `except Exception: pass` | 50+ locations | Failures vanish without trace |
| `_parse_fallback` returns empty models | `llm.py:406-411` | Caller gets empty data with no error indication |
| Silent `.catch(() => {})` | `useDueFollowups.ts`, `useGraphStats.ts` | Polling errors hidden |
| No-catch save | `SettingsModal.tsx` (frontend save), `ProfileView.tsx` (edit/save) | UI shows success when backend rejected the update |
| Bare `catch { setStatus("error") }` | `IngestionView.tsx` — most API calls | User sees "error" with zero detail about what failed |
| Async task fire-and-forget | `main.py` — `asyncio.create_task(_actuate(...))` | Unhandled exceptions silently disappear |

### 6.3 Error Handling Score by Module

```
semantic.py          ██████████ 10/10  (fail-soft everywhere)
selectors.py         ██████████ 10/10  (remote→cache→bundled)
quality_gate.py      █████████  9/10  (clean returns, no raises)
feedback_ranker.py   █████████  9/10  (empty data→0 delta)
browser_runtime.py   ████████   8/10  (multi-level fallback)
contact_lookup.py    ████████   8/10  (structured statuses)
query_gen.py         ████████   8/10  (LLM→deterministic fallback)
evaluator.py         ████████   8/10  (LLM→baseline fallback)
portfolio_ingestor.py ███████   7/10  (Playwright→HTTP→raw)
github_ingestor.py   ███████   7/10  (per-repo try/except)
scout.py             █████      5/10  (broad except, but retry)
free_scout.py        █████      5/10  (broad except, tenacity)
main.py              ███        3/10  (50+ except:pass, race conditions)
db/client.py         ███        3/10  (35+ except:pass, no pooling)
generator.py         ████       4/10  (big fallback, but dead code)
lead_intel.py        █          1/10  (no try/except anywhere)
```

---

## 7. Hardcoded Values Registry

### 7.1 URLs and API Endpoints

| Value | File | Line |
|-------|------|------|
| `https://api.x.com/2/tweets/search/recent` | `x_scout.py` | API base URL |
| `https://boards-api.greenhouse.io/v1/boards/...` | `free_scout.py` | ATS API |
| `https://api.lever.co/v0/postings/...` | `free_scout.py` | ATS API |
| `https://api.ashbyhq.com/posting-api/job-board/...` | `free_scout.py` | ATS API |
| `https://www.workable.com/api/accounts/...` | `free_scout.py` | ATS API |
| `https://api.github.com` | `github_ingestor.py` | API base URL |
| `https://api.apify.com/v2/acts/...` | `scout.py` | Scraper API |
| `https://hn.algolia.com/api/v1/search` | `scout.py` | HN API |
| `https://api.hunter.io/v2/domain-search` | `contact_lookup.py` | Contact API |
| `https://nubela.co/proxycurl/api/linkedin/profile/resolve` | `contact_lookup.py` | Contact API |
| `https://github.com/vasu-devs/JustHireMe/releases/latest/download` | `browser_runtime.py` | Browser runtime download base |
| `https://github.com/vasu-devs/JustHireMe/releases/latest/download/latest.json` | `tauri.conf.json` | Updater endpoint |
| `http://localhost:1420` | `tauri.conf.json` | Dev server URL |
| `http://127.0.0.1:${port}` | `App.tsx` | API base URL (dynamic port) |
| `ws://127.0.0.1:${p}/ws?token=...` | `useWS.ts` | WebSocket URL (dynamic) |

### 7.2 Magic Numbers and Thresholds

| Value | Where | Meaning |
|-------|-------|---------|
| `7` (days) | `scout.py`, `quality_gate.py` | Max lead age |
| `60` | `quality_gate.py`, `graph/__init__.py` | Minimum quality score / auto-generate threshold |
| `85` | `main.py` | Score threshold for auto-approval |
| `6` (hours) | `main.py` | Ghost mode interval |
| `30` | `useWS.ts` | Max sidecar retries (30s total) |
| `5000` (ms) | `useLeads.ts` | Lead polling interval |
| `1800` (ms) | `ApplyJobView.tsx` | Generate result polling interval |
| `PAGE_SIZE = 80` | `leadUtils.ts` | Pipeline page size |
| `15` (s) | `src-tauri/lib.rs` | Per-message sidecar timeout |
| `2` (s) | `main.py` | WebSocket heartbeat timeout |
| `1440x900` | `tauri.conf.json` | Default window size |
| `38` | `scoring_engine.py` | Seniority cap for no-experience candidates |
| `18` | `feedback_ranker.py` | Max signal delta from feedback |
| `5` | `feedback_ranker.py` | Confidence saturation count |

### 7.3 LLM Provider Configuration

All 17 provider base URLs and default models are hardcoded in `llm.py:56-85`:

```python
_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "nvidia": "z-ai/glm-5.1",
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "xai": "grok-4",
    "kimi": "kimi-k2-turbo-preview",
    "mistral": "mistral-large-latest",
    "openrouter": "openrouter/auto",
    "together": "openai/gpt-oss-120b",
    "fireworks": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    "cerebras": "llama-3.3-70b",
    "perplexity": "sonar",
    "huggingface": "openai/gpt-oss-120b",
    "custom": "model-id",
    "ollama": "llama3",
}
```

**Risk:** These model names go stale. Models are deprecated, renamed, or removed by providers regularly. Should be configurable or at minimum documented as stale dates.

### 7.4 Score Weights and Rubric (scoring_engine.py)

```
Role alignment:       18 pts
Stack coverage:       27 pts (20 with semantic)
Proof of work:        20 pts (18 with semantic)
Seniority fit:        20 pts
Constraints:          15 pts (12 with semantic)
Semantic fit:         15 pts (optional)
```

### 7.5 Lead Source Definitions (hardcoded defaults)

| Source | File | Type |
|--------|------|------|
| OpenAI, Anthropic, Perplexity ATS | `free_scout.py:DEFAULT_TARGETS` | Watchlist |
| RemoteOK, Remotive, Jobicy, WFH | `scout.py:_SOURCE_CAPS` | RSS/API |
| Greenhouse, Lever, Ashby, Workable | `free_scout.py` | ATS boards |
| HN "Who Is Hiring" | `scout.py`, `free_scout.py` | Algolia API |
| Reddit r/forhire | `free_scout.py` | Search API |
| GitHub issues | `free_scout.py` | Search API |
| Google dorks (`site:`) | `scout.py` | Custom search |
| X/Twitter search | `x_scout.py` | v2 API |
| Global/India source presets | `src/settings/shared.tsx` | Frontend presets |

---

## 8. Security Assessment

### 8.1 Critical Issues

| # | Issue | Location | Details | Fix |
|---|-------|----------|---------|-----|
| **C1** | **API keys stored in SQLite plaintext** | `db/client.py:923-928` | All 17 provider keys + tokens stored as `INSERT INTO settings(key,val)` — plaintext at rest. Anyone with filesystem access reads all keys | Integrate OS keychain (libsecret/Keychain/Credential Manager) |
| **C2** | **Auth token printed to stdout at startup** | `main.py:2033` | `_API_TOKEN = secrets.token_hex(32)` printed to stdout where any process reading sidecar output sees it | Only print to stderr or file descriptor not readable by other processes |
| **C3** | **Apify token in URL query parameter** | `scout.py:362` | `?token={tok}` appended to Apify API URL — leaks to HTTP logs, referrer headers | Use header-based auth if API supports it |
| **C4** | **Hunter.io key in URL query parameter** | `contact_lookup.py:118` | `?api_key={key}` same pattern | Use header-based auth |

### 8.2 Medium Issues

| # | Issue | Location | Details |
|---|-------|----------|---------|
| M1 | No token rotation | `main.py:36` | Single token for entire process lifetime. No logout endpoint |
| M2 | WebSocket token in URL | `useWS.ts`, `main.py:43` | `?token=` in query string — logged by browsers, possibly by Tauri |
| M3 | No rate limiting | all endpoints | Any route can be hammered |
| M4 | No input size limits | various | `POST /api/v1/ingest` has no explicit size cap on `raw` field |
| M5 | Path traversal in generator | `generator.py:1185-1186` | `f"{job_id}_v{new_version}.pdf"` — if `job_id` contains `../`, files written outside asset dir |
| M6 | Custom connector headers in plaintext | `main.py:1354` | Listed as sensitive but stored in plaintext SQLite |

### 8.3 Security Strengths

| # | Strength | Location |
|---|----------|----------|
| S1 | CSP restricts connect-src to localhost only | `tauri.conf.json` |
| S2 | CORS origin regex locked to localhost/tauri | `main.py:37, 633-639` |
| S3 | Bearer token required on all non-health routes | `main.py:642-653` |
| S4 | API keys masked on settings reads (`••••••••••••••••••••`) | `main.py:1352-1367` |
| S5 | Masked values preserved on settings writes | `main.py:1456-1459` |
| S6 | Auto-apply gated by `JHM_AUTO_APPLY` env var | `actuator.py:12` |
| S7 | Vision LLM prompt explicitly blocks Submit/CAPTCHA | `actuator.py:222-223` |

---

## 9. Dependency Analysis

### 9.1 Python Dependencies (pyproject.toml)

All 22 dependencies use `>=` — no upper bounds. Highest risk packages:

| Package | Version | Risk | Why |
|---------|---------|------|-----|
| `langgraph` | `>=0.2.0` | **HIGH** | v0.2.x has frequent breaking API changes |
| `anthropic` | `>=0.49.0` | **HIGH** | SDK major version bumps change API surface |
| `openai` | `>=1.30.0` | **HIGH** | SDK v2 pending — will break v1 API |
| `sentence-transformers` | `>=3.0.0` | **MEDIUM** | ~2GB download, model path changes |
| `instructor` | `>=1.3.0` | **MEDIUM** | Patch versions can change Pydantic integration |
| `kuzu` | `>=0.7.0` | **MEDIUM** | Small community, breaking storage format changes |
| `lancedb` | `>=0.17.0` | **MEDIUM** | Rapid development, breaking API changes |

### 9.2 Node Dependencies (package.json)

| Package | Version | Notes |
|---------|---------|-------|
| `@tauri-apps/api` | `^2.11.0` | Core API — stable |
| `framer-motion` | `^12.38.0` | Animation — stable API |
| `react` | `^19.1.0` | Stable |
| `tailwindcss` | `^4.2.4` | v4 is new but stable |

### 9.3 Rust Dependencies (Cargo.toml)

| Package | Version | Notes |
|---------|---------|-------|
| `tauri` | 2 | Core framework |
| `tokio` | 1 (time only) | Minimal usage |
| No `thiserror`/`anyhow` | — | All errors stringified |

### 9.4 External Services

| Service | Used By | Purpose | Requires Key? |
|---------|---------|---------|---------------|
| Apify | `scout.py` | Web scraping as a service | Yes (Apify token) |
| Hunter.io | `contact_lookup.py` | Email domain search | Yes (API key) |
| Proxycurl | `contact_lookup.py` | LinkedIn profile resolution | Yes (API key) |
| X/Twitter API | `x_scout.py` | Social job search | Yes (Bearer token) |
| GitHub API | `github_ingestor.py` | Profile import | Optional |
| Various RSS/JSON feeds | `scout.py`, `free_scout.py` | Job board data | No |
| GitHub Releases | `browser_runtime.py` | Browser runtime download | No |
| GitHub Releases | `tauri.conf.json` | App updates | No |
| Google Fonts | `index.html` | Typography CDN | No |

---

## 10. Test Coverage Analysis

### 10.1 Backend Tests (~100 total)

| File | Tests | What They Cover | Run in CI? |
|------|-------|-----------------|------------|
| `test_api.py` | 30 | Auth, health, leads CRUD, settings, export, ingestion, pipeline, form reader | **No** |
| `test_graph.py` | 7 | LangGraph compile, invoke, nodes, score range, generate gate | **No** |
| `test_mcp_server.py` | 3 | MCP init, tool list, extract tool call | **No** |
| `test_paths.py` | 12 | Data dir resolution across platforms, browser discovery | **No** |
| `test_regressions.py` | ~45 | Evaluator, generator, quality gate, semantic, feedback, scoring engine, X scout, query gen | **Yes** |

**Only 45% of backend tests run in CI.** The auth, path resolution, graph pipeline, and MCP server are never tested by CI.

### 10.2 Frontend Tests

- **1 test file**: `src/lib/leadUtils.test.ts`
- **6 test functions**: normalizeSeniority, seniorityMatches, sortLeads, leadDisplayHeading, stripCompanyPrefix, getMark
- **~20 total assertions**
- **Zero component tests.** Zero hook tests. Zero integration tests.
- **Frontend CI just runs `typecheck` (TypeScript compile check)** — no meaningful test coverage.

### 10.3 What's Not Tested At All

| Area | Why It Matters |
|------|----------------|
| WebSocket lifecycle | Reconnection, heartbeat, event dispatch |
| LLM provider routing | Fallback logic, key resolution chain |
| Settings save/load | Mask/preserve logic for sensitive keys |
| Ghost mode concurrency | Lock acquisition, timeout behavior |
| Sidecar stdout parsing | Port/token discovery protocol |
| Error boundaries | Recovery from render crashes |
| All frontend views | Dashboard, pipeline, apply, etc. |
| Race conditions | `_CM` broadcast, `_scan_task` mutation |

---

## 11. Configuration Audit

### 11.1 What's Configurable

| Mechanism | Items |
|-----------|-------|
| Env vars (`JHM_*`) | App data dir, log level, auto-apply gate, browser runtime dir, Playwright path |
| Env vars (provider keys) | 6 LLM provider API keys (OLLAMA_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) |
| Settings UI (in-app) | 74+ settings: provider selection, API keys, models, sources, automation toggles, scrapers |
| `tauri.conf.json` | Window size, CSP, bundle format, updater endpoints, deps |
| `vite.config.ts` | Dev port, HMR config |
| `pyproject.toml` | Python deps |

### 11.2 What Should Be Configurable But Isn't

| Item | Currently | Should Be |
|------|-----------|-----------|
| Ghost mode interval (6h) | `main.py:620` | Setting or env var |
| Score threshold (85) | `main.py:542` | Configurable setting |
| Default job targets | `free_scout.py:DEFAULT_TARGETS` | Config file in data dir |
| Default LLM models | `llm.py:56-73` | Config file or env vars |
| Provider base URLs | `llm.py:75-85` | Config file (some are dynamic via custom provider) |
| Lead freshness (7 days) | `scout.py:14` | Setting or env var |
| Polling intervals | `useLeads.ts:5000`, `useGraphStats.ts:10000` | Env vars or settings |
| WebSocket heartbeat (2s) | `main.py:2017` | Configurable constant |
| Max retries (30) | `useWS.ts` | Env var |
| Free source limits | `free_scout.py` | Settings (some are user-configurable) |

### 11.3 Tauri Configuration Issues

| Issue | Detail | Impact |
|-------|--------|--------|
| `createUpdaterArtifacts: false` | Updater plugin configured but no artifacts generated | Updates silently fail — user clicks "Update" → nothing happens |
| `targets: ["appimage"]` | Top-level bundle target, not platform-specific | Windows/macOS builds produce nothing |
| `PLAYWRIGHT_BROWSERS_PATH` dead code | Lines 232-243 always overwritten by lines 244-257 | Bundled browser path never used |
| NSIS hook references `backend.exe` | But `externalBin` names `jhm-sidecar` | Installer won't kill running process during update |
| Google Fonts CDN | `index.html` loads from `fonts.googleapis.com` | No internet → fallback fonts (app still works, but visual) |

---

## 12. Recommendations

### 12.1 Do Now (High Impact, Low Effort)

| # | Recommendation | Effort | Impact | Files |
|---|---------------|--------|--------|-------|
| 1 | Run full test suite in CI | 5 min | **High** — catches auth/path/regression bugs | `.github/workflows/ci.yml` |
| 2 | Fix `SettingsModal.tsx` error handling | 10 min | **High** — prevents "Saving?"-forever bug | `src/SettingsModal.tsx` |
| 3 | Fix `ProfileView.tsx` saveEdit/candidate error handling | 10 min | **High** — prevents silent save failures | `src/views/ProfileView.tsx` |
| 4 | Fix `createUpdaterArtifacts` + bundle targets | 15 min | **High** — makes updater work, fixes Windows/macOS builds | `tauri.conf.json` |
| 5 | Fix `targets: ["appimage"]` to be platform-specific | 10 min | **High** — without this, Windows/macOS release CI produces nothing | `tauri.conf.json` |

### 12.2 Do This Week (High Impact, Moderate Effort)

| # | Recommendation | Effort | Impact |
|---|---------------|--------|--------|
| 6 | Implement OS keychain for API keys | 4-8 hr | **Critical** — closes the only real security hole |
| 7 | Replace all `except: pass` with logged warnings | 2-4 hr | **High** — stops silent failure swallowing |
| 8 | Split `main.py` into `routes/` package | 4-6 hr | **High** — enables testing routing in isolation |
| 9 | Add WAL mode to SQLite + reuse connection | 1 hr | **Medium** — better concurrent performance |
| 10 | Fix `_CM` race condition in WebSocket broadcast | 2 hr | **Medium** — prevents client list corruption |

### 12.3 Defer (Low/Medium Impact)

| # | Recommendation | Effort | Why Defer |
|---|---------------|--------|-----------|
| 11 | Pin critical deps (`langgraph`, `anthropic`, `openai`) | 30 min | `uv.lock` mitigates for dev |
| 12 | Add pre-commit hooks (ruff + typecheck) | 1 hr | Nice-to-have quality gate |
| 13 | Self-host Google Fonts | 1 hr | Offline-first, but app works without them |
| 14 | Remove dead code (evaluator.py prompt, generator.py _draft, lib.rs bundled path) | 1 hr | Cleanup — no behavior change |
| 15 | Fix `lead_intel.py` `classify_kind()` always returning "job" | 10 min | Minor — may be intentional |
| 16 | Fix `mcp_server.py` `min_quality: 0` falsy bug | 5 min | Edge case — zero is invalid for quality |

### 12.4 Never (or After Upstream)

| # | Recommendation | Why |
|---|---------------|-----|
| 17 | Full frontend component test suite | Upstream's problem — fork focuses on backend correctness |
| 18 | Performance benchmarks | Not needed until app has performance issues |
| 19 | Complete type safety with mypy/pyright | Aspirational — not blocking any known issue |

---

*Report generated by `feature/codebase-audit`. Based on analysis of 70+ source files, 100 tests, and 15+ documentation files.*
