# Current State Analysis

## Repository Structure

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

## Platform-Specific Code Locations

### 2.0 Browser Runtime (`backend/agents/browser_runtime.py:8-17`)

**Windows-Only Chrome Paths:**
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

**Fix Needed:** Add Linux paths:
```python
# Add to candidates list:
"/usr/bin/google-chrome",
"/usr/bin/chromium",
"/usr/bin/chromium-browser",
"/var/lib/flatpak/exports/bin/com.google.Chrome",
```

**Assessment:** ❌ No Linux browser paths. BLOCKER for automation features.

### 2.1 Rust/Tauri Layer (`src-tauri/src/lib.rs`)

#### Windows-Specific Code (lines 5-6, 87-103)

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

#### Bundled Python Path (lines 56-60)

```rust
let candidates = if cfg!(windows) {
    vec!["python.exe", "python"]
} else {
    vec!["bin/python3", "bin/python", "python"]
};
```

**Assessment:** ✅ Correctly handles Unix paths.

### 2.2 Python Backend (`backend/main.py`)

#### Windows Path Fallback (line 658, 827)

```python
# main.py:658 - get_lead_versions()
base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe", "assets")

# main.py:827 - similar pattern in other functions
base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe", "assets")
```

**Impact:** On Linux, creates `~/JustHireMe/assets/` instead of XDG-compliant `~/.local/share/JustHireMe/assets/`.

**Assessment:** ⚠️ Works but non-standard. Should use `$XDG_DATA_HOME` or `~/.local/share/`.

**Fix (for future):**
```python
# backend/db/client.py:11 (same pattern)
_b = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "JustHireMe"
)
```

### 2.3 Database Client (`backend/db/client.py:11`)

```python
_b = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustHireMe")
```

**Impact:** Same issue - non-standard path on Linux.

**Assessment:** ⚠️ HIGH - data location nonstandard, breaks backup/restore conventions.

### 2.4 Asset Directory (`backend/generator.py:10-13`)

```python
_assets = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "JustHireMe", "assets",
)
```

**Assessment:** ⚠️ MEDIUM - same non-standard path issue.

### 2.5 Build Configuration (`tauri.conf.json`)

#### Current Bundle Targets (line 28)

```json
"bundle": {
  "targets": ["nsis"],  // Windows-only!
  "externalBin": ["resources/backend/backend"],
  "resources": ["resources/bin/**/*"]
}
```

**Assessment:** ❌ Needs Linux targets added (`["deb", "AppImage", "tar.gz"]`).

#### Windows-Specific Settings (lines 42-51)

```json
"windows": {
  "nsis": {
    "displayLanguageSelector": false,
    "installMode": "currentUser"
  },
  "wix": {
    "language": "en-US"
  }
}
```

**Assessment:** ❌ Missing `"linux"` configuration block.

**Recommended Addition:**
```json
"linux": {
  "deb": {
    "depends": ["libgtk-3-0", "libwebkit2gtk-4.1-0", "libappindicator3-1"]
  },
  "appimage": {
    "bundleMediaPackager": true
  }
}
```

### 2.6 Package Scripts (`package.json`)

#### Current Scripts

```json
"scripts": {
  "package:windows": "tauri build --bundles nsis",
  "package:windows:all": "tauri build --bundles nsis msi",
  "package:windows:msi": "tauri build --bundles msi",
  "package:fast": "tauri build --no-bundle"
}
```

**Assessment:** ❌ No Linux packaging scripts. Need to add:

```json
"package:linux": "tauri build --bundles deb tar.gz",
"package:appimage": "tauri build --bundles appimage",
"package:deb": "tauri build --bundles deb"
```

### 2.7 PyInstaller Spec (`backend/backend.spec:11-13,29-30`)

**Windows-Only venv Path (line 11):**
```python
venv_site_packages = backend_root / ".venv" / "Lib" / "site-packages"
```

**Impact:** On Linux, venv site-packages lives at `.venv/lib/python3.13/site-packages`. This only matters for PyInstaller builds (Windows release packaging).

**Assessment:** ⚠️ MEDIUM - only affects release builds, not dev mode.

**Outdated References (lines 29-30):**
```python
hidden = [
    # ...
    "agents.free_scout", "agents.scoring_engine", "agents.semantic",
]
```

**Problem:** These files DON'T EXIST in the current codebase! The actual agents are:
- `agents/ingestor.py`
- `agents/scout.py`
- `agents/evaluator.py`
- `agents/generator.py`
- `agents/actuator.py`

**Assessment:** ❌ HIGH - `backend.spec` references non-existent files. PyInstaller bundle will fail or include wrong modules.

### 2.8 Unimplemented Security Claims

**Documentation Claims (project.md, SPEC.md):**
- "AES-256 Encryption using Windows DPAPI or Machine_UID"
- "Key Storage: AES-256 encryption using Windows DPAPI or Machine_UID"

**Reality:** NOT IMPLEMENTED anywhere. API keys stored in **plaintext** in SQLite `settings` table.

**Location:** `backend/db/client.py` - settings stored as plain key-value pairs.

**Assessment:** ❌ HIGH - misleading documentation about non-existent security features.

### 2.9 CI/CD Analysis (`.github/workflows/`)

| Workflow | Platform | Status |
|----------|-----------|--------|
| `ci.yml` | `ubuntu-latest` | ✅ Tests on Linux |
| `release.yml` | Windows only | ❌ No Linux release |

#### Linux Dependencies Installed in CI (ci.yml:84-99)

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

**Assessment:** ✅ Confirms Linux is tested in CI. Need to map these to Arch packages (see [Arch/Hyprland Requirements](03-arch-hyprland-requirements.md)).

## Code Quality Observations

### Strengths
- Clean separation: Tauri shell (`src-tauri/`), React frontend (`src/`), Python backend (`backend/`)
- Modern stack with good type safety (TypeScript + Python type hints)
- Local-first design (no cloud dependency for core features)
- WebSocket-based communication between frontend and Python backend
- Proper use of Rust's conditional compilation (`#[cfg]`) for platform-specific code

### Concerns
- **Alpha status** - expect bugs and breaking changes
- **Complex dependency chain:** Node + npm + Python 3.13 + uv + Rust + Tauri + Playwright + ML libraries
- **Python sidecar pattern:** Tauri spawns Python as a sidecar process (see `lib.rs:208`)
- **Experimental features disabled by default:** Browser automation, auto-apply
- **No Linux release pipeline:** Only Windows releases are automated

## File Statistics

| Category | Count |
|----------|-------|
| Total Directories | 42 (excluding .git internals) |
| Total Files | ~140 |
| Python files (.py) | 40 |
| TypeScript/TSX files | 25 |
| Rust files (.rs) | 3 |
| Shell scripts (.sh, .ps1) | 2 |
| Documentation (.md) | 19 |

## Next Steps

1. Review [Arch/Hyprland Requirements](03-arch-hyprland-requirements.md) for system setup
2. Check [Dependency Review](04-dependency-review.md) for version compatibility
3. Follow [Migration Steps](07-migration-steps.md) for installation
