# Audit Report — JustHireMe (Linux Fork)

> Adapted from `docs/linux-migration/11-comprehensive-platform-audit.md`  
> Updated: 2026-05-09

---

## Meta

| Field | Value |
|-------|-------|
| Project | JustHireMe (fork) |
| Audit type | `Fork` |
| Upstream repo | `vasu-devs/JustHireMe` |
| Upstream last commit | 2026-05 (tree has recent dependabot PRs) |
| Audit date | 2026-05-07 |
| Audited by | Automated audit + manual review |
| Last updated | 2026-05-09 — fork context added |

---

## 1. Executive Summary

JustHireMe is a local-first AI job intelligence workbench — Tauri 2 desktop shell with a React/TypeScript frontend and Python FastAPI sidecar backend, using SQLite (CRM), Kùzu (graph), and LanceDB (vectors). The upstream is actively maintained (v0.1.25) with Windows as the primary release target.

This fork exists to port JustHireMe to Arch Linux + Hyprland (Wayland) as a fully independent downstream. The codebase is cross-platform by design (`#[cfg(windows)]` guards, Python with `expanduser` fallbacks) but has ~10 Windows-isms to fix, no Linux packaging, and a PyInstaller sidecar build that fails on Linux (file/directory conflict at `_internal/aiohttp`).

**Overall health:** `Good` — well-typed, modular, tested. Porting is moderate effort (4-6 hours).

---

## 2. Project Overview

### Purpose
Local-first AI workbench for scraping job leads, ranking fit against a user's profile graph, and generating tailored application materials (resume PDF, cover letter, outreach drafts).

### Origin (fork)
- **License:** Source-Available Non-Commercial (custom LICENSE)
- **Upstream activity:** Active — multiple dependabot branches, recent fix commits
- **Upstream release model:** Windows-only (NSIS/MSI installers via GitHub Actions)
- **Fork rationale:** Linux desktop users (Arch/Hyprland) have no supported path to run this app. Fork enables full Linux port with eventual packaging and distribution.

### Divergence plan

| Area | Upstream behaviour | Our approach |
|------|--------------------|--------------|
| Desktop shell | Tauri 2 (Windows-focused) | `Keep` — add Linux bundle targets |
| Frontend | React 19 + Vite | `Keep` — cross-platform, no changes needed |
| Backend | Python + FastAPI | `Keep` — fix data paths for XDG compliance |
| Browser automation | Playwright + Windows Chrome paths | `Extend` — add Linux browser paths |
| Scrapers | US/UK-focused sources | `Extend` — KE-specific scrapers later |
| Release pipeline | Windows-only CI | `Replace` — add Linux CI + packaging |
| Security (claimed) | "AES-256 DPAPI" (unimplemented) | `Fix` — either implement or correct docs |

---

## 3. Architecture Overview

### Directory structure

```
JustHireMe/
├── src/                     # React 19 + TypeScript frontend
├── backend/                 # Python FastAPI sidecar
│   ├── agents/              # Scout, evaluator, generator, ingestor
│   ├── db/                  # SQLite, Kùzu, LanceDB clients
│   ├── graph/               # LangGraph workflow orchestration
│   ├── main.py              # FastAPI entry point
│   └── llm.py               # LLM router (7+ providers)
├── src-tauri/               # Rust Tauri 2 shell
├── docs/                    # Architecture, migration, specs
├── scripts/                 # Build scripts (.sh + .ps1)
└── .github/                 # CI (Windows-only releases)
```

### Architecture pattern
Dual-process desktop app: Tauri (parent) spawns Python sidecar. IPC via HTTP REST + WebSocket on localhost with bearer token auth.

### Data flow (scan cycle)
User clicks Scan → backend generates queries → scout scrapes → quality gate filters → SQLite + Kùzu store → evaluator scores → UI gets WebSocket update → (optional) generator creates PDFs

---

## 4. Tech Stack (as found)

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language (frontend) | TypeScript | ~5.8.3 | Strict mode |
| Language (backend) | Python | >=3.13 | uv-managed |
| Language (shell) | Rust | stable | Tauri 2 |
| Framework (frontend) | React | ^19.1.0 | Vite-bundled |
| Framework (backend) | FastAPI | >=0.136.1 | + WebSockets |
| Desktop shell | Tauri 2 | ^2.11.0 | GTK3/WebKit2GTK |
| Database (CRM) | SQLite | stdlib | Via aiosqlite |
| Database (graph) | Kùzu | >=0.7.0 | Embedded |
| Database (vectors) | LanceDB | >=0.17.0 | Embedded |
| LLM routing | Custom router | — | 7 providers |
| Testing (backend) | pytest | >=9.0.3 | — |
| Testing (frontend) | vitest | ^4.1.5 | — |
| Build (frontend) | Vite | ^7.0.4 | — |
| Build (sidecar) | PyInstaller | >=6.20.0 | **Broken on Linux** |

### Dependency health

| Package | Issue | Severity | Recommendation |
|---------|-------|----------|----------------|
| PyInstaller | File/directory conflict at `_internal/aiohttp` on Linux | `High` | Investigate build path or switch to standalone Python for dev |
| langgraph | v0.2.x — breaking changes common | `Medium` | Pin exact version in pyproject.toml |
| kuzu | Small community, occasional breaking changes | `Low` | Monitor upstream |
| sentence-transformers | Requires PyTorch (~2GB) | `Low` | Acceptable for desktop app |

---

## 5. Code Quality Assessment

### Consistency

| Area | Observation | Impact |
|------|-------------|--------|
| Naming conventions | Consistent — snake_case Python, camelCase TS | Low |
| File/module structure | Clean separation of concerns | Low |
| Error handling style | Mixed — some try/catch, some bare raises | Medium |
| Logging approach | Python: `print()` in places, no structured logging | Medium |
| Test coverage | Backend has tests, frontend coverage unknown | Medium |

### Hardcodes & config

| Location (file:line) | Hardcoded value | Risk | Action required |
|----------------------|-----------------|------|-----------------|
| `backend/db/client.py:11` | `LOCALAPPDATA` | `Medium` | XDG-compliant fallback |
| `backend/agents/generator.py:11` | `LOCALAPPDATA` | `Medium` | XDG-compliant fallback |
| `backend/main.py:738,907` (now using `data_base()`) | `LOCALAPPDATA` | `Medium` | ✅ Fixed — uses `data_base()` from `db.client` |
| `backend/agents/browser_runtime.py:8-17` | Windows-only Chrome paths | `High` | Add Linux browser paths |
| `backend/agents/scout.py:580` | Windows User-Agent | `Low` | Make UA configurable |
| `backend/backend.spec:11` | Windows venv path | `Medium` | Cross-platform spec |
| `src-tauri/tauri.conf.json` | NSIS-only bundle targets | `High` | Add Linux targets |
| `package.json` | Windows-only package scripts | `Medium` | Add `package:linux` |

### Error handling gaps
- No startup validation (DB writable, Chromium installed, API keys configured)
- Ghost mode has no concurrency lock
- stdout-based port discovery is fragile

### Logging gaps
- Python backend uses `print()` in places instead of `logging`
- No structured logging (JSON) — makes machine parsing hard
- Rust/Tauri side has minimal logging of sidecar lifecycle

---

## 6. Security Observations

| Observation | Location | Severity | Notes |
|-------------|----------|----------|-------|
| API keys in plaintext SQLite | `backend/db/client.py` | `Critical` | All 7 LLM provider keys readable by any user-process |
| No upload size limits | `POST /api/v1/ingest` | `Low` | PDF upload could consume memory |
| HTTP without TLS | All localhost IPC | `Low` | Standard for local-only, acceptable |
| Bearer token in process listing | Sidecar startup | `Low` | Visible in `ps aux` briefly |

---

## 7. Test Coverage

| Area | Coverage status | Notes |
|------|----------------|-------|
| Unit tests (backend) | `Partial` | pytest configured, test directory exists |
| Integration tests | `Partial` | Some agent tests present |
| E2E tests | `None` | No Playwright-based E2E |
| Frontend tests | `Unknown` | vitest configured but coverage unclear |

**Overall:** Tests exist for backend agents and DB layers. No E2E or frontend tests visible. Not a blocker for porting — we can add tests as we fix Windows-isms.

---

## 8. Known Issues & Technical Debt

| # | Issue | Location | Severity | Owned by this project? |
|---|-------|----------|----------|------------------------|
| D1 | PyInstaller build fails on Linux (`_internal/aiohttp` conflict) | `backend/backend.spec` | `High` | `Yes` |
| D2 | Sidecar stdout parsing fragile | `src-tauri/src/lib.rs:223-235` | `High` | `Yes` |
| D3 | Placeholder data in generator | `backend/agents/generator.py:536` | `Low` | `Yes` |
| D4 | Security docs claim encryption that doesn't exist | `project.md`, `SPEC.md` | `Medium` | `Yes` |
| D5 | Loose dependency pins (`>=`) across all deps | `backend/pyproject.toml` | `Medium` | `Yes` |

---

## 9. Constraints Imposed on Spec Work

- **PyInstaller sidecar build is broken on Linux** — dev mode (`uv run python main.py`) works, but release packaging needs a fix or alternative
- **No Linux bundle targets in Tauri config** — needed before any Linux release can happen
- **Data dirs use Windows paths** — must be fixed early or data will be scattered across filesystem
- **API keys stored in plaintext** — should be addressed if we ever share/distribute this fork
- **README omits Linux system deps** — setup friction until documented

---

## 10. Recommended Pre-Work

| Priority | Task | Reason | Estimated effort |
|----------|------|--------|-----------------|
| 1 | Fix data dirs to XDG-compliant paths | Avoids data fragmentation across filesystem | `Small` |
| 2 | Add Linux browser paths to browser_runtime.py | Enables automation features on Linux | `Small` |
| 3 | Add Linux bundle targets to tauri.conf.json | First step toward Linux packaging | `Small` |
| 4 | Add `package:linux` npm script | Developer convenience | `Small` |
| 5 | Document Linux system deps in README | Reduces setup friction | `Small` |

> Full detailed fix inventory: `docs/linux-migration/11-comprehensive-platform-audit.md`

---

## 11. Progressive Update Log

| Date | Phase / Feature | Area touched | New findings |
|------|----------------|--------------|--------------|
| 2026-05-09 | Constitution init | docs/specs/ | Fork audit adopted from linux-migration audit |
| 2026-05-09 | Phase 1 Foundation | backend/, src-tauri/, scripts/, docs/ | XDG data paths fixed, browser detection refactored, sidecar build fixed, AppImage target configured. Remaining: update_settings.py, force_model.py, package.json duplicate key — all addressed in audit. |
| 2026-05-09 | Test infrastructure audit | backend/tests/ | Identified 3x copy-pasted fake storage classes (~60 lines each), global `os.makedirs` monkey-patch, duplicated env setup across test files. Coverage gaps: no tests for `data_base()` XDG path, `chromium_executable()` Linux behavior. Mitigation and refactoring deferred to Phase 2. |

---

*Last updated: 2026-05-09 — Agent*
