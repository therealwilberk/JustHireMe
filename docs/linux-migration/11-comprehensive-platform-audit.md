# Comprehensive Platform Audit: JustHireMe on Linux

**Date:** 2026-05-07  
**Target:** Arch Linux + Hyprland (Wayland)  
**Author:** Automated audit  
**Source:** Full source tree review — every `.py`, `.tsx`, `.rs`, `.toml`, `.json`, `.md`, `.yml` file.

---

## Table of Contents

1. [System Architecture (How It Works)](#1-system-architecture-how-it-works)
2. [OS-Specific Dependencies](#2-os-specific-dependencies)
3. [Hardcoded Windows Assumptions](#3-hardcoded-windows-assumptions)
4. [Arch Linux / Hyprland Compatibility Risks](#4-arch-linux--hyprland-compatibility-risks)
5. [Documentation vs. Implementation Mismatches](#5-documentation-vs-implementation-mismatches)
6. [Fragile Architecture Decisions](#6-fragile-architecture-decisions)
7. [Security & Maintainability Concerns](#7-security--maintainability-concerns)
8. [Dependency & Version Review](#8-dependency--version-review)
9. [Setup Flow Verification](#9-setup-flow-verification)
10. [Verdict & Recommendations](#10-verdict--recommendations)

---

## 1. System Architecture (How It Works)

### Process Topology

```
┌─────────────────────────────────────────────────────────────┐
│                   Tauri 2.0 Desktop Shell (Rust)            │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │ React 19 +   │  │  Tauri IPC:                        │  │
│  │ Vite +       │  │  • get_sidecar_port()               │  │
│  │ Tailwind 4   │  │  • get_api_token()                  │  │
│  │ TypeScript   │  │  • notify_high_score_lead()          │  │
│  └──────┬───────┘  │  • tauri-plugin-opener (links)      │  │
│         │          │  • tauri-plugin-shell (sidecar)      │  │
│         │          │  • tauri-plugin-notification         │  │
│         │          └───────────────┬──────────────────────┘  │
│         │                          │                         │
│         ▼                          ▼                         │
│  ┌──────────────────────────────────────────────────┐       │
│  │       HTTP REST + WebSocket (ws://127.0.0.1)     │       │
│  │       Bearer token auth (JHM_TOKEN=xxx)           │       │
│  └──────────────────────┬───────────────────────────┘       │
└─────────────────────────┼───────────────────────────────────┘
                          │ spawns (via shell plugin)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Python FastAPI Sidecar (uvicorn)                │
│                                                              │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Scout Agent │  │ Quality  │  │Evaluator │  │Generator│ │
│  │ (Playwright │  │ Gate     │  │(LLM or   │  │(LLM →   │ │
│  │  + httpx)   │  │(determ.) │  │ rubric)  │  │ fpdf2)  │ │
│  └──────┬──────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│         │               │             │              │      │
│         ▼               ▼             ▼              ▼      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Scheduled Ghost Mode (6hr)              │   │
│  │         APScheduler → scout → eval → gen → apply    │   │
│  └──────────────────────────┬──────────────────────────┘   │
│                             │                                │
│              ┌──────────────┼──────────────┐                │
│              ▼              ▼              ▼                │
│         SQLite CRM     Kùzu Graph     LanceDB Vectors       │
│         (leads,        (profile       (embeddings)          │
│          events,        ontology)                            │
│          settings)                                           │
│              │                                               │
│              ▼                                               │
│         PDF Assets (filesystem)                              │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              LLM Router (llm.py)                     │   │
│  │  Anthropic │ OpenAI │ Groq │ Gemini │ NVIDIA │ Ollama│   │
│  │  DeepSeek  │  instructor (structured output)         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow (Scan Cycle)

```
1. User clicks "Scan" → POST /api/v1/scan
2. Backend generates profile-tailored queries (query_gen.py)
3. Scout agent scrapes:
   - RSS feeds (httpx + xml.etree)
   - RemoteOK/Remotive/Jobicy APIs (httpx)
   - HN "Who Is Hiring" (Algolia API)
   - Google dorking for ATS boards (Playwright crawl)
   - X/Twitter posts (x_scout.py)
   - Free sources (free_scout.py)
   - Apify actors (optional)
4. Each lead passes Quality Gate (deterministic: URL, freshness, seniority, red flags)
5. Passed leads written to SQLite CRM + Kùzu graph
6. Evaluator scores each lead:
   - Deterministic rubric first (scoring_engine.py)
   - Optional LLM refinement (if API key configured)
7. Scores saved, UI updated via WebSocket broadcast
8. (Optional) Generator creates tailored resume/cover letter PDFs
9. (Experimental) Actuator auto-submits via Playwright
```

---

## 2. OS-Specific Dependencies

### System Packages (Tauri on Linux)

| Dependency | Arch Package | Required By | Notes |
|-----------|-------------|-------------|-------|
| WebKitGTK 4.1 | `webkit2gtk-4.1` | Tauri 2 | Core rendering engine |
| GTK 3 | `gtk3` | Tauri 2 | Dialog toolkit |
| libappindicator | `libayatana-appindicator` | Tauri 2 | System tray |
| librsvg | `librsvg` | Tauri 2 | SVG icon rendering |
| dbus | `dbus` | Tauri 2 | IPC |
| OpenSSL | `openssl` | Tauri 2 / Rust | TLS |
| libsoup | `libsoup3` | WebKit | HTTP backend |
| cairo | `cairo` | WebKit | 2D rendering |
| gdk-pixbuf2 | `gdk-pixbuf2` | WebKit | Image loading |
| pango | `pango` | WebKit | Text layout |
| gcc / make | `base-devel` | Rust compilation | Build tools |
| Python 3.13+ | `python` | Backend sidecar | Available |
| Node.js 20+ | `nodejs-lts-iron` | Frontend build | Available |
| Rust | `rustup` / `rust` | Tauri build | Available |
| uv | `uv` (AUR) | Python package mgmt | AUR only |
| Chromium | `playwright-chromium` (AUR) | Playwright scraping | Optional |

### Python Runtime Dependencies (from `pyproject.toml`)

All `pip`-installable. Native wheels exist for Linux on all major packages:

| Package | Min Version | Linux Wheel | Notes |
|---------|-------------|-------------|-------|
| kuzu | >=0.7.0 | ✅ | Embedded graph DB, native extension |
| lancedb | >=0.17.0 | ✅ | Embedded vector DB, native extension |
| sentence-transformers | >=3.0.0 | ✅ | Requires PyTorch (~2GB) |
| playwright | >=1.44.0 | ✅ | Downloads Chromium binary |
| fpdf2 | >=2.7.0 | ✅ | Pure Python |
| uvicorn | >=0.46.0 | ✅ | Pure Python |

### Rust Dependencies (from `Cargo.toml`)

All cross-platform. No platform-specific crates beyond the `cfg(windows)` guarded `CommandExt`.

---

## 3. Hardcoded Windows Assumptions

### 3.1 Browser Binary Paths — `backend/agents/browser_runtime.py:8-17`

```python
candidates = [
    os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
```

**Impact:** Browser auto-apply and headed scraping broken on Linux.  
**Fix:** Add `/usr/bin/google-chrome`, `/usr/bin/chromium`, `/usr/bin/chromium-browser`, `flatpak` paths.  
**Severity:** BLOCKER for automation features. Not needed for headless scraping (Playwright downloads its own binary).

### 3.2 Data Directory — `backend/db/client.py:11`

```python
_b = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe")
```

**Impact:** On Linux, creates `~/JustHireMe/` instead of XDG Base Directory-compliant `~/.local/share/JustHireMe/`.  
**Fix:** Prefer `$XDG_DATA_HOME` / `~/.local/share/` on Linux.  
**Severity:** HIGH — data location nonstandard, breaks backup/restore conventions.

### 3.3 Asset Directory — `backend/generator.py:10-13`

```python
_assets = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "JustHireMe", "assets",
)
```

**Same issue** as db/client.py — falls back to `~/JustHireMe/assets/` on Linux.  
**Severity:** MEDIUM.

### 3.4 PDF Version Base Dir — `backend/main.py:658,827`

```python
base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe", "assets")
```

**Same pattern** in `get_lead_versions` and `get_lead_pdf`.  
**Severity:** MEDIUM.

### 3.5 User-Agent String — `backend/agents/scout.py:580`

```python
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ..."
```

**Impact:** Sites may serve Windows-specific content or layouts to a Linux browser.  
**Severity:** LOW — cosmetic/may affect scraping reliability.

### 3.6 PyInstaller Spec — `backend/backend.spec:11`

```python
venv_site_packages = backend_root / ".venv" / "Lib" / "site-packages"
```

**Impact:** On Linux, venv site-packages lives at `.venv/lib/python3.13/site-packages`. This only matters for PyInstaller builds (Windows release packaging).  
**Severity:** MEDIUM — only affects release builds.

### 3.7 Tauri Config — `src-tauri/tauri.conf.json`

```json
"bundle": { "targets": ["nsis"] }
```

**Impact:** No Linux bundle target configured. Need `"appimage"`, `"deb"`, or custom.  
**Severity:** HIGH — no Linux installer can be built.

### 3.8 Package Scripts — `package.json`

```json
"package:windows": "tauri build --bundles nsis",
"package:windows:all": "tauri build --bundles nsis msi",
"package:windows:msi": "tauri build --bundles msi"
```

**Impact:** No `package:linux` script exists.  
**Severity:** MEDIUM.

### 3.9 GitHub Actions — `.github/workflows/release.yml`

Windows-only release pipeline. No Linux runner configuration for release builds.  
**Severity:** HIGH for anyone wanting automated Linux releases.

### 3.10 Unimplemented Windows API Claims

| Source | Claim | Reality |
|--------|-------|---------|
| `project.md`, `SPEC.md` | "AES-256 Encryption using Windows DPAPI or Machine_UUID" | **Not implemented anywhere.** API keys stored in plaintext in SQLite settings table. |
| `SPEC.md` | "Key Storage: AES-256 encryption using Windows DPAPI or Machine_UUID" | Same — never implemented. |

**Severity:** HIGH — misleading documentation about nonexistent security features.

---

## 4. Arch Linux / Hyprland Compatibility Risks

### 4.1 Tauri + XWayland

- Tauri 2 on Linux uses GTK/WebKit which render through XWayland on Wayland compositors
- This works but has known issues:
  - **HiDPI scaling** may be blurry or inconsistent across monitors with different scale factors
  - **Window decorations** may not match Hyprland theme
  - **Drag-and-drop** between Wayland-native apps and XWayland windows may fail
- Fix: Tauri 2 has experimental Wayland support via `WEBKIT_DISABLE_COMPOSITING_MODE=1` or `GDK_BACKEND=wayland`

### 4.2 Playwright + Wayland

- **Headless mode**: Works perfectly (doesn't need display)
- **Headed mode**: Needs `DISPLAY` or `WAYLAND_DISPLAY` environment
  - Chromium under Wayland needs `--headless=new` or `--ozone-platform-hint=auto`
  - Playwright's `launch_chromium` in `browser_runtime.py` doesn't pass Wayland flags
- The experimental actuator (auto-apply) uses headed mode for form filling

### 4.3 System Tray

- `libayatana-appindicator` must be installed on Arch
- Tauri's system tray operates through AppIndicator protocol
- Hyprland needs `wlr-layer-shell-unstable-v1` (usually included)
- May need `hyprctl` calls to manage tray visibility

### 4.4 File Dialogs

- Tauri uses GTK's native file dialog on Linux
- Works under XWayland, native under Wayland if `GDK_BACKEND=wayland`
- No code changes needed

### 4.5 GPU / Rendering

- WebKitGTK can use `mesa` or `nvidia` drivers
- On Hyprland, WebKit renders via EGL/GLX through XWayland
- Some GPUs may have rendering glitches (AMD generally fine, NVIDIA may need `__GLX_VENDOR_LIBRARY_NAME=nvidia`)

---

## 5. Documentation vs. Implementation Mismatches

| # | Doc Claim | Real Implementation | Gap |
|---|-----------|-------------------|-----|
| 1 | ARCHITECTURE.md: "Storage: `~/.local/share/JustHireMe/` (Linux)" | Code uses `%LOCALAPPDATA%` or `~/JustHireMe` | Doc says one thing, code does another |
| 2 | README: "Requirements: Node.js 20+, Python 3.13+, Rust, uv, Git" | No mention of webkit2gtk, librsvg, libayatana-appindicator | Missing **critical system deps** for Tauri on Linux |
| 3 | README: Quick Start assumes `npm run tauri dev` works immediately | Fails on Linux without 10+ system packages | No Linux setup guidance anywhere in README |
| 4 | SPEC.md: "AES-256 encryption using Windows DPAPI" | Keys in SQLite plaintext | Feature claimed but never built |
| 5 | project.md: "AES-256 Encryption using Windows DPAPI or Machine_UUID" | Same — not implemented | Unsupported security claim |
| 6 | SPEC.md: "Bundle Format: Portable .exe (Wix Toolset)" | Confirmed — only Windows format specified | Linux packaging never designed |
| 7 | ARCHITECTURE.md: "LLM Router: Anthropic, Groq, NVIDIA, Ollama" + OpenAI, Gemini, DeepSeek in code | Code has all 6+ providers | Doc is already outdated — code supports more providers than documented |
| 8 | README: "First public packaging target is Windows" | release.yml confirms Windows-only | Linux packaging has no target date in ROADMAP.md |

---

## 6. Fragile Architecture Decisions

### 6.1 Stdout-Based Port Discovery (HIGH)

**`src-tauri/src/lib.rs:223-235`**

```rust
// Tauri reads Python stdout to find PORT: and JHM_TOKEN= lines
CommandEvent::Stdout(b) => {
    let line = String::from_utf8_lossy(&b).trim().to_string();
    if let Some(port_str) = line.strip_prefix("PORT:") { ... }
    else if let Some(token) = line.strip_prefix("JHM_TOKEN=") { ... }
}
```

**Problem:** If the Python backend prints anything else to stdout (e.g., from a library, logging misconfiguration, or `print()` debugging), parsing breaks silently. The sidecar never starts properly from the user's perspective, with only `eprintln!` messages to stderr for diagnostics.

**Fix:** Use a sidecar handshake file, environment variable, or Tauri sidecar protocol.

### 6.2 Three Embedded Databases (MEDIUM)

SQLite (CRM) + Kùzu (graph) + LanceDB (vectors).

- No cross-DB transaction consistency
- If Kùzu DB is corrupted, profile operations silently degrade
- If LanceDB fails initialization, a `_NullVectorStore` no-op replaces it — features degrade without user visibility
- Each DB has its own connection management pattern (Kùzu creates new `Connection(db)` objects per call — this is correct for Kùzu's MVCC, but unusual)

### 6.3 Heavy ML Dependency Chain (MEDIUM)

`sentence-transformers` requires PyTorch (~2GB+ download, ~800MB installed).

- PyTorch is explicitly **excluded** from PyInstaller bundles (`backend.spec:52-55`)
- But `sentence-transformers` is a runtime dependency in `pyproject.toml`
- First-run downloads model files (hundreds of MB) from HuggingFace
- Network required at runtime for model download
- No model caching strategy documented

### 6.4 No Startup Validation (MEDIUM)

`main.py:528-536` — the `lifespan` context manager starts the server without:

- Checking Kùzu DB path is writable
- Verifying LanceDB connection
- Checking Playwright/Chromium availability
- Validating API keys
- Confirming asset directory is writable

Failures surface as 500 errors when the user triggers a feature.

### 6.5 Ghost Mode Scheduler (LOW)

APScheduler fires every 6 hours regardless of system state. No:
- Lock to prevent concurrent ghost + manual scans
- Power/battery awareness
- Network availability check
- Progressive backoff on repeated failures

### 6.6 Graceful Fallback Over-Silence (LOW)

The `_parse_fallback` in `llm.py:299-304` returns an empty/zeroed Pydantic model when no LLM is configured. Downstream code may not notice and could produce empty evaluations silently. The quality gate, evaluator, and generator all have fallbacks, but they sometimes mute real errors.

### 6.7 Port Binding Race (LOW)

`_free_port()` in `main.py:28-31` binds to port 0 (OS picks), gets the port, then unbinds. There's a tiny race window where another process grabs the port before uvicorn starts. In practice this is rare on localhost.

---

## 7. Security & Maintainability Concerns

### 7.1 API Key Storage (CRITICAL)

| Detail | Value |
|--------|-------|
| Storage | SQLite `settings` table, key-value store |
| Encryption | **None** — plaintext in `~/.local/share/JustHireMe/crm.db` |
| Access | Any process with user file read access |
| Documentation | claims "Windows DPAPI" but never implemented |

Plaintext API keys for OpenAI, Anthropic, Groq, Gemini, DeepSeek, NVIDIA are accessible to any process or script running as the same user.

### 7.2 Loose Dependency Pins (MEDIUM)

`pyproject.toml` uses `>=` for all dependencies (e.g., `fastapi>=0.136.1`). Combined with weekly Dependabot updates, this means transitive updates can introduce breaking changes without explicit review. The `uv.lock` file pins exact versions for development, but re-running `uv sync` may pull newer versions.

### 7.3 No Input Size Limits on Uploads (LOW)

`POST /api/v1/ingest` accepts files without a size limit in the route handler (the `UploadFile` has no `max_size`). File size is only checked for LinkedIn ZIP uploads (`50 MB guard`). A large PDF upload could consume memory during PyPDF parsing.

### 7.4 HTTP Without TLS (LOW/LOCALHOST)

All traffic between Tauri and Python sidecar is plain HTTP/WS on `127.0.0.1`. This is standard for local-only IPC and acceptable since the interface is not exposed to the network. The CSP in `tauri.conf.json` correctly restricts connections to `http://127.0.0.1:*`.

### 7.5 Bearer Token Management (LOW)

The JHM_TOKEN is generated by the Python backend and sent to Tauri via stdout, then relayed to the frontend via Tauri IPC (`invoke("get_api_token")`). The frontend then includes it in every HTTP request header. This is reasonable for local-only operation, but the token is visible in process listings and memory.

---

## 8. Dependency & Version Review

### Frontend (`package.json`)

| Package | Version | Status |
|---------|---------|--------|
| react | ^19.1.0 | ✅ Current stable |
| react-dom | ^19.1.0 | ✅ Current stable |
| framer-motion | ^12.38.0 | ✅ Current |
| tailwindcss | ^4.2.4 | ✅ Current major version |
| @tauri-apps/api | ^2.11.0 | ✅ Current |
| @tauri-apps/plugin-opener | ^2 | ✅ Current |
| @tauri-apps/plugin-shell | ^2.3.5 | ✅ Current |
| vite | ^7.0.4 | ✅ Current major |
| typescript | ~5.8.3 | ✅ Current |
| vitest | ^4.1.5 | ✅ Current |

### Backend (`pyproject.toml`)

| Package | Min Version | Status |
|---------|-------------|--------|
| Python | >=3.13 | ✅ Very current |
| fastapi | >=0.136.1 | ✅ Current |
| uvicorn | >=0.46.0 | ✅ Current |
| kuzu | >=0.7.0 | ⚠️ Stable, small community |
| lancedb | >=0.17.0 | ✅ Active development |
| sentence-transformers | >=3.0.0 | ✅ Current |
| playwright | >=1.44.0 | ✅ Current |
| anthropic | >=0.49.0 | ✅ Current |
| openai | >=1.30.0 | ✅ Current |
| instructor | >=1.3.0 | ✅ Current |
| langgraph | >=0.2.0 | ⚠️ Breaking changes common |
| fpdf2 | >=2.7.0 | ✅ Current |

### Rust (`Cargo.toml`)

| Crate | Version | Status |
|-------|---------|--------|
| tauri | 2 | ✅ Current stable |
| tauri-plugin-opener | 2 | ✅ |
| tauri-plugin-shell | 2.3.5 | ✅ |
| tauri-plugin-notification | 2 | ✅ |
| serde | 1 | ✅ |
| serde_json | 1 | ✅ |

### Potentially Outdated / Risky

| Package | Risk | Reason |
|---------|------|--------|
| `langgraph` | **HIGH** | v0.2 has breaking changes through v0.x; Python API still evolving rapidly. The current `graph/__init__.py` usage is simple enough that this is manageable. |
| `kuzu` | **MEDIUM** | Relatively new embedded graph DB (v0.7). Smaller community than Neo4j. Python API stability improving but occasional breaking changes. |
| `sentence-transformers` + PyTorch | **MEDIUM** | Heavy dependency chain. PyTorch 2.x is stable but large. Wayland GPU acceleration may require additional CUDA/ROCm setup on Arch. |

---

## 9. Setup Flow Verification

### What the README Says

```bash
git clone <repo>
cd JustHireMe
npm install
cd backend
uv sync --dev
cd ..
npm run tauri dev
```

### What's Actually Needed on Linux

```bash
# 1. Clone
git clone <repo> && cd JustHireMe

# 2. Install missing system deps (NOT in README)
sudo pacman -S webkit2gtk-4.1 gtk3 libayatana-appindicator librsvg \
               dbus openssl libsoup3 cairo gdk-pixbuf2 pango base-devel

# 3. Rust toolchain (NOT in README)
rustup default stable

# 4. Node + Python (if not installed)
npm install    # works as documented

# 5. Python deps
cd backend
uv sync --dev  # works as documented
cd ..

# 6. Install Playwright browsers (NOT in README)
cd backend
uv run playwright install chromium
cd ..

# 7. Run (documents as is)
npm run tauri dev
```

**Gaps between docs and reality:**
- README omits 10+ system packages required by Tauri on Linux
- README omits Playwright browser installation step
- README omits Rust toolchain installation
- No `.env` setup guidance
- `mysqlclient` / `libpq` equivalents may be needed depending on whether Apify actors use them

---

## 10. Verdict & Recommendations

### Summary

| Dimension | Rating | Details |
|-----------|--------|---------|
| **Portability** | MODERATE | ~4-6 hrs for full Linux setup. 10 Windows-isms to fix. |
| **Code Quality** | GOOD | Well-typed, modular, tested. Solid patterns overall. |
| **Maintainability** | MODERATE | 3 databases, heavy ML deps, evolving LangGraph API. |
| **Security** | WEAK | Plaintext API keys in SQLite. No encryption despite docs claiming it. |
| **Docs Accuracy** | FAIR | ARCHITECTURE.md contradicts code on data paths. README misses Linux deps. |
| **Value** | HIGH | Local-first AI job tooling is genuinely useful. Architecture is sound. |

### What Works on Linux Today (Zero Changes)

- ✅ React/Vite frontend build and dev server
- ✅ Python FastAPI backend (all agents, DB layers, LLM routing)
- ✅ Kùzu graph database (pure Python wheel with native extension)
- ✅ LanceDB vector store
- ✅ SQLite CRM
- ✅ MCP server
- ✅ Frontend+backend test suites
- ✅ CI pipeline (already runs on Ubuntu)
- ✅ Headless Playwright scraping

### What Needs Changes (4-6 Hours Total)

| Task | Effort | Priority |
|------|--------|----------|
| XDG data dirs in `db/client.py`, `generator.py`, `main.py` | 30 min | P0 — fixes data location |
| Browser paths in `browser_runtime.py` | 10 min | P0 — enables automation |
| Tauri bundle config for Linux | 1 hr | P1 — enables packaging |
| Add Linux system deps to README | 20 min | P1 — reduces friction |
| Add `package:linux` npm script | 10 min | P1 |
| Add PyInstaller venv path fix | 5 min | P2 — only matters for builds |
| Wayland Playwright flags | 30 min | P2 — headed mode |
| GitHub Actions Linux release | 2 hr | P3 — for automated releases |

### Should You Proceed?

**Yes, proceed.** Here's why:

1. **The linux-migration docs already exist** and are thorough. The `docs/linux-migration/` directory covers every issue I found. You're not starting from zero.

2. **The core architecture is platform-agnostic** — Python + Rust + React are first-class Linux citizens. Only ~8 files have platform-specific code.

3. **The project's value proposition** (local-first, explainable AI job search) is independent of platform. There's nothing Windows-specific about job scraping, scoring, or document generation.

4. **The heavy dependencies** (PyTorch, Kùzu, LanceDB) all have Linux native wheels. Performance may actually be better on Linux due to better memory management.

5. **The security issues** (plaintext API keys) are platform-independent and should be fixed regardless.

### Hyprland-Specific Recommendations

1. **Use XWayland for Tauri initially** — the default. Works fine for testing.
2. **For hi-res displays**, set environment: `GDK_DPI_SCALE=1` or configure Hyprland's `xwayland:use_nearest_neighbor = true`
3. **For Playwright headed mode**, set `--ozone-platform-hint=auto` as a Chromium argument
4. **For system tray**, ensure `libayatana-appindicator` is installed and Hyprland has `dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP`
5. **Disable Ghost Mode** (`ghost_mode=false` in settings) to avoid scheduler issues during testing

### Quick Wins (First Hour)

```bash
# Fix data directory (single edit in db/client.py)
# Change:
_b = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe")
# To:
_b = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "JustHireMe")

# Fix generator.py assets path (same pattern)
# And main.py:658,827 (same pattern)
```

```bash
# Fix browser paths (single edit in browser_runtime.py)
# Add after line 12:
"/usr/bin/google-chrome",
"/usr/bin/chromium",
"/usr/bin/chromium-browser",
```

```bash
# Install all system deps on Arch
sudo pacman -S webkit2gtk-4.1 gtk3 libayatana-appindicator librsvg pango \
               gdk-pixbuf2 libsoup3 cairo dbus openssl base-devel
rustup default stable
```

---

## Appendix: File Inventory of Platform-Sensitive Code

| File | Lines | Platform Sensitivity | Fix Required? |
|------|-------|---------------------|---------------|
| `backend/db/client.py` | 11 | LOCALAPPDATA on Windows | Yes |
| `backend/generator.py` | 10-13 | LOCALAPPDATA on Windows | Yes |
| `backend/main.py` | 658, 827 | LOCALAPPDATA on Windows | Yes |
| `backend/agents/browser_runtime.py` | 8-17 | Windows Chrome paths | Yes |
| `backend/agents/scout.py` | 580 | Windows User-Agent | Optional |
| `backend/backend.spec` | 11 | Windows venv path | Only for builds |
| `src-tauri/tauri.conf.json` | 28 | NSIS-only bundle | For Linux releases |
| `src-tauri/src/lib.rs` | 6, 86-102 | `cfg(windows)` + `taskkill`/`kill` | Already handled |
| `src-tauri/src/main.rs` | 1 | `windows_subsystem` | Already handled |
| `package.json` | 24-28 | Windows packaging scripts | For Linux releases |
| `.github/workflows/release.yml` | entire | Windows-only CI | For Linux releases |
| `scripts/build-sidecar.ps1` | entire | Windows only | Already have `.sh` |
| `scripts/build-sidecar.sh` | entire | Cross-platform | Already exists |
