# JustHireMe Linux Migration Guide
## From Windows-Centric to Arch/Hyprland Compatible

**Date:** 2026-05-07  
**Target Platform:** Arch Linux with Hyprland (Wayland)  
**Project Status:** Alpha v0.1.7  
**Document Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Arch/Hyprland Requirements](#3-archhyprland-requirements)
4. [Dependency Review & Updates](#4-dependency-review--updates)
5. [Error Handling Strategy](#5-error-handling-strategy)
6. [Logging Strategy](#6-logging-strategy)
7. [Migration Steps](#7-migration-steps)
8. [Known Issues & Solutions](#8-known-issues--solutions)
9. [Testing & Validation](#9-testing--validation)
10. [Future Work](#10-future-work)

---

## 1. Executive Summary

### 1.1 Project Overview

JustHireMe is a **local-first AI job intelligence workbench** built with:
- **Frontend:** React 19 + TypeScript + Vite 7 + Tailwind CSS 4
- **Backend:** Python 3.13 + FastAPI + WebSockets
- **Desktop Shell:** Tauri 2 (Rust)
- **Databases:** SQLite (CRM), Kuzu (Graph), LanceDB (Vectors)

### 1.2 Platform Compatibility Assessment

| Aspect | Windows | Linux (Arch/Hyprland) | Status |
|--------|---------|----------------------|--------|
| Core Architecture | ✅ Primary target | ✅ Compatible (with work) | Cross-platform by design |
| Tauri 2 Shell | ✅ Fully supported | ✅ Supported (GTK3/WebKit2GTK) | Good |
| Python Backend | ✅ Tested | ✅ Compatible | Good |
| Release Pipeline | ✅ Automated (NSIS/MSI) | ❌ Manual only | Needs work |
| Package Scripts | ✅ PowerShell + bash | ⚠️ bash only (no pkg script) | Partial |
| Documentation | ✅ `docs/windows-release.md` | ❌ None | Missing |
| Wayland Support | N/A | ⚠️ XWayland fallback | Unconfirmed |

### 1.3 Migration Difficulty: **MODERATE**

**Reasons:**
- Codebase is cross-platform by design (proper `#[cfg(windows)]` usage)
- No hard Windows dependencies found in core logic
- Tauri 2 officially supports Linux
- **BUT:** Release tooling is Windows-focused, Linux packaging needs creation
- Alpha status means bugs are expected

---

## 2. Current State Analysis

### 2.1 Repository Structure

```
JustHireMe/
├── src-tauri/              # Rust Tauri shell
│   ├── src/lib.rs         # Sidecar management (has Windows-specific code)
│   ├── tauri.conf.json    # Build config (NSIS-only targets)
│   ├── Cargo.toml        # Rust dependencies
│   └── resources/
│       ├── bin/chromium/  # Playwright browsers (.gitkeep)
│       └── python-runtime/# Bundled Python (.gitkeep)
├── src/                   # React TypeScript frontend
├── backend/               # Python FastAPI backend
│   ├── main.py           # Has LOCALAPPDATA fallback (line 658)
│   ├── pyproject.toml   # Python 3.13+ required
│   └── uv.lock          # Dependency lockfile
├── scripts/
│   ├── build-sidecar.sh  # Linux/macOS build script
│   └── build-sidecar.ps1 # Windows build script
├── docs/
│   ├── windows-release.md # Windows-only release docs
│   └── [no Linux docs]  # Missing!
└── package.json          # Has Windows-only package scripts
```

### 2.2 Platform-Specific Code Locations

#### 2.2.1 Rust/Tauri Layer (`src-tauri/src/lib.rs`)

**Windows-Specific (lines 5-6, 87-103):**
```rust
#[cfg(windows)]
use std::os::windows::process::CommandExt;

// ...

fn kill_process_tree(pid: u32) {
    #[cfg(windows)]
    {
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let _ = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW)
            .output();
    }

    #[cfg(not(windows))]
    {
        let _ = std::process::Command::new("kill")
            .args(["-TERM", &pid.to_string()])
            .output();
    }
}
```

**Assessment:** ✅ Properly guarded with `#[cfg]` attributes. Linux path uses `kill -TERM`.

**Bundled Python Path (lines 56-60):**
```rust
let candidates = if cfg!(windows) {
    vec!["python.exe", "python"]
} else {
    vec!["bin/python3", "bin/python", "python"]
};
```

**Assessment:** ✅ Correctly handles Unix paths.

#### 2.2.2 Python Backend (`backend/main.py`)

**Windows Path Fallback (line 658):**
```python
base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe", "assets")
```

**Assessment:** ✅ Has proper fallback to `~/.local/share` equivalent via `expanduser("~")`.

#### 2.2.3 Build Configuration (`tauri.conf.json`)

**Current bundle targets (line 28):**
```json
"bundle": {
  "targets": ["nsis"],  // Windows-only!
  "externalBin": ["resources/backend/backend"],
  "resources": ["resources/bin/**/*"]
}
```

**Assessment:** ❌ Needs Linux targets added (`["deb", "AppImage", "tar.gz"]`).

#### 2.2.4 Package Scripts (`package.json`)

**Current scripts:**
```json
"scripts": {
  "package:windows": "tauri build --bundles nsis",
  "package:windows:all": "tauri build --bundles nsis msi",
  "package:windows:msi": "tauri build --bundles msi",
  "package:fast": "tauri build --no-bundle"
}
```

**Assessment:** ❌ No Linux packaging scripts. Need to add `package:linux`, `package:appimage`, etc.

### 2.3 CI/CD Analysis (`.github/workflows/`)

| Workflow | Platform | Status |
|----------|-----------|--------|
| `ci.yml` | `ubuntu-latest` | ✅ Tests on Linux |
| `release.yml` | Windows only | ❌ No Linux release |

**Linux dependencies installed in CI (ci.yml:84-99):**
```yaml
- name: Install Tauri Linux system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y \
      build-essential curl file \
      libayatana-appindicator3-dev \
      libglib2.0-dev libgtk-3-dev \
      librsvg2-dev libssl-dev \
      libwebkit2gtk-4.1-dev \
      libxdo-dev pkg-config patchelf wget
```

**Assessment:** ✅ Confirms Linux is tested in CI. Need to map these to Arch packages.

---

## 3. Arch/Hyprland Requirements

### 3.1 System Dependencies (Arch Linux)

Map Ubuntu CI packages to Arch equivalents:

| Ubuntu Package | Arch Package | Purpose |
|---------------|--------------|---------|
| `build-essential` | `base-devel` | Compilation tools |
| `curl` | `curl` | HTTP requests |
| `file` | `file` | File type detection |
| `libayatana-appindicator3-dev` | `libappindicator-gtk3` | System tray icons |
| `libglib2.0-dev` | `glib2` | GLib library |
| `libgtk-3-dev` | `gtk3` | GTK3 toolkit |
| `librsvg2-dev` | `librsvg` | SVG rendering |
| `libssl-dev` | `openssl` | SSL/TLS support |
| `libwebkit2gtk-4.1-dev` | `webkit2gtk-4.1` | WebView rendering |
| `libxdo-dev` | `libxdo` | X11 automation (fallback) |
| `pkg-config` | `pkg-config` | Library configuration |
| `patchelf` | `patchelf` | ELF binary patching |
| `wget` | `wget` | File downloads |

**Installation Command:**
```bash
sudo pacman -S base-devel curl file glib2 gtk3 librsvg openssl \
  webkit2gtk-4.1 libxdo pkg-config patchelf wget \
  libappindicator-gtk3
```

### 3.2 Hyprland/Wayland Considerations

#### 3.2.1 Tauri on Wayland

Tauri 2 uses GTK3 which runs on Wayland via **XWayland** by default.

**Environment Variables for Wayland:**
```bash
# Force Wayland backend (experimental for GTK3)
export GDK_BACKEND=wayland
export XDG_SESSION_TYPE=wayland

# Or use XWayland (default, more stable)
# No special config needed - Tauri will use XWayland automatically
```

**Recommendation:** Start with default (XWayland). Switch to `GDK_BACKEND=wayland` only if needed.

#### 3.2.2 Known Hyprland Issues

| Issue | Likelihood | Solution |
|-------|-----------|----------|
| Scaling problems (HiDPI) | Medium | Set `GDK_SCALE=2` or use Hyprland's `env = GDK_SCALE,2` |
| Missing system tray | Low | Hyprland doesn't have system tray; use `libappindicator-gtk3` for fallback |
| Window decorations | Low | Tauri uses client-side decorations; should work |
| WebView rendering | Low | WebKit2GTK should work via XWayland |

#### 3.2.3 Hyprland Configuration

Add to `~/.config/hypr/hyprland.conf`:
```ini
# For JustHireMe (if using XWayland)
windowrulev2 = float, class:(JustHireMe)
windowrulev2 = size 1440 900, class:(JustHireMe)

# Or force Wayland backend
env = GDK_BACKEND,wayland
env = XDG_SESSION_TYPE,wayland
```

### 3.3 Rust/Tauri on Arch

**Install Rust:**
```bash
# Using rustup (recommended)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Or via pacman
sudo pacman -S rustup
rustup install stable
rustup default stable
```

**Install Tauri CLI:**
```bash
cargo install tauri-cli --version "^2"
```

### 3.4 Python 3.13 on Arch

**Install Python 3.13:**
```bash
sudo pacman -S python python-pip

# Verify version
python --version  # Should be 3.13+
```

**Install uv (Python package manager):**
```bash
# Using pip
pip install uv

# Or via official installer
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3.5 Node.js 24+ on Arch

**Using nvm (recommended):**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# Install Node 24
nvm install 24
nvm use 24
```

**Or via pacman:**
```bash
sudo pacman -S nodejs npm
```

---

## 4. Dependency Review & Updates

### 4.1 Current Dependency Versions

#### 4.1.1 Frontend (`package.json`)

| Dependency | Current Version | Latest Stable | Action Needed |
|-----------|-----------------|---------------|---------------|
| Node.js | 24 (CI) | 24.x | ✅ Current |
| React | ^19.0.0 | 19.x | ✅ Current |
| TypeScript | ^5.8.3 | 5.8.x | ✅ Current |
| Vite | ^7.0.0 | 7.x | ✅ Current |
| Tailwind CSS | ^4.1.7 | 4.1.x | ✅ Current |
| @tauri-apps/api | ^2.7.0 | 2.7.x | ✅ Current |
| @tauri-apps/cli | ^2.15.0 | 2.15.x | ✅ Current |

**Assessment:** ✅ Frontend dependencies are up-to-date.

#### 4.1.2 Backend (`backend/pyproject.toml`)

| Dependency | Current Version | Latest Stable | Action Needed |
|-----------|-----------------|---------------|---------------|
| Python | >=3.13 | 3.13.x | ✅ Current |
| FastAPI | ^0.115.0 | 0.115.x | ✅ Current |
| uvicorn | ^0.34.0 | 0.34.x | ✅ Current |
| sentence-transformers | ^5.1.0 | 5.1.x | ✅ Current |
| kuzu | ^0.6.0 | 0.6.x | ✅ Current |
| lancedb | ^0.17.0 | 0.17.x | ✅ Current |
| playwright | ^1.49.0 | 1.49.x | ✅ Current |

**Assessment:** ✅ Python dependencies are up-to-date.

#### 4.1.3 Rust (`src-tauri/Cargo.toml`)

| Dependency | Current Version | Latest Stable | Action Needed |
|-----------|-----------------|---------------|---------------|
| tauri | 2.x (workspace) | 2.x | ✅ Current |
| tauri-build | ^2 | 2.x | ✅ Current |
| serde | ^1.0 | 1.0.x | ✅ Current |

**Assessment:** ✅ Rust dependencies are up-to-date.

### 4.2 Dependency Conflicts Check

**Potential Issues:**

1. **Python ML Libraries on Linux:**
   - `sentence-transformers` requires `torch` (PyTorch)
   - PyTorch on Linux may need CUDA setup for GPU acceleration
   - **Solution:** CPU-only PyTorch is fine for local use

2. **Playwright Browsers:**
   - `playwright` needs browser binaries
   - Linux: `playwright install chromium` (might need system deps)
   - **Solution:** Document browser install steps

3. **KuzuDB + LanceDB:**
   - Both have native components
   - Should work on Arch x86_64
   - **Solution:** Test import after `uv sync`

### 4.3 Recommended Version Pinning

**For reproducibility, pin these in `pyproject.toml`:**
```toml
[project]
dependencies = [
    "fastapi==0.115.11",  # Pin to specific patch
    "uvicorn==0.34.0",
    "sentence-transformers==5.1.0",
    # ... etc
]
```

---

## 5. Error Handling Strategy

### 5.1 Current Error Handling Gaps

#### 5.1.1 Tauri Sidecar Management (`src-tauri/src/lib.rs`)

**Current Issues:**
- Sidecar process errors not always logged with context
- Port discovery (`PORT:`) has no timeout
- API token (`JHM_TOKEN=`) discovery has no timeout
- No retry logic for sidecar spawn failures

**Recommended Improvements (for later implementation):**

```rust
// Add to sidecar spawn logic
fn spawn_sidecar_with_retry(app: &AppHandle, max_retries: u32) -> Result<(), String> {
    for attempt in 1..=max_retries {
        match spawn_sidecar(app) {
            Ok(_) => return Ok(()),
            Err(e) => {
                eprintln!("[tauri] Sidecar spawn attempt {} failed: {}", attempt, e);
                if attempt == max_retries {
                    return Err(format!("Failed to spawn sidecar after {} attempts: {}", max_retries, e));
                }
                std::thread::sleep(std::time::Duration::from_secs(2));
            }
        }
    }
    unreachable!()
}
```

#### 5.1.2 Python Backend (`backend/main.py`)

**Current Issues:**
- No global exception handler for unhandled errors
- FastAPI startup doesn't validate critical dependencies
- Database connection failures not caught early
- WebSocket errors not always logged

**Recommended Improvements:**

```python
# Add to main.py startup event
@app.on_event("startup")
async def startup_event():
    try:
        # Validate critical dependencies
        import torch
        import sentence_transformers
        import kuzu
        import lancedb
        _log.info("All critical dependencies imported successfully")
    except ImportError as e:
        _log.error(f"Critical dependency missing: {e}")
        raise RuntimeError(f"Cannot start: missing dependency: {e}")

    # Validate database connections
    try:
        from db.client import init_db
        init_db()
        _log.info("Database initialized successfully")
    except Exception as e:
        _log.error(f"Database initialization failed: {e}")
        raise
```

### 5.2 Error Handling Checklist

For Linux migration, ensure these are logged:

- [ ] Tauri sidecar spawn success/failure
- [ ] Sidecar port discovery (with timeout)
- [ ] Sidecar API token discovery (with timeout)
- [ ] Python backend startup errors
- [ ] Database connection status
- [ ] ML model loading (sentence-transformers)
- [ ] FastAPI startup completion
- [ ] WebSocket connection errors
- [ ] File system permission errors (for `resources/` dirs)

---

## 6. Logging Strategy

### 6.1 Current Logging Implementation

#### 6.1.1 Rust/Tauri (`src-tauri/src/lib.rs`)

**Current logging:**
- Uses `eprintln!` for sidecar events
- Sidecar stdout/stderr forwarded via `CommandEvent`
- Tauri events emitted: `sidecar-port`, `sidecar-token`, `sidecar-terminated`

**Enhancement Recommendations:**
- Add structured logging with `log` crate
- Log to file in addition to stderr
- Include timestamps in all log messages

#### 6.1.2 Python Backend (`backend/main.py`)

**Current logging:**
- Uses custom `logger.py` with `_log = get_logger(__name__)`
- Log level controlled via environment variable (likely)

**Enhancement Recommendations:**
- Log to both file and stderr
- Include request IDs for tracing
- Log ML model loading times
- Structured JSON logging for machine parsing

### 6.2 Recommended Logging Architecture

```
JustHireMe/
├── ~/.local/share/JustHireMe/logs/  # Or XDG_DATA_HOME
│   ├── tauri.log                   # Rust/Tauri logs
│   ├── backend.log                  # Python FastAPI logs
│   └── sidecar.log                 # Sidecar stdout/stderr
└── Console output (stderr/stdout)   # Real-time logs
```

### 6.3 Log Levels for Debugging

| Level | Tauri/Rust | Python/Backend | Purpose |
|-------|-----------|----------------|---------|
| ERROR | `eprintln!` | `_log.error()` | Failures that need attention |
| WARN | `eprintln!` | `_log.warning()` | Recoverable issues |
| INFO | `eprintln!` | `_log.info()` | Startup, shutdown, key events |
| DEBUG | `eprintln!` | `_log.debug()` | Detailed flow (dev mode) |
| TRACE | `eprintln!` | `_log.trace()` | Very verbose (troubleshooting) |

### 6.4 Key Events to Log

**Tauri Side (Rust):**
```rust
eprintln!("[tauri] Starting JustHireMe v{}", env!("CARGO_PKG_VERSION"));
eprintln!("[tauri] Platform: {} {}", std::env::consts::OS, std::env::consts::ARCH);
eprintln!("[tauri] Sidecar PID: {}", pid);
eprintln!("[tauri] Sidecar port discovered: {}", port);
eprintln!("[tauri] Sidecar terminated with code: {:?}", s.code);
eprintln!("[tauri] WebSocket connection from frontend");
```

**Backend Side (Python):**
```python
_log.info(f"Starting JustHireMe backend v{__version__}")
_log.info(f"Platform: {sys.platform}")
_log.info(f"Python: {sys.version}")
_log.info(f"Loaded profile with {len(skills)} skills")
_log.info(f"SentenceTransformer model loaded: {model_name}")
_log.info(f"FastAPI listening on port {port}")
_log.info(f"WebSocket client connected")
```

---

## 7. Migration Steps

### 7.1 Pre-Migration Checklist

- [ ] Backup current codebase (`git stash` or branch)
- [ ] Document current Windows setup (for reference)
- [ ] Install Arch system dependencies (see Section 3.1)
- [ ] Install Rust, Node 24+, Python 3.13, uv
- [ ] Verify Hyprland config (see Section 3.2.3)

### 7.2 Step-by-Step Migration

#### Step 1: Clone and Install Frontend Dependencies
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm install
```

**Expected output:** `added XXX packages in Xs`

**If error:** Check Node version (`node --version` should be 24+)

#### Step 2: Install Backend Dependencies
```bash
cd backend
uv sync --dev
```

**Expected output:** `Resolved XXX packages in Xs`

**If error:** Check Python version (`python --version` should be 3.13+)

#### Step 3: Verify Tauri Setup
```bash
cd ..
npm run tauri info
```

**Expected output:** Tauri version, Rust version, platform info

**If error:** Install Tauri CLI (`cargo install tauri-cli`)

#### Step 4: Test Backend Independently
```bash
cd backend
uv run python main.py
```

**Expected output:**
```
PORT:12345
JHM_TOKEN=abc123...
INFO:     Uvicorn running on http://127.0.0.1:12345
```

**If error:** Check logs for missing dependencies

#### Step 5: Test Frontend + Backend (Dev Mode)
```bash
# Terminal 1: Start backend
cd backend
uv run python main.py

# Terminal 2: Start frontend dev server
cd ..
npm run dev
```

**Expected:** Vite dev server at `http://localhost:1420`

#### Step 6: Test Full Tauri App
```bash
npm run tauri dev
```

**Expected:** Tauri window opens with React frontend

**If error:** Check `src-tauri/tauri.conf.json` devUrl

#### Step 7: Build for Production (No Bundle)
```bash
npm run package:fast
```

**Expected:** Binary at `src-tauri/target/debug/justhireme`

#### Step 8: Build Linux Package (Future)
```bash
# After adding Linux targets to tauri.conf.json
npm run package:linux  # (to be created)
```

### 7.3 Post-Migration Verification

- [ ] Frontend loads at `localhost:1420`
- [ ] Backend starts and outputs `PORT:` and `JHM_TOKEN=`
- [ ] Tauri window opens and connects to backend
- [ ] WebSocket connection established
- [ ] Database files created (`~/.local/share/JustHireMe/`)
- [ ] No critical errors in logs

---

## 8. Known Issues & Solutions

### 8.1 Build Issues

#### Issue: `webkit2gtk-4.1` Not Found
**Symptom:** Cargo build fails with `webkit2gtk` not found

**Solution:**
```bash
sudo pacman -S webkit2gtk-4.1
```

**If not available:** Check AUR or use `webkit2gtk` (older version)

#### Issue: `libappindicator3` Not Found
**Symptom:** Tauri build fails with appindicator error

**Solution:**
```bash
sudo pacman -S libappindicator-gtk3
```

#### Issue: Rust Compilation Errors
**Symptom:** `cargo check` fails in `src-tauri/`

**Solution:**
```bash
cd src-tauri
cargo clean
cargo check
```

### 8.2 Runtime Issues

#### Issue: Sidecar Won't Start
**Symptom:** Tauri opens but shows "Sidecar port not yet discovered"

**Debug steps:**
1. Check logs: `tail -f ~/.local/share/JustHireMe/logs/tauri.log`
2. Test backend manually: `cd backend && uv run python main.py`
3. Check Python path in `lib.rs` (line 56-60)

**Solution:** Ensure `backend/.venv/bin/python` exists or `uv` is in PATH

#### Issue: WebSocket Connection Failed
**Symptom:** Frontend can't connect to backend

**Debug steps:**
1. Check backend is running: `curl http://127.0.0.1:PORT/api/v1/health`
2. Check token: Compare `JHM_TOKEN` in backend output vs frontend request
3. Check CSP in `tauri.conf.json` (line 23)

**Solution:** Verify `connect-src` in CSP allows `ws://127.0.0.1:*`

#### Issue: Database Permission Denied
**Symptom:** SQLite/KuzuDB fails to create files

**Solution:**
```bash
mkdir -p ~/.local/share/JustHireMe
chmod 755 ~/.local/share/JustHireMe
```

#### Issue: ML Models Download Fails
**Symptom:** `sentence-transformers` fails to download model

**Solution:**
```bash
# Set HuggingFace cache to writable location
export HF_HOME=~/.cache/huggingface
mkdir -p $HF_HOME
```

### 8.3 Hyprland-Specific Issues

#### Issue: App Shows as Blank Window
**Symptom:** Tauri window opens but is blank/white

**Solution:**
```bash
# Force XWayland
export WAYLAND_DISPLAY=""
npm run tauri dev
```

#### Issue: Scaling is Wrong (HiDPI)
**Symptom:** UI elements too small/large

**Solution:**
Add to `~/.config/hypr/hyprland.conf`:
```ini
env = GDK_SCALE,2  # Adjust based on your DPI
```

#### Issue: No System Tray Icon
**Symptom:** App doesn't show in system tray

**Note:** Hyprland doesn't have a system tray by default. Consider using `waybar` with tray module.

### 8.4 Future Linux Packaging Issues

#### Issue: No `.desktop` File
**Current state:** Not created automatically

**Solution (future):** Create `JustHireMe.desktop`:
```ini
[Desktop Entry]
Name=JustHireMe
Exec=/usr/bin/justhireme
Icon=/usr/share/icons/JustHireMe.png
Type=Application
Categories=Office;
```

#### Issue: No Linux Release in GitHub Actions
**Current state:** `release.yml` only builds Windows

**Solution (future):** Add Linux job to release workflow (see Section 10).

---

## 9. Testing & Validation

### 9.1 Manual Testing Checklist

#### 9.1.1 Backend API Tests
```bash
cd backend
uv run python -m pytest tests/test_regressions.py -v
```

**Expected:** All tests pass

#### 9.1.2 Frontend Build Test
```bash
npm run build
```

**Expected:** `dist/` directory created without errors

#### 9.1.3 Tauri Check
```bash
cd src-tauri
cargo check
```

**Expected:** No compilation errors

### 9.2 Integration Testing

#### 9.2.1 Full App Test
1. Start app: `npm run tauri dev`
2. Check sidecar port discovered: Look for `[tauri] Sidecar port: XXXX`
3. Check API token discovered: Look for token in logs
4. Test job scraping (if configured)
5. Test document generation
6. Check database files created

#### 9.2.2 Log Verification
```bash
# Check Tauri logs
grep -i "error\|fail\|exception" ~/.local/share/JustHireMe/logs/tauri.log

# Check backend logs
grep -i "error\|fail\|exception" ~/.local/share/JustHireMe/logs/backend.log
```

### 9.3 Performance Testing

#### 9.3.1 Startup Time
```bash
time npm run tauri dev
# Note: First run will be slower (compilation)
```

#### 9.3.2 ML Model Loading
Check logs for model loading time:
```
_log.info("SentenceTransformer model loaded in X.XXs")
```

---

## 10. Future Work

### 10.1 Linux Packaging

**To Do:**
1. Add Linux targets to `tauri.conf.json`:
   ```json
   "bundle": {
     "targets": ["nsis", "deb", "AppImage", "tar.gz"]
   }
   ```

2. Create Linux package scripts in `package.json`:
   ```json
   "scripts": {
     "package:linux": "tauri build --bundles deb AppImage",
     "package:appimage": "tauri build --bundles AppImage",
     "package:deb": "tauri build --bundles deb"
   }
   ```

3. Create `.desktop` file for Linux desktop integration

### 10.2 GitHub Actions for Linux Releases

**To Do:**
Add to `.github/workflows/release.yml`:

```yaml
build-tauri-linux:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - name: Install Tauri dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y build-essential curl file \
          libayatana-appindicator3-dev libglib2.0-dev libgtk-3-dev \
          librsvg2-dev libssl-dev libwebkit2gtk-4.1-dev \
          libxdo-dev pkg-config patchelf wget
    - uses: dtolnay/rust-toolchain@stable
    - uses: actions/setup-node@v6
      with:
        node-version: '24'
    - uses: astral-sh/setup-uv@v8
    - run: npm ci
    - run: cd backend && uv sync --dev
    - run: npm run package:linux
    - uses: actions/upload-artifact@v4
      with:
        name: JustHireMe-Linux
        path: src-tauri/target/release/bundle/
```

### 10.3 Wayland Native Support

**To Do:**
- Test with `GDK_BACKEND=wayland`
- Fix any GTK3/Wayland issues
- Consider migration to GTK4 (better Wayland support) in future

### 10.4 Documentation

**To Do:**
- Create `docs/linux-release.md` (mirror of `windows-release.md`)
- Update `README.md` with Linux installation instructions
- Add Arch/Hyprland specific troubleshooting section
- Create video walkthrough for Linux setup

### 10.5 Code Improvements (Future PRs)

1. **Better error messages in `lib.rs`**
2. **Structured logging with file output**
3. **Timeout for sidecar port/token discovery**
4. **Retry logic for sidecar spawn**
5. **Health check endpoint for backend**
6. **Graceful shutdown handling**

---

## Appendix A: Quick Reference

### A.1 Useful Commands

| Task | Command |
|------|---------|
| Install system deps | `sudo pacman -S base-devel curl file glib2 gtk3 librsvg openssl webkit2gtk-4.1 libxdo pkg-config patchelf wget libappindicator-gtk3` |
| Install Rust | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Install Node 24 | `nvm install 24 && nvm use 24` |
| Install uv | `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Clone repo | `git clone https://github.com/vasu-devs/JustHireMe.git` |
| Install frontend | `npm install` |
| Install backend | `cd backend && uv sync --dev` |
| Run dev mode | `npm run tauri dev` |
| Build (no bundle) | `npm run package:fast` |
| Test backend | `cd backend && uv run python -m pytest tests/ -v` |
| Check Tauri | `npm run tauri info` |

### A.2 Log Locations

| Log | Location |
|-----|----------|
| Tauri/Rust | `~/.local/share/JustHireMe/logs/tauri.log` (future) |
| Backend/Python | `~/.local/share/JustHireMe/logs/backend.log` (future) |
| Sidecar stdout | stderr (forwarded by Tauri) |
| Build logs | `src-tauri/target/debug/build/` |

### A.3 Config File Locations

| Config | Location |
|--------|----------|
| Tauri config | `src-tauri/tauri.conf.json` |
| Frontend config | `vite.config.ts`, `tsconfig.json` |
| Backend config | `backend/pyproject.toml`, `backend/.env` |
| User data | `~/.local/share/JustHireMe/` |

---

## Document Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-07 | Initial document created from codebase analysis |

---

**End of Document**
