# Arch/Hyprland Requirements

## System Dependencies (Arch Linux)

### Package Mapping: Ubuntu CI → Arch

Map Ubuntu CI packages to Arch equivalents (from `.github/workflows/ci.yml:84-99`):

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

### Installation Command

```bash
sudo pacman -S base-devel curl file glib2 gtk3 librsvg openssl \
  webkit2gtk-4.1 libxdo pkg-config patchelf wget \
  libappindicator-gtk3
```

**Verification:**
```bash
pacman -Q base-devel curl file glib2 gtk3 librsvg openssl webkit2gtk-4.1 libxdo pkg-config patchelf wget libappindicator-gtk3
```

## Hyprland/Wayland Considerations

### Tauri on Wayland

Tauri 2 uses GTK3 which runs on Wayland via **XWayland** by default.

#### Environment Variables for Wayland

**Option 1: XWayland (Default, More Stable)**
```bash
# No special config needed - Tauri will use XWayland automatically
npm run tauri dev
```

**Option 2: Native Wayland (Experimental for GTK3)**
```bash
# Force Wayland backend
export GDK_BACKEND=wayland
export XDG_SESSION_TYPE=wayland
npm run tauri dev
```

**Recommendation:** Start with default (XWayland). Switch to `GDK_BACKEND=wayland` only if needed.

### Known Hyprland Issues

| Issue | Likelihood | Solution |
|-------|-----------|----------|
| Scaling problems (HiDPI) | Medium | Set `GDK_SCALE=2` or use Hyprland's `env = GDK_SCALE,2` |
| Missing system tray | Low | Hyprland doesn't have system tray; use `libappindicator-gtk3` for fallback or use `waybar` with tray module |
| Window decorations | Low | Tauri uses client-side decorations; should work |
| WebView rendering | Low | WebKit2GTK should work via XWayland |
| Keyboard shortcuts | Low | May need to configure in Hyprland config |

### Hyprland Configuration

Add to `~/.config/hypr/hyprland.conf`:

```ini
# Environment variables for GTK applications
env = GDK_BACKEND,wayland,x11  # Try Wayland first, fallback to X11
env = XDG_SESSION_TYPE,wayland
env = GDK_SCALE,1  # Adjust based on your DPI (2 for HiDPI)

# Window rules for JustHireMe
windowrulev2 = float, class:(JustHireMe)
windowrulev2 = size 1440 900, class:(JustHireMe)
windowrulev2 = workspace 2, class:(JustHireMe)  # Optional: open on specific workspace

# Optional: Force XWayland for better compatibility
# windowrulev2 = xwayland, class:(JustHireMe)
```

### Wayland vs XWayland Performance

| Aspect | XWayland | Native Wayland |
|--------|----------|----------------|
| Stability | ✅ More stable for GTK3 | ⚠️ Experimental |
| Performance | Good | Better (less overhead) |
| Scaling | May need `GDK_SCALE` | Native fractional scaling |
| System Tray | Works with libappindicator | Limited support |

## Rust/Tauri on Arch

### Install Rust

**Option 1: Using rustup (Recommended)**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Verify installation
rustc --version
cargo --version
```

**Option 2: Via pacman**
```bash
sudo pacman -S rustup
rustup install stable
rustup default stable
```

**Verify:**
```bash
rustc --version  # Should be stable (e.g., 1.85+)
cargo --version
```

### Install Tauri CLI

```bash
# Install Tauri CLI v2
cargo install tauri-cli --version "^2"

# Verify
cargo tauri --version
```

**Alternative: Local project installation**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm install
# Tauri CLI will be available via `npm run tauri`
```

## Python 3.13 on Arch

### Install Python

```bash
sudo pacman -S python python-pip

# Verify version
python --version  # Should be 3.13+
python3 --version
```

**Note:** Arch Linux typically ships the latest Python stable. As of 2026-05, Python 3.13+ should be available.

### Install uv (Python Package Manager)

**Option 1: Via pip**
```bash
pip install uv

# Verify
uv --version
```

**Option 2: Official installer**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

**Option 3: Via pacman (if available)**
```bash
sudo pacman -S uv  # Check if in repos
```

**Verify:**
```bash
uv --version
```

## Node.js 24+ on Arch

### Option 1: Using nvm (Recommended for Version Management)

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc  # or ~/.zshrc for zsh

# Install Node 24
nvm install 24
nvm use 24
nvm alias default 24
```

**Verify:**
```bash
node --version  # Should be v24.x
npm --version
```

### Option 2: Via pacman

```bash
sudo pacman -S nodejs npm

# Verify
node --version
npm --version
```

**Note:** Arch's pacman may not have Node 24 yet. Check with `pacman -Ss nodejs`.

### Option 3: Using n (Node Version Manager)

```bash
npm install -g n
n 24
```

## Additional Tools

### Git

```bash
sudo pacman -S git
git --version
```

### Additional Useful Packages

```bash
# For building Python packages with native extensions
sudo pacman -S python-setuptools python-wheel

# For ML libraries (if using GPU)
sudo pacman -S cuda  # If you have NVIDIA GPU

# For debugging
sudo pacman -S gdb strace
```

## Verification Script

Create a verification script to ensure all dependencies are installed:

```bash
#!/bin/bash
# Save as verify-setup.sh

echo "=== JustHireMe Linux Setup Verification ==="
echo

# Check system packages
echo "Checking system packages..."
for pkg in base-devel curl file glib2 gtk3 librsvg openssl webkit2gtk-4.1 libxdo pkg-config patchelf wget libappindicator-gtk3; do
  if pacman -Q $pkg &>/dev/null; then
    echo "✅ $pkg installed"
  else
    echo "❌ $pkg NOT installed"
  fi
done

echo
echo "Checking development tools..."
echo -n "Rust: "; rustc --version 2>/dev/null || echo "❌ Not installed"
echo -n "Cargo: "; cargo --version 2>/dev/null || echo "❌ Not installed"
echo -n "Node: "; node --version 2>/dev/null || echo "❌ Not installed"
echo -n "npm: "; npm --version 2>/dev/null || echo "❌ Not installed"
echo -n "Python: "; python --version 2>/dev/null || echo "❌ Not installed"
echo -n "uv: "; uv --version 2>/dev/null || echo "❌ Not installed"
echo -n "Git: "; git --version 2>/dev/null || echo "❌ Not installed"

echo
echo "=== Verification Complete ==="
```

**Run it:**
```bash
chmod +x verify-setup.sh
./verify-setup.sh
```

### Playwright + Wayland Flags

**Headless mode:** Works perfectly (doesn't need display).

**Headed mode:** Needs `DISPLAY` or `WAYLAND_DISPLAY` environment.

**For Chromium under Wayland:**
```bash
# In backend/agents/browser_runtime.py, add to launch arguments:
--ozone-platform-hint=auto
--enable-features=UseOzonePlatform
```

**Playwright's `launch_chromium` in `browser_runtime.py` doesn't pass Wayland flags.**

**Fix for `browser_runtime.py`:**
```python
# Add after line 22:
if os.environ.get("WAYLAND_DISPLAY"):
    kwargs.setdefault("args", [])
    kwargs["args"].extend([
        "--ozone-platform-hint=auto",
        "--enable-features=UseOzonePlatform"
    ])
```

**The experimental actuator (auto-apply) uses headed mode for form filling.**

**Reference:** Audit finding 4.2 - Playwright + Wayland.

---

## Next Steps

1. Install all dependencies using the commands above
2. Run verification script to confirm setup
3. Review [Dependency Review](04-dependency-review.md) for version compatibility
4. Follow [Migration Steps](07-migration-steps.md) for installation
