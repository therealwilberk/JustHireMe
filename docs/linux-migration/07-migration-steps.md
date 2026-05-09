# Migration Steps

## Pre-Migration Checklist

Before starting the migration, ensure:

- [ ] Backup current codebase (`git stash` or create a branch)
- [ ] Document current Windows setup (for reference, if applicable)
- [ ] Install Arch system dependencies (see [Arch/Hyprland Requirements](03-arch-hyprland-requirements.md))
- [ ] Install Rust, Node 24+, Python 3.13, uv
- [ ] Verify Hyprland config (see Section 3.2.3 in [Arch/Hyprland Requirements](03-arch-hyprland-requirements.md))
- [ ] Read [Error Handling Strategy](05-error-handling-strategy.md) and [Logging Strategy](06-logging-strategy.md)

## Step-by-Step Migration

### Step 1: Clone and Install Frontend Dependencies

```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm install
```

**Expected output:** `added XXX packages in Xs`

**If error:**
- Check Node version: `node --version` (should be 24+)
- Clear cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`, then retry

---

### Step 2: Install Backend Dependencies

```bash
cd backend
uv sync --dev
```

**Expected output:** `Resolved XXX packages in Xs`

**If error:**
- Check Python version: `python --version` (should be 3.13+)
- Check uv installation: `uv --version`
- If PyTorch fails: Use CPU-only version (see [Dependency Review](04-dependency-review.md))

---

### Step 3: Verify Tauri Setup

```bash
cd ..
npm run tauri info
```

**Expected output:** Tauri version, Rust version, platform info

**If error:**
- Install Tauri CLI: `cargo install tauri-cli --version "^2"`
- Check Rust installation: `rustc --version`

**Expected output example:**
```
Environment
  › OS: Arch Linux 64-bit
  › Node.js: 24.x.x
  › npm: 10.x.x
  › pnpm: Not installed!
  › yarn: Not installed!
  › rustup: installed
  › rustc: 1.85.0 (x86_64-unknown-linux-gnu)
  › cargo: 1.85.0
  › Rust toolchain: stable-x86_64-unknown-linux-gnu 
  › Tauri CLI: 2.15.0
```

---

### Step 4: Test Backend Independently

```bash
cd backend
uv run python main.py
```

**Expected output:**
```
INFO:     JustHireMe backend starting...
INFO:     FastAPI listening on port 12345
PORT:12345
JHM_TOKEN=abc123...
```

**If error:**
- Check logs for missing dependencies
- Verify database initialization
- Check port availability (may need to kill existing processes on that port)

**Kill existing backend if needed:**
```bash
# Find process using port 8000 (or whatever port is configured)
lsof -i :8000
kill -9 <PID>
```

---

### Step 5: Test Frontend + Backend (Dev Mode)

**Terminal 1: Start backend**
```bash
cd /home/kamaa/dev/code-base/JustHireMe/backend
uv run python main.py
```

**Terminal 2: Start frontend dev server**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm run dev
```

**Expected:** Vite dev server at `http://localhost:1420`

**If error:**
- Check if port 1420 is available
- Check `vite.config.ts` for correct configuration
- View browser console for errors (F12)

---

### Step 6: Test Full Tauri App

```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm run tauri dev
```

**Expected:** Tauri window opens with React frontend

**If error:**
- Check `src-tauri/tauri.conf.json` devUrl setting
- Ensure backend is running first (or Tauri will start it)
- Check Rust compilation errors: `cd src-tauri && cargo check`

**Debug Tauri issues:**
```bash
cd src-tauri
cargo clean  # Clean build artifacts
cargo check  # Check for compilation errors
```

---

### Step 7: Build for Production (No Bundle)

```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm run package:fast
```

**Expected:** Binary at `src-tauri/target/debug/justhireme` (or `justhireme.exe` on Windows)

**If error:**
- Check `tauri.conf.json` beforeBuildCommand and beforeDevCommand
- Ensure frontend is built: `npm run build`

---

### Step 8: Build Linux Package (Future)

```bash
# After adding Linux targets to tauri.conf.json
npm run package:linux  # (to be created)
```

**Note:** This step requires modifying `tauri.conf.json` to add Linux targets (see Section 10 in [Future Work](../MIGRATION_GUIDE.md#10-future-work)).

---

## Post-Migration Verification

After completing the migration steps, verify:

- [ ] Frontend loads at `localhost:1420`
- [ ] Backend starts and outputs `PORT:` and `JHM_TOKEN=`
- [ ] Tauri window opens and connects to backend
- [ ] WebSocket connection established (check browser console)
- [ ] Database files created (`~/.local/share/JustHireMe/`)
- [ ] No critical errors in logs
- [ ] Can navigate through app views (Dashboard, Pipeline, etc.)
- [ ] Settings panel works
- [ ] Can add a manual job lead (test the full flow)

### Verification Commands

**Check backend API:**
```bash
curl http://127.0.0.1:PORT/api/v1/health  # Replace PORT with actual port
```

**Check log files:**
```bash
ls -la ~/.local/share/JustHireMe/logs/
cat ~/.local/share/JustHireMe/logs/backend.log
```

**Check database files:**
```bash
ls -la ~/.local/share/JustHireMe/
```

---

## Common Issues and Solutions

### Issue: "sidecar port not yet discovered"

**Cause:** Backend not starting or not outputting `PORT:` line.

**Solution:**
1. Test backend manually: `cd backend && uv run python main.py`
2. Check Python path in `lib.rs` (line 56-60)
3. Ensure `backend/.venv/bin/python` exists or `uv` is in PATH

### Issue: "Failed to spawn Python sidecar"

**Cause:** Python binary not found or permissions issue.

**Solution:**
```bash
# Check if Python exists
ls -la backend/.venv/bin/python

# Make executable if needed
chmod +x backend/.venv/bin/python

# Or use system Python
uv venv --python /usr/bin/python
```

### Issue: WebSockets not connecting

**Cause:** CSP in `tauri.conf.json` blocking connections.

**Solution:** Check `tauri.conf.json` line 23:
```json
"connect-src http://127.0.0.1:* ws://127.0.0.1:*"
```

Ensure this includes your backend port.

### Issue: Blank Tauri window

**Cause:** Frontend not loading or dev server not running.

**Solution:**
1. Check if frontend dev server is running: `npm run dev`
2. Check `tauri.conf.json` devUrl: `"devUrl": "http://localhost:1420"`
3. Check browser console in Tauri window (if dev tools available)

---

## Next Steps

1. If all verification passes, proceed to [Known Issues](08-known-issues.md) for troubleshooting
2. Set up [Testing & Validation](09-testing-validation.md)
3. Consider contributing Linux improvements back to upstream

---

## Quick Reference

| Step | Command | Expected Result |
|------|---------|-----------------|
| 1 | `npm install` | Frontend deps installed |
| 2 | `cd backend && uv sync --dev` | Backend deps installed |
| 3 | `npm run tauri info` | Tauri config displayed |
| 4 | `cd backend && uv run python main.py` | Backend starts, shows PORT and TOKEN |
| 5 | `npm run dev` | Vite dev server at :1420 |
| 6 | `npm run tauri dev` | Tauri window opens |
| 7 | `npm run package:fast` | Production binary built |

---
