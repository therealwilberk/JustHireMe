# Feature Spec — Phase 3: Linux Packaging

> Written before any code. Source of truth for scope, requirements, and validation.
> Agent: do not begin implementation until this file is approved.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | Linux Packaging — AppImage, deb, tar.gz |
| Roadmap phase | Phase 3 |
| Branch | `feature/linux-packaging` |
| Status | `[x] Draft / [ ] Approved / [ ] In Progress / [ ] Done` |
| Depends on | Phase 1 + Phase 2 complete |
| Created | 2026-05-10 |
| Last updated | 2026-05-10 |

---

## 1. Goal

Linux users can install JustHireMe via standard package formats. A developer can run `npm run package:linux:all` and produce AppImage (portable), `.deb` (Debian/Ubuntu), and `.tar.gz` (other distros) artifacts. The app appears in the system launcher with a proper `.desktop` file and icon. The release pipeline builds Linux packages alongside Windows.

---

## 2. Background & Context

Phase 1 already seeded several packaging pieces:
- `package:linux` script added (`tauri build --bundles appimage`)
- `tauri.conf.json` bundle targets changed from `["nsis"]` to `["appimage"]`
- `scripts/build-sidecar.sh` works on Linux
- Sidecar binary already built locally (`jhm-sidecar-x86_64-unknown-linux-gnu`, 229MB)
- GitHub Actions `release.yml` already has a Linux build matrix entry

However, three gaps remain:

1. **Only AppImage is configured** — `package:linux` builds `--bundles appimage` only. No deb or tar.gz.
2. **No `.desktop` file** — the app won't appear in launcher menus after install. Required for proper `.deb` packaging.
3. **No Linux icons** — AppImage requires a 256x256 PNG, and the deb bundle expects standard icon paths.
4. **No linux bundle config in tauri.conf.json** — deb package dependencies, AppImage config, and desktopTemplate are not set.
5. **No `docs/linux-release.md`** — the release checklist doc doesn't exist yet.

The `release.yml` expects `.deb` and `.AppImage` on Linux (line 367), but `package:linux` only builds AppImage — so the existing CI would fail to find artifacts.

---

## 3. Scope

### In scope

- [ ] Update `tauri.conf.json` bundle targets to `["appimage", "deb", "tar.gz"]`
- [ ] Add Linux-specific bundle config to `tauri.conf.json` (deb depends, AppImage config, desktopTemplate)
- [ ] Create `resources/JustHireMe.desktop` — desktop entry file
- [ ] (No icon changes needed — `icon.png` is 512x512, Tauri scales for AppImage)
- [ ] Add npm scripts: `package:deb`, `package:tarball`, `package:linux:all`
- [ ] Create `docs/linux-release.md` — release checklist for Linux builds

### Out of scope

- GitHub Actions Linux release CI job (deferred to Phase 4 or later)
- README.md Linux installation section (separate task)
- Wayland/Hyprland rendering tweaks (Phase 4)
- System tray configuration (Phase 4)
- AUR package or community distribution

---

## 4. Requirements

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | `npm run package:linux:all` produces `.AppImage`, `.deb`, and `.tar.gz` | `Must` |
| F2 | `npm run package:appimage` produces AppImage | `Must` |
| F3 | `npm run package:deb` produces `.deb` | `Must` |
| F4 | `npm run package:tarball` produces `.tar.gz` | `Must` |
| F5 | Installed `.deb` registers app in system launcher via `.desktop` file | `Must` |
| F6 | AppImage includes launcher integration metadata | `Should` |
| F7 | `docs/linux-release.md` documents the full release process | `Must` |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | Existing Windows packaging is unchanged | No regressions on existing workflows |
| NF2 | Backward-compatible `package:linux` alias | Existing `package:linux` either remains AppImage-only or delegates to `package:linux:all` |
| NF3 | deb package declares correct system dependencies | Depends list prevents missing-lib errors on install |
| NF4 | AppImage runs on Ubuntu 22.04+ and Arch | FUSE2 or FUSE3 required at runtime |

---

## 5. Implementation Plan

### Task 1 — Update `tauri.conf.json` bundle config

**File:** `src-tauri/tauri.conf.json`

Changes:
- Change `"targets": ["appimage"]` to `"targets": ["appimage", "deb", "tar.gz"]`
- Add `linux` block with deb depends and desktopTemplate path:

```json
"linux": {
  "deb": {
    "depends": [
      "libgtk-3-0",
      "libwebkit2gtk-4.1-0",
      "libappindicator3-1",
      "librsvg2-2",
      "libssl3",
      "libxdo0"
    ]
  }
}
```

Point `desktopTemplate` at the new `.desktop` file.

### Task 2 — Create `.desktop` file

**File:** `resources/JustHireMe.desktop`

Standard desktop entry referencing the installed binary and icon. Use `%k` for exec path so it works with both AppImage (relative) and deb (absolute).

### Task 3 — Verify icons (no action expected)

`icon.png` is already 512x512 — Tauri scales it down for AppImage's 256x256 requirement. `32x32.png`, `128x128.png`, `128x128@2x.png` all exist. No new icon files needed unless the build warns about a missing size.

### Task 4 — Add npm scripts

**File:** `package.json`

Add:
- `"package:deb": "tauri build --bundles deb"`
- `"package:tarball": "tauri build --bundles tar.gz"`
- `"package:linux:all": "tauri build --bundles appimage,deb,tar.gz"`

Decide: keep `package:linux` as-is (AppImage-only, backward compat) or point it at `package:linux:all`.

### Task 5 — Create release documentation

**File:** `docs/linux-release.md`

Structure mirroring `docs/windows-release.md`:
- Pre-release checklist
- Build commands
- Verification steps
- Checksum generation
- Upload instructions

### Task order

Tasks 1–4 are independent. Task 5 is last (documents the complete process).

---

## 6. API / Interface Design

No API changes. This is entirely packaging config, static resources, and npm scripts.

---

## 7. Error Handling Map

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| deb build fails due to missing deps | Build exits with error + apt-get hint | By cargo/tauri | "Run sudo apt-get install ..." |
| AppImage missing 256x256 icon | Tauri build warns or fails | By tauri CLI | "Missing icon size 256x256 for AppImage" |
| `.desktop` file has syntax error | Package builds but launcher entry broken | N/A | N/A — caught in review |
| `package:linux:all` partially fails | Tauri CLI shows partial build failure | By cargo/tauri | Per-package error message |

---

## 8. Validation Checklist

### Build verification

- [ ] `npm run package:appimage` produces `.AppImage` in `src-tauri/target/release/bundle/appimage/`
- [ ] `npm run package:deb` produces `.deb` in `src-tauri/target/release/bundle/deb/`
- [ ] `npm run package:tarball` produces `.tar.gz` in `src-tauri/target/release/bundle/tar.gz/`
- [ ] `npm run package:linux:all` produces all three formats
- [ ] `npm run package:linux` still works (backward compat check)
- [ ] `.desktop` file validates with `desktop-file-validate`
- [ ] deb declares correct depends: `dpkg -I justhireme_x64.deb | grep Depends`

### Manual install test

- [ ] AppImage launches on Arch: `chmod +x ./JustHireMe*.AppImage && ./JustHireMe*.AppImage`
- [ ] deb installs on Ubuntu: `sudo dpkg -i justhireme_x64.deb`
- [ ] App appears in application launcher after deb install
- [ ] App runs after deb install (backend sidecar included)

### Code quality gates

- [ ] `tauri.conf.json` validates against Tauri 2 schema
- [ ] No Windows packaging broken (verify CI would still produce NSIS)
- [ ] `.desktop` file follows [freedesktop.org spec](https://specifications.freedesktop.org/desktop-entry-spec/latest/)
- [ ] All new files committed on `feature/linux-packaging` branch
- [ ] Branch is clean — no unrelated changes

---

## 9. Ripple Effects

### Task 1 — tauri.conf.json bundle config

| File | Nature of change | Cascade |
|------|------------------|---------|
| `src-tauri/tauri.conf.json` | Add `deb`, `tar.gz` targets, linux block, desktopTemplate | ⚠️ CI `release.yml` line 367 now finds actual artifacts instead of potentially empty glob |
| `src-tauri/tauri.conf.json` | Linux deb depends | Must match Ubuntu 22.04 package names (CI runs on ubuntu-latest) |

### Task 2 — .desktop file

| File | Nature of change | Cascade |
|------|------------------|---------|
| `resources/JustHireMe.desktop` | NEW | Referenced by `tauri.conf.json` `linux.desktopTemplate`. Tauri processes this into the bundle. |
| `src-tauri/icons/` | Must have 256x256 icon | Tauri uses this for the launcher icon in the `.desktop` file |

### Task 3 — Icons (already sufficient)

| File | Nature of change | Cascade |
|------|------------------|---------|
| `src-tauri/icons/icon.png` | Already exists at 512x512 | Tauri scales to 256x256 for AppImage automatically. No action needed. |

### Task 4 — npm scripts

| File | Nature of change | Cascade |
|------|------------------|---------|
| `package.json` | Add 3 new scripts | No cascade — purely additive. Existing `package:linux` unchanged. |
| CI `release.yml` | Future | When Phase 4 adds Linux CI, the scripts are already in place |

### Task 5 — Release docs

| File | Nature of change | Cascade |
|------|------------------|---------|
| `docs/linux-release.md` | NEW | Referenced by `docs/linux-migration/` index and roadmap. No code impact. |

---

## 10. Open Questions

| # | Question | Raised by | Status |
|---|----------|-----------|--------|
| Q1 | Should `package:linux` (existing script) stay AppImage-only (backward compat), or delegate to `package:linux:all`? | Agent | `[ ] Open` — Recommendation: keep AppImage-only, since existing CI/tutorials reference this script. `package:linux:all` is the new comprehensive command. |

## 11. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-10 | All three formats (AppImage, deb, tar.gz) | Covers all Linux users, CI already expects deb | AppImage-only (too narrow) |
| 2026-05-10 | GitHub Actions CI deferred | Not blocking — can add later when release process is tested | Adding now (would delay Phase 3) |
| 2026-05-10 | `.desktop` file as Tauri template | Clean integration, Tauri handles install paths | Manual placement (fragile) |

---

*Last updated: 2026-05-10 — Agent*
