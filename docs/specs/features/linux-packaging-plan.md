# Linux Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add deb Linux package format alongside existing AppImage, with launcher integration and release documentation.

**Architecture:** Straightforward Tauri config changes + static resource files + npm script additions. No runtime code changes.

**Tech Stack:** Tauri 2 bundle config, freedesktop.org `.desktop` spec, npm scripts

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src-tauri/tauri.conf.json` | Modify | Keep `["appimage"]` targets, add linux block with deb depends |
| `resources/JustHireMe.desktop` | Create | Freedesktop-compliant desktop entry (reference — Tauri auto-generates for packages) |
| `package.json` | Modify | Add `package:appimage`, `package:deb`, `package:linux:all` scripts |
| `docs/linux-release.md` | Create | Release checklist mirroring `docs/windows-release.md` structure |

---

### Task 1: Update `tauri.conf.json` bundle config

**Files:**
- Modify: `src-tauri/tauri.conf.json:50-54`

- [ ] **Keep `targets` as `["appimage"]`**

Tauri 2 config-level `targets` doesn't accept multi-format arrays. The config stays:
```json
    "targets": ["appimage"],
```
CLI `--bundles` flag overrides this for per-format builds (handled by npm scripts in Task 4).

- [ ] **Add `linux` block with deb depends**

Add after the `"windows"` block (after line 48 `}`), before the `"targets"` line:
```json
    "linux": {
      "deb": {
        "depends": [
          "libgtk-3-0",
          "libwebkit2gtk-4.1-0",
          "libappindicator3-1",
          "librsvg2-2",
          "libssl3",
          "libjavascriptcoregtk-4.1-0"
        ]
      }
    },
```

Note: Tauri v2 auto-generates the `.desktop` file for deb/AppImage — no custom template or `files` config needed.

- [ ] **Verify the config**

```bash
python3 -c "import json; json.load(open('src-tauri/tauri.conf.json')); print('valid')"
```
Expected: `valid`

---

### Task 2: Create `.desktop` file (reference resource)

**Files:**
- Create: `resources/JustHireMe.desktop`

Tauri 2 auto-generates the `.desktop` file for deb/AppImage packages. This file is kept as a reference for manual installs or future use.

- [ ] **Create the desktop entry file**

Write `resources/JustHireMe.desktop`:
```desktop
[Desktop Entry]
Type=Application
Name=JustHireMe
Comment=Local-first AI job intelligence workbench
Exec=justhireme
Icon=justhireme
Terminal=false
Categories=Office;
StartupNotify=true
```

- [ ] **Validate the desktop file syntax**

```bash
desktop-file-validate resources/JustHireMe.desktop
```
Expected: No output (valid)

Install validator if missing: `sudo pacman -S desktop-file-utils` (Arch) or `sudo apt install desktop-file-utils` (Debian/Ubuntu).

---

### Task 3: Verify icons (no action expected)

**Files:**
- Verify: `src-tauri/icons/icon.png`

- [ ] **Step 1: Confirm icon.png is 512x512 or larger**

Run:
```bash
file src-tauri/icons/icon.png
python3 -c "from PIL import Image; img = Image.open('src-tauri/icons/icon.png'); print(f'{img.size[0]}x{img.size[1]}')"
```

Expected: 512x512 or larger. Tauri scales down for AppImage's 256x256 requirement. If PIL not available, `file` output showing PNG dimensions is sufficient.

If icon is smaller than 256x256, we'd need a new icon — but the existing 14183-byte `icon.png` is almost certainly 512x512 (standard Tauri init size).

---

### Task 4: Add npm scripts

**Files:**
- Modify: `package.json:28`

- [x] **Step 1: Add Linux packaging scripts to package.json**

Edit `package.json` — after line 28 (`"package:linux": "tauri build --bundles appimage"`), add:
```json
    "package:appimage": "tauri build --bundles appimage",
    "package:deb": "tauri build --bundles deb",
    "package:linux:all": "tauri build --bundles appimage,deb",
```

Note: Tauri 2 does not support `tar.gz` (removed). rpm deferred — no local rpmbuild tooling.

The `package:linux` script is unchanged (AppImage-only for backward compat).

- [ ] **Step 2: Verify scripts parse**

Run: `node -e "const p = require('./package.json'); Object.entries(p.scripts).filter(([k]) => k.startsWith('package:')).forEach(([k,v]) => console.log(k, '→', v))"`
Expected: All 10 package:* scripts listed including the 3 new ones.

---

### Task 5: Create release documentation

**Files:**
- Create: `docs/linux-release.md`

- [ ] **Step 1: Write linux-release.md**

Write `docs/linux-release.md`:
```markdown
# Linux Release Checklist

## Prerequisites

- Arch Linux (or Debian/Ubuntu for deb builds)
- Rust toolchain, Node.js 20+, Python 3.13+
- System deps: `webkit2gtk-4.1`, `gtk3`, `libayatana-appindicator`, etc.
- Sidecar built: `scripts/build-sidecar.sh`

## Build

```bash
npm install
cd backend
uv sync --dev
cd ..
./scripts/build-sidecar.sh
```

### Individual formats

```bash
# AppImage (portable, single-file)
npm run package:appimage

# Debian/Ubuntu package
npm run package:deb

# tar.gz archive (other distros)
npm run package:tarball
```

### All formats at once

```bash
npm run package:linux:all
```

### Fast local smoke test (no bundle)

```bash
npm run package:fast
./src-tauri/target/release/justhireme
```

## Artifacts

| Format | Path | Use case |
|--------|------|----------|
| AppImage | `src-tauri/target/release/bundle/appimage/JustHireMe_<version>_x86_64.AppImage` | Portable — run anywhere with FUSE |
| deb | `src-tauri/target/release/bundle/deb/justhireme_<version>_amd64.deb` | Debian/Ubuntu install |
| tar.gz | `src-tauri/target/release/bundle/tar.gz/justhireme_<version>_amd64.tar.gz` | Manual install on other distros |

## Smoke Test

- Launch AppImage: `chmod +x ./JustHireMe*.AppImage && ./JustHireMe*.AppImage`
- Install deb: `sudo dpkg -i justhireme_*.deb && justhireme`
- Verify app appears in system launcher (after deb install)
- Verify backend starts and WebSocket connects
- Run a scan cycle

## Verification

```bash
# Check deb dependencies
dpkg -I src-tauri/target/release/bundle/deb/justhireme_*.deb | grep Depends

# Validate desktop file (if installed)
desktop-file-validate /usr/share/applications/justhireme.desktop

# Generate checksums
cd src-tauri/target/release/bundle
sha256sum appimage/*.AppImage deb/*.deb tar.gz/*.tar.gz > SHA256SUMS.txt
```

## Notes

- AppImage requires FUSE2 or FUSE3 at runtime
- deb package registers the app in the system launcher automatically
- The `package:linux` script (AppImage-only) is maintained for backward compatibility — use `package:linux:all` for comprehensive builds
- CI release builds are not yet automated (see Phase 4)
```

- [ ] **Step 2: Verify rendering**

Run: `head -5 docs/linux-release.md`
Expected: Shows markdown header

---

## Validation Checklist

After all tasks are complete, verify:

- [ ] `npm run package:appimage` produces `.AppImage` (verify path exists)
- [ ] `npm run package:deb` produces `.deb` (verify path exists)
- [ ] `npm run package:appimage` produces `.AppImage` (verify path exists)
- [ ] `npm run package:linux` still works (backward compat)
- [ ] `.desktop` file validates with `desktop-file-validate`
- [ ] `tauri.conf.json` passes JSON validation
- [ ] All changes on `feature/linux-packaging` branch (no unrelated files)
