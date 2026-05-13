# Tech Stack

> **Living document.** When a technology decision changes, update this file AND note the reason.
> Agent: treat this file as the source of truth for all tooling, language, and architecture decisions.
> Never introduce a new dependency or deviate from patterns defined here without explicit instruction.

---

## Language(s)

| Language | Version (pin this) | Role |
|----------|--------------------|------|
| Rust | stable (rustup) | Desktop shell (Tauri 2), sidecar management, IPC bridge |
| TypeScript | ~5.8.3 | Frontend UI (React 19) |
| Python | >=3.13 | Backend sidecar (FastAPI, agents, DB layers) |

---

## Runtime & Environment

| Runtime | Version | Notes |
|---------|---------|-------|
| Node.js | 20+ (LTS recommended) | Frontend build, npm scripts |
| Python | >=3.13 | Managed via `uv` |
| Rust | stable | Managed via `rustup` |
| uv | latest | Python package manager (faster than pip) |

---

## Framework(s)

| Framework | Version | Layer | Reason for choice |
|-----------|---------|-------|-------------------|
| Tauri 2 | ^2.11.0 | Desktop shell | Lightweight alternative to Electron. Rust-based. Linux-native via GTK3/WebKit2GTK. |
| React | ^19.1.0 | Frontend | Current stable. Strong ecosystem. |
| Vite | ^7.0.4 | Build tool | Fast HMR, TypeScript-native. |
| Tailwind CSS | ^4.2.4 | Styling | Utility-first, composable. |
| FastAPI | >=0.136.1 | Backend API | Async-native, auto-docs, WebSocket support. |
| LangGraph | >=0.2.0 | Agent orchestration | State machine for multi-agent workflows. |

---

## Database

| Component | Choice | Notes |
|-----------|--------|-------|
| Database engine (CRM) | SQLite | Local-first relational store for leads, events, settings |
| Database engine (graph) | Kùzu >=0.7.0 | Embedded property graph for profile ontology |
| Database engine (vectors) | LanceDB >=0.17.0 | Embedded vector store for semantic search |
| ORM / query layer | aiosqlite (SQLite) / Kùzu Python API / LanceDB Python API | No ORM abstraction layer |

---

## Key Libraries & Dependencies

| Package | Version (pinned) | Purpose | Notes |
|---------|------------------|---------|-------|
| framer-motion | ^12.38.0 | UI animations | Frontend |
| @tauri-apps/api | ^2.11.0 | Tauri IPC from frontend | Frontend |
| @tauri-apps/plugin-shell | ^2.3.5 | Sidecar process management | Rust/Frontend |
| @tauri-apps/plugin-opener | ^2 | Open external links | Rust |
| @tauri-apps/plugin-updater | ^2.10.1 | In-app updates | Rust |
| uvicorn | >=0.46.0 | ASGI server for FastAPI | Backend |
| websockets | >=16.0 | Real-time UI updates | Backend |
| anthropic / openai / instructor | >=0.49.0 / >=1.30.0 / >=1.3.0 | LLM providers + structured output | Backend |
| sentence-transformers | >=3.0.0 | Local embeddings | Backend (requires PyTorch ~2GB) |
| playwright | >=1.44.0 | Browser automation / scraping | Backend |
| httpx | >=0.27.0 | Async HTTP client | Backend |
| fpdf2 | >=2.7.0 | PDF generation | Backend |
| apscheduler | >=3.10.0 | Ghost mode scheduling | Backend |
| pypdf | >=4.0.0 | PDF parsing (ingestion) | Backend |
| tenacity | >=9.1.4 | Retry logic | Backend |

> **Rule:** Dependencies should have pinned versions in lockfiles. Upstream uses `>=` in `pyproject.toml` with `uv.lock` for reproducibility. Keep uv.lock committed.

---

## Architecture Pattern

Dual-process desktop application. Tauri (parent process) spawns a Python FastAPI sidecar. Frontend communicates with the backend via HTTP REST + WebSocket on localhost with bearer token auth.

```
┌─────────────────────────────────────────────────────┐
│              Tauri 2 Desktop Shell (Rust)            │
│  React UI ←→ Tauri IPC ←→ shell plugin (sidecar)    │
└──────────────────────────────────┬──────────────────┘
                                   │ spawns
                                   ▼
┌─────────────────────────────────────────────────────┐
│         Python FastAPI Sidecar (uvicorn)             │
│  Scrapers → Quality Gate → SQLite/Kuzu/LanceDB       │
│  Evaluator (LLM/rubric) → Generator (PDF)            │
└─────────────────────────────────────────────────────┘
```

### Directory Structure (top-level)

```
JustHireMe/
├── src/              # React + TypeScript frontend
├── backend/
│   ├── config/       # Typed config by domain (scoring.py, llm.py, scraping.py, etc.)
│   └── ...           # FastAPI sidecar
├── data/
│   └── config/       # User-facing config (sources.yaml, filters.yaml, ghost_mode.yaml)
├── src-tauri/        # Rust Tauri shell
├── docs/             # Architecture, migration, specs
├── scripts/          # Build scripts
├── .github/          # CI/CD
└── skills/           # Agent skill definitions
```

---

## Code Quality Standards

### General
- [x] No hardcoded values — all config via environment variables or a dedicated config module
- [ ] No `console.log` / `print` left in production code — use structured logging only *(Not yet enforced — backend uses print() in places)*
- [x] Every function has a single, clear responsibility
- [ ] No silent failures — all errors must be caught, logged, and handled explicitly *(Partial — some gaps identified in audit)*

### Logging
- **Library:** Python: `logging` module / Rust: `log` + `tracing`
- **Format:** Currently plain text. Target: structured JSON with timestamp, level, message, context
- **Levels in use:** `DEBUG | INFO | WARN | ERROR`
- **Rule:** Log at boundaries (function entry/exit for complex ops, all error paths). Never swallow exceptions silently.

### Error Handling
- All async operations must handle rejection explicitly — no unhandled promise rejections
- Errors must propagate with context, not be swallowed (`raise ... from original_exception`)
- User-facing errors must never expose internal stack traces
- Distinguish between operational errors (expected, recoverable) and programmer errors (bugs)

### TypeScript
- Strict mode: `"strict": true` in `tsconfig.json` — non-negotiable
- No `any` without explicit comment justification
- All exported functions must have explicit return types

### Python
- Type hints required on all function signatures *(Upstream uses them — maintain)*
- Use `logging` module — never bare `print()` in non-script code
- `mypy` or `pyright` for static type checking *(Not yet enforced — aspirational)*

---

## Testing Strategy

| Test Type | Tool | Scope | When it runs |
|-----------|------|-------|--------------|
| Unit | pytest (backend), vitest (frontend) | Individual functions, agents, DB helpers | On every commit |
| Integration | pytest | Agent workflows, API endpoints | On PR / before merge |
| Manual | Checklist (see feature specs) | Happy path + edge cases | Pre-release |

> **Rule:** New features require corresponding tests before they are considered complete.

---

## API Design

- **Style:** REST + WebSocket
- **Versioning:** `/api/v1/...`
- **Auth:** Bearer token (JHM_TOKEN) generated by backend at startup, relayed via Tauri IPC
- **Error responses:** All errors return structured JSON: `{ "error": { "code": "...", "message": "..." } }`

---

## Environment & Configuration

- All secrets via environment variables — never committed to version control (API keys currently stored in SQLite settings table — known gap)
- `.env.example` must be kept up to date with all required variables
- Config validation at startup — app should fail fast with clear error if required env vars are missing *(Not yet implemented — identified in audit)*

---

## Infrastructure & Deployment

| Concern | Approach | Notes |
|---------|----------|-------|
| Hosting | Local desktop only | No cloud deployment |
| CI/CD | GitHub Actions | Currently Windows-only. Target: add Linux runner. |
| Containerization | None | Desktop app, not server |
| Secrets management | Environment variables / SQLite settings | SQLite storage is a known security gap |
| Packaging | Tauri bundle (AppImage/deb) | Target `npm run package:linux` |
| Distribution | GitHub Releases | Manual for now, automated eventually |

---

## Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-09 | Keep upstream tech stack unchanged for core | Fork is about Linux porting, not re-architecting | Rewriting backend in Rust, switching DBs |
| 2026-05-09 | No containerization or cloud deployment | Local-first is a core value of the upstream project | Docker dev environment |
| 2026-05-09 | Full independent fork (no upstream PRs) | Focus on Linux port first. Upstream contributions deferred. | Contributing changes upstream |
| 2026-05-13 | Authority-boundary config layers for Phase A | Prevents chaos from extracting 150+ hardcodes. Uses Pydantic validation + domain-aligned file structure. | Monolithic settings.py, flat config.yaml, OS.getenv everywhere |
| 2026-05-13 | Solo fork strategy (watch upstream, don't contribute) | Phase A makes deep structural changes upstream wouldn't accept | Keeping changes PR-friendly from start |

---

*Last updated: 2026-05-09 — Agent*
