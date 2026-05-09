# Future Work

## Overview

This document outlines planned improvements for JustHireMe on Linux/Arch/Hyprland.

## 10.1 Linux Packaging

### 10.1.1 Add Linux Targets to Tauri Config

**File:** `src-tauri/tauri.conf.json`

**Current state (line 28):**
```json
"bundle": {
  "targets": ["nsis"],  // Windows-only!
  "externalBin": ["resources/backend/backend"],
  "resources": ["resources/bin/**/*"]
}
```

**Recommended addition:**
```json
"bundle": {
  "targets": ["nsis", "deb", "AppImage", "tar.gz"],
  "externalBin": ["resources/backend/backend"],
  "resources": ["resources/bin/**/*"],
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
    },
    "appimage": {
      "bundleMediaPackager": true
    }
  }
}
```

**Note:** Package names above are Debian/Ubuntu format. For Arch, the `depends` field isn't used (Arch packages are different).

---

### 10.1.2 Create Linux Package Scripts

**File:** `package.json`

**Current scripts (Windows-only):**
```json
"scripts": {
  "package:windows": "tauri build --bundles nsis",
  "package:windows:all": "tauri build --bundles nsis msi",
  "package:windows:msi": "tauri build --bundles msi",
  "package:fast": "tauri build --no-bundle"
}
```

**Recommended addition:**
```json
"scripts": {
  "package:linux": "tauri build --bundles deb tar.gz",
  "package:appimage": "tauri build --bundles appimage",
  "package:deb": "tauri build --bundles deb",
  "package:tarball": "tauri build --bundles tar.gz",
  "package:windows": "tauri build --bundles nsis",
  "package:windows:all": "tauri build --bundles nsis msi",
  "package:windows:msi": "tauri build --bundles msi",
  "package:fast": "tauri build --no-bundle"
}
```

**Usage:**
```bash
# Build Linux packages
npm run package:linux      # Build deb + tar.gz
npm run package:appimage   # Build AppImage
npm run package:deb        # Build deb only

# Build for all platforms (requires cross-compilation setup)
npm run package:all        # Windows + Linux packages
```

---

### 10.1.3 Create `.desktop` File

**Create:** `resources/JustHireMe.desktop`

```ini
[Desktop Entry]
Name=JustHireMe
Comment=Local-first AI job intelligence workbench
Exec=/usr/bin/justhireme
Icon=/usr/share/icons/hicolor/256x256/apps/justhireme.png
Terminal=false
Type=Application
Categories=Office;Utility;
StartupNotify=true
StartupWMClass=JustHireMe
```

**Include in Tauri bundle:**
Add to `tauri.conf.json`:
```json
"bundle": {
  "linux": {
    "desktopTemplate": "./resources/JustHireMe.desktop"
  }
}
```

---

## 10.2 GitHub Actions for Linux Releases

### 10.2.1 Add Linux Build Job to Release Workflow

**File:** `.github/workflows/release.yml`

**Current state:** Only builds Windows (see `docs/windows-release.md`).

**Recommended addition:**

```yaml
build-tauri-linux:
  name: Build Linux
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6

    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y \
          build-essential curl file \
          libayatana-appindicator3-dev \
          libglib2.0-dev libgtk-3-dev \
          librsvg2-dev libssl-dev \
          libwebkit2gtk-4.1-dev \
          libxdo-dev pkg-config patchelf wget

    - uses: dtolnay/rust-toolchain@stable

    - uses: actions/setup-node@v6
      with:
        node-version: '24'
        cache: npm

    - uses: astral-sh/setup-uv@v8

    - name: Install frontend dependencies
      run: npm ci

    - name: Install backend dependencies
      run: cd backend && uv sync --dev

    - name: Build backend sidecar
      run: ./scripts/build-sidecar.sh

    - name: Build Tauri (Linux packages)
      run: npm run package:linux
      env:
        TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
        TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}

    - name: Generate checksums
      run: |
        cd src-tauri/target/release/bundle/
        sha256sum **/* > SHA256SUMS.txt

    - name: Upload Linux artifacts
      uses: actions/upload-artifact@v4
      with:
        name: JustHireMe-Linux
        path: src-tauri/target/release/bundle/

  # Then update the release job to include Linux artifacts
```

---

### 10.2.2 Create Linux Release in GitHub

**Update release job to include Linux:**

```yaml
create-release:
  name: Create Release
  needs: [build-tauri-windows, build-tauri-linux]  # Add Linux dependency
  runs-on: ubuntu-latest
  steps:
    - uses: actions/download-artifact@v4
      with:
        name: JustHireMe-Windows
        path: artifacts/windows/

    - uses: actions/download-artifact@v4
      with:
        name: JustHireMe-Linux
        path: artifacts/linux/

    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          artifacts/windows/**/*
          artifacts/linux/**/*
        body: |
          ## JustHireMe v${{ needs.get-version.outputs.version }}
          
          ### Downloads
          - **Windows:** `JustHireMe_x64-setup.exe`
          - **Linux (deb):** `justhireme_x64.deb`
          - **Linux (AppImage):** `JustHireMe_x64.AppImage`
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 10.3 Wayland Native Support

### 10.3.1 Test with `GDK_BACKEND=wayland`

**Current state:** Tauri uses GTK3 which runs via XWayland by default.

**To test native Wayland:**
```bash
export GDK_BACKEND=wayland
npm run tauri dev
```

**Potential issues:**
- GTK3 has limited Wayland support
- System tray may not work
- Scaling may be different

---

### 10.3.2 Consider Migration to GTK4 (Long-term)

**Benefit:** Better native Wayland support

**Challenges:**
- Tauri 2 currently uses GTK3
- Requires changes to Tauri's Linux backend
- May break compatibility with some Linux distributions

**Recommendation:** Wait for Tauri 3 or official GTK4 support.

---

## 10.4 Documentation

### 10.4.1 Create `docs/linux-release.md`

**Mirroring `docs/windows-release.md`, create Linux-specific release documentation.**

**Outline:**
```markdown
# Linux Release Checklist

## Pre-Release
- [ ] Update version in `src-tauri/tauri.conf.json`
- [ ] Update version in `package.json`
- [ ] Test on clean Arch VM
- [ ] Test on Ubuntu/Debian
- [ ] Test on Fedora

## Build
- [ ] Run `npm run package:linux`
- [ ] Verify .deb package
- [ ] Verify AppImage
- [ ] Generate SHA256 checksums

## Release
- [ ] Create GitHub release
- [ ] Upload Linux artifacts
- [ ] Update website with Linux download links
- [ ] Announce on social media
```

---

### 10.4.2 Update `README.md` with Linux Instructions

**Add section:**
```markdown
## Linux Installation

### Prerequisites
- Arch: see [Arch requirements](docs/linux-migration/03-arch-hyprland-requirements.md)
- Ubuntu/Debian: `sudo apt install ...`
- Fedora: `sudo dnf install ...`

### Quick Start (Developers)
```bash
git clone https://github.com/vasu-devs/JustHireMe.git
cd JustHireMe
npm install
cd backend && uv sync --dev && cd ..
npm run tauri dev
```

### Download Release
- [JustHireMe_x64.deb](releases/latest) (Debian/Ubuntu)
- [JustHireMe_x64.AppImage](releases/latest) (Portable)
- [JustHireMe_x64.tar.gz](releases/latest) (Other)
```

---

### 10.4.3 Create Video Walkthrough

**Topics to cover:**
1. Installing dependencies on Arch
2. Setting up Rust, Node, Python
3. Cloning and building JustHireMe
4. First run and configuration
5. Troubleshooting common issues

---

## 10.5 Code Improvements (Future PRs)

### 10.5.1 Better Error Messages in `lib.rs`

**Improve sidecar spawn errors:**
```rust
match sidecar_cmd.spawn() {
    Ok((rx, child)) => {
        eprintln!("[tauri] Sidecar spawned successfully (PID: {})", child.pid());
        // ... handle sidecar ...
    }
    Err(e) => {
        eprintln!("[tauri] ERROR: Failed to spawn sidecar: {}", e);
        eprintln!("[tauri] Command: {:?}", sidecar_cmd);
        eprintln!("[tauri] CWD: {:?}", std::env::current_dir());
        // Suggest solutions
        if cfg!(unix) {
            eprintln!("[tauri] On Linux, ensure `uv` is installed or venv exists");
        }
        panic!("Failed to start JustHireMe backend");
    }
}
```

---

### 10.5.2 Structured Logging with File Output

**Implement as described in [Logging Strategy](06-logging-strategy.md).**

---

### 10.5.3 Timeout for Sidecar Port/Token Discovery

**Implement timeout as described in [Error Handling Strategy](05-error-handling-strategy.md).**

---

### 10.5.4 Retry Logic for Sidecar Spawn

**Implement retry logic:**
```rust
async fn spawn_sidecar_with_retry(app: &AppHandle, max_retries: u32) -> Result<(), String> {
    for attempt in 1..=max_retries {
        match try_spawn_sidecar(app).await {
            Ok(_) => return Ok(()),
            Err(e) => {
                eprintln!("[tauri] Attempt {}/{} failed: {}", attempt, max_retries, e);
                if attempt < max_retries {
                    tokio::time::sleep(Duration::from_secs(2)).await;
                }
            }
        }
    }
    Err(format!("Failed to spawn sidecar after {} attempts", max_retries))
}
```

---

### 10.5.5 Health Check Endpoint for Backend

**Add to `backend/main.py`:**
```python
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "version": __version__,
        "platform": sys.platform,
        "python": sys.version,
        "uptime": time.time() - _UP
    }
```

---

### 10.5.6 Graceful Shutdown Handling

**Improve shutdown in `lib.rs`:**
```rust
fn shutdown_sidecar(app: &AppHandle) {
    let child = app.state::<SidecarChild>().0.lock().unwrap().take();
    
    if let Some(child) = child {
        let pid = child.pid();
        eprintln!("[tauri] Stopping sidecar (PID: {})", pid);
        
        // Send SIGTERM first (graceful)
        kill_process_graceful(pid);
        
        // Wait for process to exit (with timeout)
        for _ in 0..10 {
            if !is_process_running(pid) {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(500));
        }
        
        // Force kill if still running
        kill_process_tree(pid);
        let _ = child.kill();
        
        eprintln!("[tauri] Sidecar stopped");
    }
    
    // Clear state
    // ...
}
```

---

## 10.6 Community & Contribution

### 10.6.1 Create Linux Testing Guide

**Document how others can test JustHireMe on Linux:**
- Different distributions (Ubuntu, Fedora, Arch)
- Different desktop environments (GNOME, KDE, Hyprland)
- Different hardware (x86_64, ARM)

---

### 10.6.2 Add Linux CI Matrix

**Extend `.github/workflows/ci.yml` to test on multiple Linux distros:**
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, fedora-latest, arch-latest]
```

**Note:** GitHub Actions may not have Arch directly. Use Docker:
```yaml
- name: Test on Arch
  run: |
    docker run -v $(pwd):/app archlinux /bin/bash -c "cd /app && ./scripts/test-on-arch.sh"
```

---

### 10.6.3 Create `SUPPORT_LINUX.md`

**Document Linux-specific support:**
- Where to get help
- How to report Linux-specific bugs
- Known issues by distribution
- Community-maintained packages (AUR, etc.)

---

## Summary

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Add Linux targets to Tauri config | High | Low | Enables Linux packaging |
| Create Linux package scripts | High | Low | Easy Linux builds |
| Add Linux to GitHub Actions | Medium | Medium | Automated Linux releases |
| Improve error handling | Medium | Medium | Better debugging |
| Add structured logging | Medium | Medium | Easier troubleshooting |
| Create Linux documentation | High | Low | Helps new users |
| Test Wayland native support | Low | Medium | Future-proofing |
| Create `.desktop` file | Medium | Low | Better desktop integration |

---

## Next Steps

1. Start with high-priority, low-effort tasks (config changes, scripts)
2. Test thoroughly on your Arch/Hyprland setup
3. Submit PRs to upstream repository
4. Encourage others to test on different Linux distributions
5. Build community around Linux support for JustHireMe
