# Known Issues & Solutions

## Build Issues

### Issue 1: `webkit2gtk-4.1` Not Found

**Symptom:** Cargo build fails with `webkit2gtk` not found

**Error message:**
```
error: failed to run custom build command for `webkit2gtk-sys v...`
Package `webkit2gtk-4.1` was not found in the pkg-config search path
```

**Solution:**
```bash
sudo pacman -S webkit2gtk-4.1
```

**If not available in Arch repos:**
- Check AUR: `yay -S webkit2gtk-4.1`
- Or use older version: `webkit2gtk` (may work with Tauri 2)

**Verification:**
```bash
pkg-config --modversion webkit2gtk-4.1
```

---

### Issue 2: `libappindicator3` Not Found

**Symptom:** Tauri build fails with appindicator error

**Error message:**
```
error: failed to run custom build command for `libappindicator v...`
```

**Solution:**
```bash
sudo pacman -S libappindicator-gtk3
```

**Note:** Arch package name is `libappindicator-gtk3`, not `libappindicator3-dev` (Ubuntu name).

---

### Issue 3: Rust Compilation Errors

**Symptom:** `cargo check` or `cargo build` fails in `src-tauri/`

**Solution 1: Clean and rebuild**
```bash
cd src-tauri
cargo clean
cargo check
```

**Solution 2: Update Rust**
```bash
rustup update stable
```

**Solution 3: Check Tauri dependencies**
```bash
cd src-tauri
cargo tree  # View dependency tree
cargo audit  # Check for vulnerabilities
```

---

## Runtime Issues

### Issue 4: Sidecar Won't Start

**Symptom:** Tauri opens but shows "Sidecar port not yet discovered" or similar error

**Debug steps:**

1. **Check logs:**
   ```bash
   tail -f ~/.local/share/JustHireMe/logs/tauri.log
   ```

2. **Test backend manually:**
   ```bash
   cd backend
   uv run python main.py
   ```
   Look for `PORT:12345` and `JHM_TOKEN=...` output.

3. **Check Python path in `lib.rs` (line 56-60):**
   ```rust
   let candidates = if cfg!(windows) {
       vec!["python.exe", "python"]
   } else {
       vec!["bin/python3", "bin/python", "python"]
   };
   ```
   Ensure one of these exists in the backend directory.

4. **Verify Python virtual environment:**
   ```bash
   ls -la backend/.venv/bin/python
   ```
   If missing: `cd backend && uv venv && uv sync`

**Solution:** Ensure `backend/.venv/bin/python` exists or `uv` is in PATH.

---

### Issue 5: WebSocket Connection Failed

**Symptom:** Frontend can't connect to backend

**Debug steps:**

1. **Check backend is running:**
   ```bash
   curl http://127.0.0.1:PORT/api/v1/health  # Replace PORT
   ```

2. **Check token:** Compare `JHM_TOKEN` in backend output vs frontend request.
   - Backend outputs: `JHM_TOKEN=abc123...`
   - Frontend should send this in WebSocket connection

3. **Check CSP in `tauri.conf.json` (line 23):**
   ```json
   "connect-src http://127.0.0.1:* ws://127.0.0.1:*"
   ```
   Ensure this allows your backend port.

4. **Check browser console (F12 in Tauri dev mode):**
   Look for WebSocket connection errors.

**Solution:** Verify `connect-src` in CSP allows `ws://127.0.0.1:*`.

---

### Issue 6: Database Permission Denied

**Symptom:** SQLite/KuzuDB fails to create files

**Error message:**
```
sqlite3.OperationalError: unable to open database file
```
or
```
PermissionError: [Errno 13] Permission denied: '.../justhireme.db'
```

**Solution:**
```bash
# Create data directory with correct permissions
mkdir -p ~/.local/share/JustHireMe
chmod 755 ~/.local/share/JustHireMe

# Or fix existing directory
chmod -R u+w ~/.local/share/JustHireMe
```

**Check what user/data directory the app is using:**
```python
# In backend/main.py or Python shell
from pathlib import Path
import os

# Check XDG_DATA_HOME
xdg_data = os.environ.get("XDG_DATA_HOME")
print(f"XDG_DATA_HOME: {xdg_data}")

# Default location
default = Path.home() / ".local" / "share" / "JustHireMe"
print(f"Default data dir: {default}")
```

---

### Issue 7: ML Models Download Fails

**Symptom:** `sentence-transformers` fails to download model from HuggingFace

**Error message:**
```
OSError: Can't load tokenizer for '...'
```
or connection timeouts.

**Solution 1: Set HuggingFace cache to writable location**
```bash
export HF_HOME=~/.cache/huggingface
mkdir -p $HF_HOME
```

**Solution 2: Use offline mode (after initial download)**
```bash
export HF_HUB_OFFLINE=1
```

**Solution 3: Manually download model**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='~/.cache/huggingface')
```

**Solution 4: Check network/firewall**
- Ensure `huggingface.co` is not blocked
- Use VPN if in restricted network

---

## Hyprland-Specific Issues

### Issue 8: App Shows as Blank Window

**Symptom:** Tauri window opens but is blank/white (no content)

**Debug steps:**

1. **Check if backend is running** (see Issue 4)
2. **Check frontend dev server** (see Step 5 in [Migration Steps](07-migration-steps.md))
3. **Open browser dev tools in Tauri** (if available in dev mode)

**Solution 1: Force XWayland**
```bash
# Force X11 backend (disable Wayland)
export WAYLAND_DISPLAY=""
npm run tauri dev
```

**Solution 2: Check GDK_BACKEND**
```bash
# Try Wayland first, fallback to X11
export GDK_BACKEND=wayland,x11
npm run tauri dev
```

**Solution 3: Check Hyprland logs**
```bash
# In another terminal
journalctl --user -f | grep Hyprland
```

---

### Issue 9: Scaling is Wrong (HiDPI)

**Symptom:** UI elements too small or too large on high-DPI display

**Solution 1: Set GDK_SCALE**
Add to `~/.config/hypr/hyprland.conf`:
```ini
env = GDK_SCALE,2  # Adjust based on your DPI (1, 1.5, 2, etc.)
```

**Solution 2: Use Hyprland's native scaling**
```ini
# In hyprland.conf
monitor=eDP-1,2560x1440@60,0x0,2
# The last number is the scale factor
```

**Solution 3: Force GTK scaling**
```bash
export GDK_SCALE=2
export GDK_DPI_SCALE=0.5  # Adjust font scaling
npm run tauri dev
```

---

### Issue 10: No System Tray Icon

**Symptom:** App doesn't show in system tray

**Explanation:** Hyprland doesn't have a built-in system tray. You need a status bar with tray support.

**Solution 1: Use waybar with tray module**
```bash
sudo pacman -S waybar
```

Add to `~/.config/waybar/config`:
```json
"tray": {
  "icon-size": 13,
  "show-passive-items": true
}
```

**Solution 2: Use different status bar**
- `wofi` + tray extension
- `fuzzel` (no tray support)
- `quickshell` (custom tray)

**Note:** JustHireMe may not heavily rely on system tray. Check if it's critical for functionality.

---

## Future Linux Packaging Issues

### Issue 11: No `.desktop` File

**Current state:** Not created automatically by Tauri build

**Solution (future):** Create `JustHireMe.desktop`:
```ini
[Desktop Entry]
Name=JustHireMe
Exec=/usr/bin/justhireme
Icon=/usr/share/icons/JustHireMe.png
Type=Application
Categories=Office;
StartupNotify=true
```

**Place in:** `/usr/share/applications/` or `~/.local/share/applications/`

---

### Issue 12: No Linux Release in GitHub Actions

**Current state:** `.github/workflows/release.yml` only builds Windows

**Solution (future):** Add Linux job to release workflow (see Section 10 in [Future Work](../MIGRATION_GUIDE.md#10-future-work)).

---

## Debugging Tips

### Enable Verbose Logging

**Rust/Tauri:**
```bash
export RUST_LOG=debug
npm run tauri dev
```

**Python/Backend:**
```bash
export LOG_LEVEL=DEBUG
cd backend && uv run python main.py
```

### Check Process Status

```bash
# Check if backend is running
ps aux | grep python | grep main.py

# Check if Tauri is running
ps aux | grep justhireme

# Check network connections
ss -tulpn | grep 1420  # Frontend dev server
ss -tulpn | grep 8000  # Backend (or whatever port)
```

### View All Logs

```bash
# Watch all logs in real-time
tail -f ~/.local/share/JustHireMe/logs/*.log

# Search for errors
grep -i "error\|fail\|exception" ~/.local/share/JustHireMe/logs/*.log
```

### Test Components Independently

**Test backend only:**
```bash
cd backend
uv run python main.py
```

**Test frontend only:**
```bash
npm run dev
# Open http://localhost:1420 in browser
```

**Test Tauri only (if backend already running):**
```bash
npm run tauri dev
```

---

## Getting Help

If you encounter issues not listed here:

1. Check [Tauri Linux Guide](https://tauri.app/v1/guides/getting-started/prerequisites#linux)
2. Review [Arch Wiki: Tauri](https://wiki.archlinux.org/)
3. Search [JustHireMe Issues](https://github.com/vasu-devs/JustHireMe/issues)
4. Create a new issue with:
   - Your Arch/Hyprland version
   - Full error logs
   - Steps to reproduce

---

## Security Issues

### Issue: Plaintext API Keys

**Problem:** API keys (OpenAI, Anthropic, Groq, etc.) stored in **plaintext** in SQLite `settings` table.

**Documentation Claim (project.md, SPEC.md):**
> "AES-256 Encryption using Windows DPAPI or Machine_UID"

**Reality:** Feature **NEVER IMPLEMENTED**. No encryption anywhere in codebase.

**Location:** `backend/db/client.py` - settings stored as plain key-value pairs.

**Risk:** CRITICAL - Any process with file read access can steal API keys.

**Verification:**
```bash
sqlite3 ~/.local/share/JustHireMe/crm.db "SELECT * FROM settings WHERE key LIKE '%api_key%';"
```

**Fix (Future):** Implement encryption or use platform-specific secure storage:
- Windows: DPAPI via `win32crypt` or `keyring`
- Linux: `keyring` library (uses Secret Service/D-Bus)
- macOS: Keychain via `keyring`

**Current Workaround:** Ensure `~/.local/share/JustHireMe/crm.db` has strict permissions (600).

---

## Next Steps

1. Work through [Testing & Validation](09-testing-validation.md) to verify your setup
2. Review [Future Work](10-future-work.md) for planned improvements
3. Consider contributing fixes back to the project
