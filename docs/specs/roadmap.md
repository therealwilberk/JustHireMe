# Roadmap

> **Living document.** Update phase status as work progresses.
> Agent: use this file to understand sequencing and scope. Never work ahead of the current active phase
> without explicit instruction. Each phase becomes a feature spec before implementation begins.

---

## Roadmap Philosophy

- Phases are **sequential by default** — complete and validate one before starting the next
- Each phase maps to one or more feature specs in `specs/features/`
- A phase is **done** when its validation checklist passes, not when code is written
- Scope changes must be reflected here before the agent acts on them

---

## Project Status

| Field | Value |
|-------|-------|
| Current phase | `Phase 2 — Stability` |
| Phase started | `2026-05-09` |
| Last updated | `2026-05-10` |
| Overall status | `[ ] Not started / [x] In progress / [ ] Paused / [ ] Complete` |

---

## Phase Overview

| # | Phase | Status | Feature Spec |
|---|-------|--------|--------------|
| 1 | Foundation — XDG paths, browser paths, build working on Arch | `[x] Complete` | `specs/features/foundation.md` — `[x] Done` |
| 2 | Stability — startup validation, logging, error handling, test infrastructure | `[x] Complete` | `specs/features/stability.md` — `[x] Done` |
| 3 | Linux Packaging — AppImage/deb, npm scripts, setup docs | `[ ] Pending` | `specs/features/linux-packaging.md` — `[ ] Not created` |
| 4 | Polish — Hyprland/Wayland, system tray, HiDPI, Linux CI | `[ ] Pending` | `specs/features/polish.md` — `[ ] Not created` |

---

## Phase Details

---

### Phase 1 — Foundation

**Goal:** JustHireMe builds and runs on Arch Linux + Hyprland with core features accessible via the UI.

**Scope:**
- Fix data storage paths to XDG Base Directory compliance (`~/.local/share/JustHireMe/`)
- Add Linux browser binary paths to `browser_runtime.py`
- Fix PyInstaller sidecar spec for Linux venv path
- Add `package:linux` npm script and Linux bundle targets to Tauri config
- Verify `npm run tauri dev` succeeds end-to-end on Arch
- Verify backend starts, frontend connects, and basic scan cycle works

**Out of scope for this phase:**
- Structured logging improvements (Phase 2)
- Startup validation (Phase 2)
- Release CI (Phase 4)

**Dependencies:** Rust toolchain, Node.js 20+, Python 3.13+, system deps (webkit2gtk, gtk3, etc.)

**Validation:**
- [ ] `npm run tauri dev` succeeds — app window opens on Hyprland
- [ ] Data dir resolves to `~/.local/share/JustHireMe/` on Linux
- [ ] Backend starts, WebSocket connects, scan cycle runs without errors
- [ ] `npm run package:fast` produces a working binary (no bundle)

**Feature spec:** `specs/features/foundation.md` — `[x] Done`

**Status:** `[x] Complete`

> Phase 1 scope expanded during implementation: AppImage target, `package:linux` script, and PyInstaller fix were pulled forward from Phase 2/3. Test refactoring deferred to Phase 2 assessment.

---

### Phase 2 — Stability

**Goal:** Backend is reliable, debuggable, and testable. Errors surface clearly, logging is structured, and tests are maintainable.

**Scope (finalized — see `specs/features/stability.md`):**
- Test infrastructure cleanup: extract shared fakes into `tests/fakes.py`, remove global `os.makedirs` monkey-patch, add unit tests for `data_base()` and `chromium_executable()`
- Startup validation: enhance `/health` endpoint to probe DB writability, browser availability, API key presence
- Sidecar port/token timeout: add `tokio::time::timeout` in Rust, retry ceiling in frontend polling
- Ghost mode concurrency lock: prevent `_ghost_tick()` from racing with manual scans via `asyncio.Lock`
- Print/logging: confirmed clean at 0 `print()` calls in prod code — no action needed

**Out of scope for this phase:**
- Linux packaging/distribution (Phase 3)
- Wayland-specific rendering tweaks (Phase 4)
- Full test coverage for all agents (separate effort)

**Dependencies:** Phase 1 complete

**Validation:**
See validation checklist in `specs/features/stability.md#8-validation-checklist`

**Feature spec:** `specs/features/stability.md` — `[x] Done`

**Status:** `[x] Complete` (verified by third-party audit — all 8 tasks match spec, 128 tests pass)

---

### Phase 3 — Linux Packaging

**Goal:** Linux users can install JustHireMe via standard package formats (AppImage/deb) with documented setup.

**Scope:**
- Add AppImage and deb targets to `tauri.conf.json`
- Create Linux-appropriate `.desktop` file and icons
- Add `package:linux` npm script
- Write `docs/linux-release.md` with build and distribution instructions
- Update `README.md` with Linux system dependencies and setup steps
- Add Linux build verification to `CONTRIBUTING.md`

**Out of scope for this phase:**
- Automated Linux release CI (Phase 4)
- AUR package or distribution as community package

**Dependencies:** Phase 1 + 2 complete (sidecar must build for bundles to work)

**Validation:**
- [ ] `npm run package:linux` produces valid `.AppImage` and `.deb`
- [ ] Installed app launches, tray icon works, core features functional
- [ ] README has complete Linux setup instructions including system deps
- [ ] `docs/linux-release.md` documents the release process

**Feature spec:** `specs/features/linux-packaging.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

### Phase 4 — Polish

**Goal:** JustHireMe feels native on Hyprland/Wayland. Linux releases are automated via CI.

**Scope:**
- Test and document system tray under Hyprland (`libayatana-appindicator`)
- Handle HiDPI scaling (Hyprland configuration notes, `GDK_DPI_SCALE`)
- Test Playwright headed mode with Wayland flags (`--ozone-platform-hint=auto`)
- Add GitHub Actions workflow for Linux release builds
- Document known Hyprland-specific quirks in `docs/known-issues.md`
- Rebase `linux-base` on latest upstream `main` and resolve conflicts

**Out of scope for this phase:**
- Native Wayland rendering (requires GTK4/Tauri 3 — upstream concern)
- KE-specific scrapers (separate project)

**Dependencies:** Phase 3 complete

**Validation:**
- [ ] System tray icon appears and functions on Hyprland
- [ ] App renders correctly on HiDPI displays (no blurry text/scaling)
- [ ] GitHub Actions builds and publishes Linux releases
- [ ] Fork can rebase on latest upstream without major conflicts

**Feature spec:** `specs/features/polish.md` — `[ ] Not created`

**Status:** `[ ] Pending`

---

## Deferred / Backlog

| Item | Notes | Why deferred |
|------|-------|--------------|
| KE-specific scrapers (BrighterMonday, etc.) | Being developed in separate repo | Separate project, not part of fork |
| API key encryption | **SECURITY CRITICAL:** Docs claim AES-256 / Windows DPAPI but keys stored in plaintext in SQLite `settings` table (`project.md`, `SPEC.md`, `ARCHITECTURE.md` all contradict reality). Raised as upstream issue. | Upstream concern — fork will adopt upstream fix when available |
| Placeholder data in `generator.py:536` | LLM prompt template has real-ish example phone (`+91-XXXXXXXXXX`). Minor. | Low priority — can fix alongside any feature work |
| Loose dependency pins (`>=` in `pyproject.toml`) | Risk of unexpected breaking changes on `uv sync`. `uv.lock` mitigates for dev. | Low priority — pinned versions would improve reproducibility |
| Upstream tracking | Rebase `linux-base` onto `main` when upstream has meaningful updates | Ongoing background task, not a phase |

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-09 | Initial roadmap drafted | Constitution init |
| 2026-05-10 | Phase 2 feature spec drafted | Phase 2 research complete — scope finalized |
| 2026-05-10 | Phase 2 implementation complete | All 8 tasks done: test fakes extracted, path unit tests added, /health enhanced, sidecar timeout + retry ceiling added, ghost lock implemented. 128 tests pass, verified by third-party audit. |
| 2026-05-10 | Audit flags: plaintext API keys, placeholder data, loose deps | Phase 2 audit revealed 3 cross-cutting issues outside scope — documented in Deferred/Backlog. API key issue raised to upstream. |

---

*Last updated: 2026-05-09 — Agent*
