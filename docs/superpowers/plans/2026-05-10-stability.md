# Phase 2 — Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backend is reliable, debuggable, and testable — tests are maintainable, startup validates real dependencies, ghost mode can't race with manual operations, sidecar port discovery can't hang forever.

**Architecture:** Seven independent work streams: (1-4) test infrastructure refactor + new unit tests, (5) health endpoint enhancement, (6) Rust sidecar timeout, (7) frontend retry ceiling, (8) ghost mode asyncio lock. Tasks 1-4 are parallel. Tasks 5-8 each depend on nothing but are sequential for reviewability.

**Tech Stack:** Python 3.13 (unittest, mock, FastAPI), Rust (Tauri 2, tokio), TypeScript (React hooks)

**Spec:** `docs/specs/Features/stability.md`

---

### Task 1: Extract shared fakes into `tests/fakes.py`

**Files:**
- Create: `backend/tests/fakes.py`
- Modify: `backend/tests/test_api.py:13-80`
- Modify: `backend/tests/test_graph.py:13-80`
- Modify: `backend/tests/test_regressions.py:14-109`
- Test ad-hoc: run existing tests to confirm no regressions

- [ ] **Step 1: Create `tests/fakes.py` with all shared fake classes**

```python
import os
import sys
import types
from unittest import mock


class _FakeResult:
    def has_next(self):
        return False

    def get_next(self):
        return [0]


class _FakeConnection:
    def execute(self, *_args, **_kwargs):
        return _FakeResult()


class _FakeSqlConnection:
    def executescript(self, *_args, **_kwargs):
        return self

    def execute(self, *_args, **_kwargs):
        return self

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def commit(self):
        return None

    def close(self):
        return None


class _FakeVectorStore:
    def list_tables(self):
        return []

    def create_table(self, *_args, **_kwargs):
        return None

    def open_table(self, *_args, **_kwargs):
        return self

    def add(self, *_args, **_kwargs):
        return None


class _FakeSemanticSearch:
    def __init__(self, rows):
        self.rows = list(rows)
        self._limit = len(self.rows)

    def metric(self, *_args, **_kwargs):
        return self

    def where(self, clause, *_args, **_kwargs):
        self.rows = [row for row in self.rows if f"'{row['id']}'" in clause]
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def to_list(self):
        return self.rows[: self._limit]


class _FakeSemanticTable:
    def __init__(self, rows):
        self.rows = rows

    def search(self, *_args, **_kwargs):
        return _FakeSemanticSearch(self.rows)


class _FakeSemanticStore:
    def __init__(self, tables):
        self.tables = tables

    def list_tables(self):
        return list(self.tables)

    def open_table(self, name):
        return _FakeSemanticTable(self.tables[name])


def _install_storage_fakes():
    """Replace storage backends with fakes. Must call before importing any backend module."""
    mock.patch.object(os, "makedirs", return_value=None).start()
    sys.modules.setdefault(
        "kuzu",
        types.SimpleNamespace(
            Database=lambda _path: object(),
            Connection=lambda _db: _FakeConnection(),
        ),
    )
    sys.modules["sqlite3"] = types.SimpleNamespace(
        connect=lambda _path: _FakeSqlConnection()
    )
    sys.modules.setdefault(
        "lancedb",
        types.SimpleNamespace(
            LanceDBConnection=_FakeVectorStore,
            connect=lambda _path: _FakeVectorStore(),
        ),
    )
```

- [ ] **Step 2: Update `test_api.py` — replace class defs with import, remove global lambda**

Replace the module-level content before the `# ── Import app` line:

```python
# ── Must run before any backend module is imported ───────────────────────────
os.environ["LOCALAPPDATA"] = str(Path(__file__).resolve().parent)

from tests.fakes import _install_storage_fakes

_install_storage_fakes()

# ── Import app and override the randomly-generated token ────────────────────
```

Delete all lines from `class _FakeResult` through the old `_install_storage_fakes()` definition + call.

- [ ] **Step 3: Update `test_graph.py` — same pattern**

```python
# ── Must run before any backend module is imported ───────────────────────────
os.environ["LOCALAPPDATA"] = str(Path(__file__).resolve().parent)

from tests.fakes import _install_storage_fakes

_install_storage_fakes()
```

Delete all fake class defs and the old `_install_storage_fakes()`.

- [ ] **Step 4: Update `test_regressions.py` — same pattern**

```python
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


os.environ["LOCALAPPDATA"] = str(Path(__file__).resolve().parent)

from tests.fakes import _install_storage_fakes

_install_storage_fakes()
```

Delete all fake class defs (including `_FakeSemantic*`) and the old `_install_storage_fakes()`.

- [ ] **Step 5: Run tests to confirm no regressions**

Run: `cd backend && uv run python -m pytest tests/ -v`
Expected: All tests pass (no change in test count vs baseline)

- [ ] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "chore: extract shared test fakes into tests/fakes.py"
```

---

### Task 2: Remove global `os.makedirs` monkey-patch

**Files:**
- Already done — `_install_storage_fakes()` in `tests/fakes.py` includes the mock
- Verify: no `os.makedirs = lambda` remains in any test file

**Note:** This was done as part of Task 1 (the patch is inside `_install_storage_fakes()` in `fakes.py`). The global lambda lines were removed from all three test files in Task 1. Verify clean state.

- [ ] **Step 1: Confirm zero `os.makedirs = lambda` in test files**

Run: `rg "os.makedirs = lambda" backend/tests/`
Expected: no matches

- [ ] **Step 2: Commit (or amend previous commit)**

If needed: `git commit -m "chore: replace global os.makedirs monkey-patch with targeted mock in _install_storage_fakes"`

(If already clean, move on)

---

### Task 3: Unit tests for `data_base()`

**Files:**
- Create: `backend/tests/test_paths.py`

- [ ] **Step 1: Create `test_paths.py` with data_base tests**

```python
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests.fakes import _install_storage_fakes

_install_storage_fakes()

from db.client import data_base


class DataBaseTests(unittest.TestCase):
    """data_base() resolves the app data directory via priority chain."""

    def test_jhm_app_data_dir_takes_priority(self):
        """JHM_APP_DATA_DIR env var is checked first."""
        with mock.patch.dict(os.environ, {"JHM_APP_DATA_DIR": "/custom/path"}, clear=False):
            result = data_base()
        self.assertEqual(result, "/custom/path")

    def test_xdg_data_home_used_on_linux_when_jhm_not_set(self):
        """On Linux, XDG_DATA_HOME is used when JHM_APP_DATA_DIR is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/xdg/data"}, clear=False):
                with mock.patch("sys.platform", "linux"):
                    result = data_base()
        self.assertEqual(result, "/xdg/data/JustHireMe")

    def test_localappdata_used_on_windows_when_jhm_not_set(self):
        """On Windows, LOCALAPPDATA is used when JHM_APP_DATA_DIR is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": R"C:\Users\test\AppData\Local"}, clear=False):
                with mock.patch("sys.platform", "win32"):
                    result = data_base()
        self.assertEqual(result, R"C:\Users\test\AppData\Local\JustHireMe")

    def test_fallback_to_home_when_no_env_var_set_on_windows(self):
        """Fallback to expanduser('~') on Windows when no relevant env vars."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.platform", "win32"):
                with mock.patch("os.path.expanduser", return_value="/home/user"):
                    result = data_base()
        self.assertEqual(result, "/home/user/JustHireMe")

    def test_fallback_to_xdg_default_on_linux_when_no_env_vars(self):
        """On Linux, fallback to ~/.local/share when XDG_DATA_HOME is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.platform", "linux"):
                with mock.patch("os.path.expanduser", return_value="/home/user"):
                    result = data_base()
        self.assertEqual(result, "/home/user/.local/share/JustHireMe")


class EnsureDirTests(unittest.TestCase):
    """_ensure_dir fallback behaviour when os.makedirs fails."""

    def test_fallback_dir_used_when_makedirs_fails(self):
        """When os.makedirs raises, _ensure_dir tries a _store suffix fallback."""
        from db.client import _ensure_dir

        with mock.patch("os.makedirs", side_effect=PermissionError("denied")):
            result = _ensure_dir("/data/jhm")
        self.assertEqual(result, "/data/jhm_store")
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_paths.py -v`
Expected: 6 tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_paths.py
git commit -m "test: add unit tests for data_base() and _ensure_dir"
```

---

### Task 4: Unit tests for `chromium_executable()`

**Files:**
- Modify: `backend/tests/test_paths.py` (append to file)

- [ ] **Step 1: Add chromium_executable tests to test_paths.py**

Append to `test_paths.py` (after the `EnsureDirTests` class):

```python
class ChromiumExecutableTests(unittest.TestCase):
    """chromium_executable() resolves browser binary via priority chain."""

    def test_browser_env_var_resolved_via_path(self):
        """$BROWSER env var is checked first and resolved via shutil.which."""
        with mock.patch("shutil.which", return_value="/usr/bin/firefox"):
            with mock.patch.dict(os.environ, {"BROWSER": "firefox"}, clear=False):
                from agents.browser_runtime import chromium_executable
                result = chromium_executable()
        self.assertEqual(result, "/usr/bin/firefox")

    def test_browser_env_var_not_found_logs_warning(self):
        """When $BROWSER is set but shutil.which returns None, log warning."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch.dict(os.environ, {"BROWSER": "nonexistent"}, clear=False):
                with mock.patch("agents.browser_runtime._log.warning") as mock_warn:
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertIsNone(result)
        mock_warn.assert_called_once()

    def test_playwright_chromium_executable_env(self):
        """PLAYWRIGHT_CHROMIUM_EXECUTABLE is checked if $BROWSER not set."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch("os.path.exists", return_value=True):
                with mock.patch.dict(os.environ, {
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE": "/custom/chrome",
                }, clear=False):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertEqual(result, "/custom/chrome")

    def test_playwright_env_skipped_when_path_does_not_exist(self):
        """PLAYWRIGHT_CHROMIUM_EXECUTABLE is skipped if the file doesn't exist."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch("os.path.exists", return_value=False):
                with mock.patch.dict(os.environ, {
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE": "/missing/chrome",
                }, clear=False):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertIsNone(result)

    def test_linux_candidates_checked_via_shutil_which(self):
        """On Linux, common browser names are checked via shutil.which."""
        def fake_which(name):
            lookup = {
                "google-chrome": "/usr/bin/google-chrome",
                "chromium": None,
                "firefox": None,
            }
            return lookup.get(name)

        with mock.patch("shutil.which", side_effect=fake_which):
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("os.name", "posix"):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertEqual(result, "/usr/bin/google-chrome")

    def test_returns_none_when_no_browser_found(self):
        """When no browser is found through any path, return None."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("os.name", "posix"):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_paths.py -v`
Expected: 12 tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_paths.py
git commit -m "test: add unit tests for chromium_executable()"
```

---

### Task 5: Enhance `/health` endpoint

**Files:**
- Modify: `backend/main.py:646-653`

- [ ] **Step 1: Modify `health()` to return dependency probes**

Replace the `health()` function:

```python
@app.get("/health", dependencies=[])
async def health():
    from agents.browser_runtime import chromium_executable
    from db.client import get_settings

    db_status = "ok"
    db_latency = 0.0
    try:
        import sqlite3
        from db.client import sql
        t0 = time.monotonic()
        sqlite3.connect(sql).execute("SELECT 1")
        db_latency = round((time.monotonic() - t0) * 1000, 1)
    except Exception as exc:
        db_status = "error"
        _log.warning("health: db probe failed — %s", exc)

    browser_path = chromium_executable()
    browser_status = "found" if browser_path else "not_found"

    cfg = get_settings()
    configured_providers = []
    for key, val in cfg.items():
        if key.endswith("_api_key") or key.endswith("_key") or key.endswith("_token"):
            if val:
                provider = key.replace("_api_key", "").replace("_key", "").replace("_token", "")
                configured_providers.append(provider)
    api_keys_status = "configured" if configured_providers else "missing"

    return {
        "status": "alive",
        "uptime_seconds": round(time.monotonic() - _UP, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "log_level": os.environ.get("JHM_LOG_LEVEL", "INFO"),
        "dependencies": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency,
            },
            "browser": {
                "status": browser_status,
                "path": browser_path,
            },
            "api_keys": {
                "status": api_keys_status,
                "configured_providers": configured_providers,
            },
        },
    }
```

Remove the `# Comment on stability-task5` marker line.

- [ ] **Step 2: Run existing tests to check health endpoint not broken**

Run: `cd backend && uv run python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add dependency probes to /health endpoint"
```

---

### Task 6: Add timeout to Rust sidecar stdout scanning

**Files:**
- Modify: `src-tauri/Cargo.toml`
- Modify: `src-tauri/src/lib.rs:259-322`

- [ ] **Step 1: Add tokio dependency to Cargo.toml**

Uncomment the tokio dep line:

```toml
tokio = { version = "1", features = ["time"] }
```

Remove the `# Comment on stability-task6` comment lines.

- [ ] **Step 2: Restructure sidecar stdout loop with timeout**

Replace the `tauri::async_runtime::spawn(async move { ... })` block at `lib.rs:280-322`:

```rust
let app_handle = handle.clone();
tauri::async_runtime::spawn(async move {
    use tokio::time::timeout;
    use std::time::Duration;

    let startup_deadline = Duration::from_secs(15);
    let mut port_received = false;
    let mut token_received = false;

    loop {
        match timeout(startup_deadline, rx.recv()).await {
            Ok(Some(CommandEvent::Stdout(b))) => {
                let line = String::from_utf8_lossy(&b).trim().to_string();
                if let Some(port_str) = line.strip_prefix("PORT:") {
                    if let Ok(port) = port_str.parse::<u16>() {
                        if let Ok(mut g) = app_handle.state::<SidecarPort>().0.lock() {
                            *g = Some(port);
                        }
                        let _ = app_handle.emit("sidecar-port", port);
                        eprintln!("[tauri] Sidecar port: {port}");
                        port_received = true;
                    }
                } else if let Some(token) = line.strip_prefix("JHM_TOKEN=") {
                    if let Ok(mut g) = app_handle.state::<ApiTokenState>().0.lock() {
                        *g = Some(token.to_string());
                    }
                    let _ = app_handle.emit("sidecar-token", token.to_string());
                    token_received = true;
                }
                if port_received && token_received {
                    break;
                }
            }
            Ok(Some(CommandEvent::Stderr(b))) => {
                let line = String::from_utf8_lossy(&b).trim().to_string();
                if !line.is_empty() {
                    eprintln!("[sidecar] {line}");
                    if let Ok(mut guard) = app_handle.state::<SidecarError>().0.lock() {
                        *guard = Some(line.clone());
                    }
                    let _ = app_handle.emit("sidecar-error", line);
                }
            }
            Ok(Some(CommandEvent::Terminated(s))) => {
                let msg = format!("Sidecar terminated before startup: {:?}", s.code);
                eprintln!("[tauri] {msg}");
                if let Ok(mut guard) = app_handle.state::<SidecarError>().0.lock() {
                    *guard = Some(msg.clone());
                }
                let _ = app_handle.emit("sidecar-error", msg);
                let _ = app_handle.emit("sidecar-terminated", ());
                return;
            }
            Ok(None) => {
                eprintln!("[tauri] Sidecar stdout channel closed");
                return;
            }
            Err(_) => {
                let msg = "Sidecar startup timed out".to_string();
                eprintln!("[tauri] {msg}");
                if let Ok(mut guard) = app_handle.state::<SidecarError>().0.lock() {
                    *guard = Some(msg.clone());
                }
                let _ = app_handle.emit("sidecar-error", msg);
                if let Ok(mut guard) = app_handle.state::<SidecarChild>().0.lock() {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                    }
                }
                let _ = app_handle.emit("sidecar-terminated", ());
                return;
            }
            _ => {}
        }
    }

    // Both port and token received — forward remaining events indefinitely
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(b) => {
                /* ignore — startup info already consumed */
            }
            CommandEvent::Stderr(b) => {
                let line = String::from_utf8_lossy(&b).trim().to_string();
                if !line.is_empty() {
                    eprintln!("[sidecar] {line}");
                }
            }
            CommandEvent::Terminated(s) => {
                eprintln!("[tauri] Sidecar terminated: {:?}", s.code);
                let _ = app_handle.emit("sidecar-terminated", ());
                break;
            }
            _ => {}
        }
    }
});
```

Remove the `// Comment on stability-task6` marker lines.

- [ ] **Step 3: Build to verify Rust compiles**

Run: `cd src-tauri && cargo check`
Expected: Compiles without errors

- [ ] **Step 4: Commit**

```bash
git add src-tauri/Cargo.toml src-tauri/src/lib.rs
git commit -m "fix: add 15s timeout to sidecar stdout port/token scan"
```

---

### Task 7: Add retry ceiling to frontend polling

**Files:**
- Modify: `src/hooks/useWS.ts:87-89`

- [ ] **Step 1: Add retry ceiling to polling loop**

Replace the polling section in `useWS.ts`:

```typescript
const MAX_SIDECAR_RETRIES = 30;
let retryCount = 0;

await syncSidecar();
poll = window.setInterval(() => {
  if (cancelled) return;
  if (retryCount >= MAX_SIDECAR_RETRIES) {
    setSidecarError("Sidecar failed to start — check logs");
    if (poll !== undefined) window.clearInterval(poll);
    return;
  }
  retryCount++;
  if (!token || !currentPort) void syncSidecar();
}, 1000);
```

- [ ] **Step 2: Tear down event listeners on exhaustion**

Also update the cleanup to unregister listeners when the retry ceiling is hit. The event listener tear-down should happen inside the `if (retryCount >= MAX_SIDECAR_RETRIES)` block:

```typescript
if (retryCount >= MAX_SIDECAR_RETRIES) {
  setSidecarError("Sidecar failed to start — check logs");
  if (poll !== undefined) window.clearInterval(poll);
  unlisten?.();  // tear down event listeners
  return;
}
```

Remove the `// Comment on stability-task7` marker lines.

- [ ] **Step 3: Verify frontend typecheck**

Run: `npm run typecheck`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add src/hooks/useWS.ts
git commit -m "fix: add 30-retry ceiling to sidecar port/token polling"
```

---

### Task 8: Add ghost mode concurrency lock

**Files:**
- Modify: `backend/main.py` (6 insertion points)

- [ ] **Step 1: Add `_ghost_lock` module-level global**

Near other globals (after `_reevaluate_task`):

```python
_scan_stop = asyncio.Event()
_scan_task: asyncio.Task | None = None
_reevaluate_stop = asyncio.Event()
_reevaluate_task: asyncio.Task | None = None
_ghost_lock = asyncio.Lock()
```

Remove the `# Comment on stability-task8: add _ghost_lock` marker.

- [ ] **Step 2: Guard `_ghost_tick()` entry**

```python
async def _ghost_tick():
    try:
        await asyncio.wait_for(_ghost_lock.acquire(), timeout=0)
    except asyncio.TimeoutError:
        _log.info("ghost tick skipped — another scan or re-evaluation is running")
        return
    try:
        # ... existing body ...
    finally:
        _ghost_lock.release()
```

Remove the `# Comment on stability-task8: acquire _ghost_lock` marker in `_ghost_tick()`.

- [ ] **Step 3: Guard `scan()` HTTP handler**

```python
@app.post("/api/v1/scan")
async def scan():
    if _ghost_lock.locked():
        raise HTTPException(status_code=409, detail="Scan already in progress (ghost mode active)")
    global _scan_task
    # ... rest unchanged ...
```

Remove the `# Comment on stability-task8: check _ghost_lock.locked()` marker at `scan()`.

- [ ] **Step 4: Guard `reevaluate_jobs()` HTTP handler**

```python
@app.post("/api/v1/leads/reevaluate")
async def reevaluate_jobs():
    if _ghost_lock.locked():
        raise HTTPException(status_code=409, detail="Re-evaluation already in progress (ghost mode active)")
    global _reevaluate_task
    # ... rest unchanged ...
```

Remove the marker at `reevaluate_jobs()`.

- [ ] **Step 5: Guard `_run_scan_task()`**

```python
async def _run_scan_task():
    try:
        await asyncio.wait_for(_ghost_lock.acquire(), timeout=0)
    except asyncio.TimeoutError:
        _log.warning("scan task skipped — ghost lock held")
        return
    global _scan_task
    try:
        await _run_scan()
    except Exception as exc:
        _log.error("scan failed: %s", exc)
        await cm.broadcast({"type": "agent", "event": "eval_done", "msg": f"Scan failed: {exc}"})
    finally:
        _scan_task = None
        _ghost_lock.release()
```

Remove the marker at `_run_scan_task()`.

- [ ] **Step 6: Guard `_run_reevaluate_jobs_task()`**

```python
async def _run_reevaluate_jobs_task():
    try:
        await asyncio.wait_for(_ghost_lock.acquire(), timeout=0)
    except asyncio.TimeoutError:
        _log.warning("reevaluate task skipped — ghost lock held")
        return
    global _reevaluate_task
    try:
        await _run_reevaluate_jobs()
    except Exception as exc:
        _log.error("reevaluate failed: %s", exc)
        await cm.broadcast({"type": "agent", "event": "reeval_done", "msg": f"Re-evaluation failed: {exc}"})
    finally:
        _reevaluate_task = None
        _ghost_lock.release()
```

Remove the marker at `_run_reevaluate_jobs_task()`.

- [ ] **Step 7: Run tests**

Run: `cd backend && uv run python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/main.py
git commit -m "feat: add ghost mode concurrency lock via asyncio.Lock"
```

---

## Verification Pass

- [ ] Run full test suite: `cd backend && uv run python -m pytest tests/ -v` — all pass
- [ ] Frontend typecheck: `npm run typecheck` — clean
- [ ] Rust build: `cd src-tauri && cargo check` — compiles
- [ ] Grep for stale comments: `rg "Comment on stability-" backend/ src/` — no matches
- [ ] Grep for `os.makedirs = lambda`: `rg "os\.makedirs = lambda" backend/tests/` — no matches
- [ ] Verify new files committed: `tests/fakes.py`, `test_paths.py`
- [ ] Verify docs updated: `stability.md` Last updated date bumped
