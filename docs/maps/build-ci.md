# Map: build-ci

**File:** `docs/maps/build-ci.md`
**Codebase path(s):**
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/dependabot.yml`
- `backend/pyproject.toml`
- `package.json`
- `scripts/build-sidecar.sh`
- `scripts/build-sidecar.ps1`
**Files in scope:** 7
**Total lines:** ~822
**Generated:** 2026-05-15

---

## 1. Unit summary

The build-ci unit owns the project's CI/CD pipeline, dependency management automation, build configuration, and sidecar packaging scripts. It defines the CI gates (dependency audit, frontend/backend/Rust checks), the full cross-platform release pipeline (PyInstaller sidecar → Tauri installer → GitHub release with signed updater metadata), Dependabot schedules for all four ecosystems (npm, cargo, pip, GitHub Actions), Python project metadata with test markers, and shell/PowerShell scripts for local sidecar builds. The website CI job was recently removed alongside deletion of the `website/` directory. All Python dependency pins use `>=` (minimum-version only, no upper bounds). The pytest config in pyproject.toml auto-excludes tests marked `external` (2 of 330 backend tests).

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `.github/workflows/ci.yml` | 111 | PR/push CI: dep audit, frontend build+test, backend pytest, Rust cargo check | 🟢 |
| 2 | `.github/workflows/release.yml` | 521 | Tag-pushed release: matrix build (Win/Lin/Mac) of PyInstaller sidecar + Tauri installer + GitHub release with updater metadata | 🟢 |
| 3 | `.github/dependabot.yml` | 25 | Weekly Dependabot for npm, cargo, pip, GitHub Actions — 3 open PRs each | 🟢 |
| 4 | `backend/pyproject.toml` | 43 | Python project metadata, dependencies, dev deps, pytest config with markers | 🟠 |
| 5 | `package.json` | 59 | Frontend npm project, scripts, deps, devDeps, Tauri build scripts | 🟢 |
| 6 | `scripts/build-sidecar.sh` | 34 | Unix shell script for local PyInstaller sidecar build | 🟢 |
| 7 | `scripts/build-sidecar.ps1` | 29 | Windows PowerShell script for local PyInstaller sidecar build | 🟢 |

---

## 3. Detailed breakdown

### `.github/workflows/ci.yml`

**Purpose:** Runs on every push and PR to `main`. Four parallel jobs: dependency audit (npm audit + pip-audit + cargo audit), frontend (typecheck + vitest + vite build), backend (pytest with `-m 'not external'` via pyproject.toml addopts), Rust check (cargo check with Tauri system deps). Uses Node 24, Python 3.13, Rust stable. Concurrency group cancels in-progress runs.

**Jobs:**

| Job | OS | Steps | Purpose | Flag |
|-----|-----|-------|---------|------|
| `dependency-audit` | ubuntu-latest | npm audit, pip-audit, cargo audit | Gate on known vulns | 🟢 |
| `frontend` | ubuntu-latest | npm ci → typecheck → npm test → npm run build | JS/TS correctness | 🟢 |
| `backend` | ubuntu-latest | uv sync → pytest tests/ | Python tests (excludes `external` marker) | 🟢 |
| `rust` | ubuntu-latest | apt deps → cargo check | Rust compilation check | 🟢 |

**Flags:**
- 🟡 SUSPECT — CI backend job runs `pytest tests/ -v` which inherits `addopts = "-m 'not external'"` from pyproject.toml. This excludes 2 of 330 tests. The 2 excluded tests (`test_regressions.py:338`, `test_regressions.py:363`) are marked `@pytest.mark.external`. This means 99.4% of backend tests run — the "45%" claim does not match current state. Historical context: before commit `7dd18c1`, test files `test_ingestion.py` and `test_live_fire.py` were in `tests/` and later moved to `scripts/`, which may have resulted in a lower pass rate.
- 🟢 — `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` set on all jobs to future-proof Node 24 runner compatibility.

---

### `.github/workflows/release.yml`

**Purpose:** Triggered on `v*` tag pushes. Three-phase pipeline:
1. **`build-backend`** — matrix across Windows/Linux/macOS: builds Python sidecar via PyInstaller, installs Playwright Chromium, uploads sidecar and browser runtime artifacts.
2. **`build-tauri`** — needs `build-backend`: downloads sidecar, runs `npm run package:<platform>`, collects installer artifacts (NSIS/AppImage/DMG) + SHA256 checksums + Tauri updater `.sig` files, uploads release assets.
3. **`publish-release`** — needs `build-tauri`: downloads all platform assets, generates combined SHA256SUMS.txt and Tauri updater `latest.json`, publishes GitHub release via `gh release create`.

**Matrix:**

| Name | Platform | OS | Experimental | Package script |
|------|----------|----|--------------|----------------|
| Windows | windows | windows-latest | false | `package:windows` |
| Linux | linux | ubuntu-latest | false | `package:linux` |
| macOS | macos | macos-latest | false | `package:macos` |

**Key details:**
- `fail-fast: false` — all platforms build even if one fails.
- `continue-on-error: ${{ matrix.experimental }}` — currently false for all.
- Tauri updater signing required: `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` must be set or the build fails.
- `NO_STRIP=true` for Linux AppImage to avoid stripping issues.
- macOS: ad-hoc codesign on the sidecar (`codesign --force --sign -`).
- Browser runtime is NOT bundled into installer — shipped as separate OTA asset.
- Release notes generated automatically with platform-specific installation instructions.
- Artifact retention: 1 day.

**Flags:**
- 🟢 — `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` set at workflow level.
- 🟢 — Sidecar verified to exist before Tauri build proceeds.
- 🟠 STALE — `.deb` no longer collected or mentioned in release notes (removed in `dc6e571`). Release only produces `.AppImage` for Linux.

---

### `.github/dependabot.yml`

**Purpose:** Weekly Dependabot updates for 4 ecosystems, each limited to 3 open PRs at a time.

| Ecosystem | Directory | Interval | PR limit |
|-----------|-----------|----------|----------|
| npm | `/` | weekly | 3 |
| cargo | `/src-tauri` | weekly | 3 |
| pip | `/backend` | weekly | 3 |
| github-actions | `/` | weekly | 3 |

**Flags:**
- 🟢 — Standard config, all major ecosystems covered.

---

### `backend/pyproject.toml`

**Purpose:** Python project metadata (v0.1.25, requires-python >=3.13), runtime dependencies, dev dependencies (pyinstaller, pytest), and pytest configuration.

**Dependencies (all use `>=`, no upper bounds):**

| Package | Pin | Flag |
|---------|-----|------|
| fastapi | >=0.136.1 | 🔵 HARDCODED — no upper bound |
| uvicorn[standard] | >=0.46.0 | 🔵 HARDCODED |
| websockets | >=16.0 | 🔵 HARDCODED |
| anthropic | >=0.49.0 | 🔵 HARDCODED |
| openai | >=1.30.0 | 🔵 HARDCODED |
| instructor | >=1.3.0 | 🔵 HARDCODED |
| kuzu | >=0.7.0 | 🔵 HARDCODED |
| lancedb | >=0.17.0 | 🔵 HARDCODED |
| langchain-core | >=1.3.3 | 🔵 HARDCODED |
| langgraph | >=0.2.0 | 🔵 HARDCODED |
| sentence-transformers | >=3.0.0 | 🔵 HARDCODED |
| pypdf | >=4.0.0 | 🔵 HARDCODED |
| playwright | >=1.44.0 | 🔵 HARDCODED |
| html2text | >=2024.2.26 | 🔵 HARDCODED |
| httpx | >=0.27.0 | 🔵 HARDCODED |
| fpdf2 | >=2.7.0 | 🔵 HARDCODED |
| markdown | >=3.6 | 🔵 HARDCODED |
| apscheduler | >=3.10.0 | 🔵 HARDCODED |
| python-multipart | >=0.0.27 | 🔵 HARDCODED |
| tenacity | >=9.1.4 | 🔵 HARDCODED |

**Dev dependencies:**
| Package | Pin | Flag |
|---------|-----|------|
| pyinstaller | >=6.20.0 | 🔵 HARDCODED |
| pytest | >=9.0.3 | 🔵 HARDCODED |

**Pytest config:**
```ini
[tool.pytest.ini_options]
addopts = "-p no:cacheprovider -m 'not external'"
markers = [
    "integration: tests that cross component boundaries",
    "external: tests that write to filesystem or rely on external services",
    "requires_browser: tests that require browser automation",
]
```

**Flags:**
- 🔵 HARDCODED — Every dependency uses `>=` only, no upper bounds, no lockfile checked into repo. Risk of unexpected breakage from major version bumps. Dependabot is the sole governor.
- 🟢 — Pytest markers are well-defined and documented.
- 🟡 SUSPECT — Marker `requires_browser` defined but used by 0 tests. Dead marker definition.

---

### `package.json`

**Purpose:** Frontend npm project (v0.1.25), Vite + React + TypeScript + Tauri. Provides dev, test, build, and platform-specific packaging scripts.

**Scripts:**
| Script | Command | Purpose |
|--------|---------|---------|
| `dev` | `vite` | Dev server |
| `typecheck` | `tsc --noEmit` | TypeScript type checking |
| `test` | `vitest run` | Frontend tests |
| `build` | `tsc && vite build` | Production build |
| `tauri` | `tauri` | Tauri CLI passthrough |
| `package:windows` | `tauri build --bundles nsis` | Windows NSIS installer |
| `package:linux` | `tauri build --bundles appimage` | Linux AppImage |
| `package:macos` | `tauri build --bundles app,dmg` | macOS app bundle + DMG |

All npm dependencies use `^` (caret) ranges. All Tauri packages: `@tauri-apps/api@^2.11.0`, `@tauri-apps/cli@^2`, etc.

**Flags:**
- 🟢 — Standard npm config.
- 🟢 — Platform-specific packaging scripts named consistently with release workflow expectation.

---

### `scripts/build-sidecar.sh`

**Purpose:** Bash script for local Unix sidecar builds. Cleans previous output, runs PyInstaller with `backend.spec`, renames the binary to `jhm-sidecar-<triple>`, makes executable.

**Flow:**
1. `rm -rf src-tauri/resources/backend`
2. `cd backend && uv run pyinstaller backend.spec --distpath ../src-tauri/resources --noconfirm`
3. Detects host triple via `rustc -vV`
4. Moves binary to `src-tauri/resources/backend/jhm-sidecar-<triple>`
5. `chmod +x`

**Flags:**
- 🟢 — Straightforward, matches the release workflow's Unix build step logic.
- 🟢 — Graceful `chmod` failure (`|| true`) for Windows-under-WSL edge case.

---

### `scripts/build-sidecar.ps1`

**Purpose:** PowerShell script for local Windows sidecar builds. Similar flow to bash script but with Windows-specific paths and error handling.

**Flow:**
1. Sets `UV_CACHE_DIR`, `PYTHONNOUSERSITE`, `PYINSTALLER_CONFIG_DIR`, `HF_HOME`
2. Cleans previous output
3. `cd backend && uv run pyinstaller backend.spec --distpath ..\src-tauri\resources\backend --noconfirm --clean`
4. Detects host triple, copies `backend.exe` to `jhm-sidecar-<triple>.exe`
5. Validates output exists

**Flags:**
- 🟢 — Explicit error handling with `$ErrorActionPreference = "Stop"`.
- 🟢 — Sets cache dirs to avoid polluting user profile.
- 🟡 SUSPECT — Script uses `Copy-Item` (leaves original `backend.exe` in output dir), unlike bash script which does `mv`. Not a bug but inconsistent.

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P1 | 🔵 HARDCODED | All Python dep pins use `>=` only | `backend/pyproject.toml:9-28` | No upper bounds on any of 20 runtime deps — risk of unexpected breakage |
| P1 | 🔵 HARDCODED | Dev dep pins `>=` only | `backend/pyproject.toml:33-34` | pyinstaller and pytest also loose-pinned |
| P2 | 🟡 SUSPECT | `requires_browser` marker defined but unused | `backend/pyproject.toml:42` | 0 tests carry this marker; dead config |
| P2 | 🟡 SUSPECT | Sidecar build scripts inconsistent rename | `scripts/build-sidecar.ps1:28` vs `scripts/build-sidecar.sh:30` | .ps1 uses Copy-Item (leaves original), .sh uses mv (removes original) |
| P3 | 🟠 STALE | `.deb` removed from release pipeline | `.github/workflows/release.yml:371-374` | Linux release now AppImage-only; release notes updated accordingly |
| P3 | 🟢 CLEAN | CI runs 99.4% of backend tests (328/330) | `.github/workflows/ci.yml:74` | Only 2 `external`-marked tests excluded via pyproject.toml addopts |
| P3 | 🟢 CLEAN | Website job and directory removed | `.github/workflows/ci.yml:62-78` (deleted) + `website/` dir gone | Confirmed removal in commit `dc6e571` |
| P3 | 🟢 CLEAN | Dependabot covers all 4 ecosystems | `.github/dependabot.yml:3-25` | npm, cargo, pip, github-actions — all weekly, limit 3 each |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- Tauri build process (`src-tauri/tauri.conf.json`) references sidecar binary naming convention
- Backend unit: `backend/pyproject.toml` is the source of truth for Python deps and pytest config
- Frontend unit: `package.json` scripts (`package:linux`, `package:windows`, `package:macos`) are invoked by release workflow

**Outbound (this unit depends on others):**
- Backend unit — CI runs backend tests; release workflow builds backend via PyInstaller
- Frontend unit — CI runs frontend tests and build; release workflow uses Tauri packaging
- Rust unit (`src-tauri/`) — CI runs cargo check; release workflow compiles Tauri installer

**External (third-party services/tools):**

| Dependency | Used for | Version | Flag |
|------------|----------|---------|------|
| actions/checkout@v6 | Checkout code | v6 | 🟢 |
| actions/setup-node@v6 | Node 24 setup | v6 | 🟢 |
| actions/setup-python@v6 | Python 3.13 setup | v6 | 🟢 |
| astral-sh/setup-uv@v8.1.0 | UV package manager | v8.1.0 | 🟢 |
| dtolnay/rust-toolchain@stable | Rust toolchain | stable | 🟢 |
| Swatinem/rust-cache@v2 | Rust cargo cache | v2 | 🟢 |
| actions/upload-artifact@v7 | Pass artifacts between jobs | v7 | 🟢 |
| actions/download-artifact@v8 | Download artifacts | v8 | 🟢 |
| PyInstaller | Bundle Python backend to single binary | >=6.20.0 | 🔵 HARDCODED |
| Playwright | Browser automation for scraping | >=1.44.0 | 🟢 |
| Tauri (v2) | Desktop app framework | ^2 (npm) | 🟢 |

---

## 6. First principles assessment

### `.github/workflows/ci.yml`
1. **Needs to exist?** Yes — defines CI gates.
2. **Does what it claims?** Yes — audits dependencies, runs tests, checks Rust compilation.
3. **Right place?** Yes — standard GitHub Actions location.
4. **What would break if deleted?** No CI enforcement on PRs/pushes.

### `.github/workflows/release.yml`
1. **Needs to exist?** Yes — automates cross-platform release.
2. **Does what it claims?** Yes — builds sidecar, Tauri installer, publishes GitHub release with updater metadata.
3. **Right place?** Yes.
4. **What would break if deleted?** No automated releases; must build manually.

### `.github/dependabot.yml`
1. **Needs to exist?** Yes — automates dependency updates.
2. **Does what it claims?** Yes — covers all 4 ecosystems.
3. **Right place?** Yes.
4. **What would break if deleted?** Dependencies go stale until manually updated.

### `backend/pyproject.toml`
1. **Needs to exist?** Yes — Python project metadata and build config.
2. **Does what it claims?** Yes — defines project, deps, test config.
3. **Right place?** Yes — standard Python location.
4. **What would break if deleted?** Cannot install or test the backend.

### `package.json`
1. **Needs to exist?** Yes — frontend project metadata.
2. **Does what it claims?** Yes — defines scripts, deps, Tauri build commands.
3. **Right place?** Yes — standard.
4. **What would break if deleted?** Cannot build or develop frontend.

### `scripts/build-sidecar.sh`
1. **Needs to exist?** Partially — release workflow has equivalent inline steps; this is a convenience for local development.
2. **Does what it claims?** Yes — builds sidecar locally.
3. **Right place?** Yes — scripts/ directory.
4. **What would break if deleted?** Developers lose a convenience script but CI/release workflows still work.

### `scripts/build-sidecar.ps1`
1. **Needs to exist?** Partially — same reasoning as shell variant.
2. **Does what it claims?** Yes.
3. **Right place?** Yes.
4. **What would break if deleted?** Windows developers lose local build convenience script.
