# Testing & Validation

## Overview

This section covers testing procedures to validate your JustHireMe Linux migration.

## 9.1 Manual Testing Checklist

### 9.1.1 Backend API Tests

**Run pytest suite:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe/backend
uv run python -m pytest tests/test_regressions.py -v
```

**Expected:** All tests pass

**If tests fail:**
- Check test output for missing dependencies
- Ensure backend can start independently (see [Migration Steps](07-migration-steps.md))
- Check if test database is properly configured

**Run specific test files:**
```bash
uv run python -m pytest tests/test_api.py -v
uv run python -m pytest tests/test_graph.py -v
uv run python -m pytest tests/test_mcp_server.py -v
```

---

### 9.1.2 Frontend Build Test

**Build frontend:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm run build
```

**Expected:** `dist/` directory created without errors

**If error:**
- Check TypeScript errors: `npm run typecheck`
- Clear cache: `rm -rf dist node_modules && npm install`
- Check `vite.config.ts` configuration

**Verify build output:**
```bash
ls -la dist/
# Should contain index.html, assets/, etc.
```

---

### 9.1.3 Tauri Check

**Check Rust compilation:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe/src-tauri
cargo check
```

**Expected:** No compilation errors

**If error:**
- Update Rust: `rustup update`
- Clean build: `cargo clean && cargo check`
- Check `Cargo.toml` for correct dependencies

**Full Tauri build (no bundle):**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm run package:fast
```

**Expected:** Binary at `src-tauri/target/debug/justhireme`

---

## 9.2 Integration Testing

### 9.2.1 Full App Test

**Start the complete application:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm run tauri dev
```

**Verification checklist:**

- [ ] Tauri window opens
- [ ] Sidecar port discovered (check logs for `[tauri] Sidecar port: XXXX`)
- [ ] API token discovered (check logs for token)
- [ ] Frontend loads (no blank screen)
- [ ] WebSocket connection established (check browser console F12)
- [ ] No critical errors in logs

**Watch logs during startup:**
```bash
# Terminal 1: Watch Tauri logs
tail -f ~/.local/share/JustHireMe/logs/tauri.log

# Terminal 2: Watch backend logs
tail -f ~/.local/share/JustHireMe/logs/backend.log
```

---

### 9.2.2 Functional Testing

**Test core features:**

1. **Navigation:**
   - [ ] Switch between Dashboard, Pipeline, Activity views
   - [ ] Open Settings modal
   - [ ] Check sidebar navigation works

2. **Job Lead Management:**
   - [ ] Add a manual job lead
   - [ ] View lead details
   - [ ] Update lead status
   - [ ] Delete a lead
   - [ ] Filter leads

3. **Profile Management:**
   - [ ] View profile page
   - [ ] Update skills
   - [ ] Import portfolio (if available)

4. **Document Generation (if enabled):**
   - [ ] Generate resume
   - [ ] Generate cover letter
   - [ ] Check generated files

5. **Settings:**
   - [ ] Update API keys (OpenAI, Anthropic, etc.)
   - [ ] Toggle automation settings
   - [ ] Save settings

---

### 9.2.3 Log Verification

**Check for errors in logs:**
```bash
# Check Tauri logs
grep -i "error\|fail\|exception" ~/.local/share/JustHireMe/logs/tauri.log

# Check backend logs
grep -i "error\|fail\|exception" ~/.local/share/JustHireMe/logs/backend.log
```

**Expected:** No critical errors. Warnings may be acceptable.

**Check startup messages:**
```bash
# Should see something like:
# [tauri] Starting JustHireMe v0.1.7
# [tauri] Sidecar PID: 12345
# [tauri] Sidecar port: 12345
# [tauri] Sidecar token discovered
```

---

## 9.3 Performance Testing

### 9.3.1 Startup Time

**Measure cold startup (first launch):**
```bash
time npm run tauri dev
# Note: First run will be slower (compilation)
```

**Measure warm startup (subsequent launches):**
```bash
# After initial build
time npm run tauri dev
```

**Expected:** 
- Cold start: 10-30 seconds (compilation)
- Warm start: 2-5 seconds

---

### 9.3.2 ML Model Loading

**Check logs for model loading time:**
```bash
grep "model loaded" ~/.local/share/JustHireMe/logs/backend.log
```

**Expected output:**
```
INFO: SentenceTransformer model loaded: all-MiniLM-L6-v2 in 2.XXs
```

**If loading takes too long (>30s):**
- Check if using CPU or GPU (CPU is slower)
- Consider using a smaller model
- Check if model is cached (should be in `~/.cache/huggingface/`)

---

### 9.3.3 Memory Usage

**Check memory usage:**
```bash
# While app is running
ps aux | grep justhireme
ps aux | grep python | grep main.py
```

**Expected:**
- Tauri app: ~100-300 MB
- Python backend: ~200-500 MB (depending on ML models)

**If memory usage is too high:**
- Check for memory leaks (watch over time)
- Consider disabling ML features if not needed
- Use `htop` or `btop` for detailed monitoring

---

## 9.4 Database Testing

### 9.4.1 Database Files Created

**Check database files:**
```bash
ls -la ~/.local/share/JustHireMe/
```

**Expected files:**
- `justhireme.db` (SQLite CRM)
- `justhireme.kuzu` (Kuzu graph)
- `justhireme_lancedb/` (LanceDB vectors)
- `logs/` (log files)

---

### 9.4.2 Database Integrity

**Check SQLite database:**
```bash
sqlite3 ~/.local/share/JustHireMe/justhireme.db ".schema"
```

**Check Kuzu database:**
```python
import kuzu
db = kuzu.Database("~/.local/share/JustHireMe/justhireme.kuzu")
conn = kuzu.Connection(db)
result = conn.execute("SHOW TABLES")
print(result.get_as_df())
```

---

## 9.5 Network Testing

### 9.5.1 Backend API Endpoints

**Test health endpoint:**
```bash
curl http://127.0.0.1:PORT/api/v1/health
```

**Test leads endpoint:**
```bash
curl http://127.0.0.1:PORT/api/v1/leads
```

**Test with authentication (if required):**
```bash
curl -H "Authorization: Bearer TOKEN" http://127.0.0.1:PORT/api/v1/leads
```

---

### 9.5.2 WebSocket Connection

**Test WebSocket connection:**
```javascript
// In browser console (F12)
const ws = new WebSocket('ws://127.0.0.1:PORT/ws?token=TOKEN');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
```

**Expected:** Connection opens successfully, messages received.

---

## 9.6 Automated Testing (Future)

### 9.6.1 Frontend Tests

**Run Vitest (if configured):**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm test
```

**Expected:** Test results in `src/**/*.test.ts` files.

---

### 9.6.2 Backend Tests

**Run full test suite:**
```bash
cd backend
uv run python -m pytest tests/ -v
```

**With coverage:**
```bash
uv run python -m pytest tests/ --cov=backend --cov-report=html
```

---

## 9.7 Validation Checklist

**Complete this checklist to confirm successful migration:**

### Build & Compilation
- [ ] Frontend builds without errors (`npm run build`)
- [ ] Backend dependencies installed (`uv sync --dev`)
- [ ] Tauri compiles without errors (`cargo check` in `src-tauri/`)
- [ ] Full app starts (`npm run tauri dev`)

### Functionality
- [ ] Backend API responds to requests
- [ ] Frontend loads in Tauri window
- [ ] WebSocket connection established
- [ ] Database files created
- [ ] Can add/view/update/delete job leads
- [ ] Settings panel works
- [ ] No critical errors in logs

### Performance
- [ ] Startup time acceptable (<10s warm start)
- [ ] ML model loads successfully
- [ ] Memory usage reasonable (<1GB total)
- [ ] No lag or freezing during normal use

### Logs & Errors
- [ ] Log files created in `~/.local/share/JustHireMe/logs/`
- [ ] No critical errors in Tauri logs
- [ ] No critical errors in backend logs
- [ ] Startup messages logged correctly

---

## Next Steps

1. If all tests pass, your migration is successful! 🎉
2. Review [Future Work](10-future-work.md) for planned improvements
3. Consider contributing Linux fixes back to the project
4. Keep an eye on logs for any issues during daily use
