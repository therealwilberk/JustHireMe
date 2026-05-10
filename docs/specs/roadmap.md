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
| Last updated | `2026-05-09` |
| Overall status | `[ ] Not started / [ ] In progress / [~] Paused / [ ] Complete` |

---

## Phase Overview

| # | Phase | Status | Feature Spec |
|---|-------|--------|--------------|
| 1 | Foundation — XDG paths, browser paths, build working on Arch | `[x] Complete` | `specs/features/foundation.md` — `[x] Done` |
| 2 | Stability — startup validation, logging, error handling, test infrastructure | `[~] Active` | `specs/features/stability.md` — `[ ] Not created` |
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

**Scope (tentative — being defined):**
- Test infrastructure cleanup: extract shared fakes, remove global monkey-patches
- Startup validation: DB writability, browser availability, API key presence
- Replace `print()` with structured logging
- Fix fragile stdout-based port discovery
- Add ghost mode concurrency lock

**Out of scope for this phase:**
- Linux packaging/distribution (Phase 3)
- Wayland-specific rendering tweaks (Phase 4)
- Full test coverage for all agents (separate effort)

**Dependencies:** Phase 1 complete

**Validation:**
TODO — being defined in feature spec

**Feature spec:** `specs/features/stability.md` — `[ ] Being drafted`

**Status:** `[~] Being defined — deep research in progress`

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
| OS keychain for API keys | Upstream hasn't built it either | No point diverging until upstream does it |
| Upstream tracking | Rebase `linux-base` onto `main` when upstream has meaningful updates | Ongoing background task, not a phase |

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-09 | Initial roadmap drafted | Constitution init |

---

*Last updated: 2026-05-09 — Agent*
