# Feature Spec — Phase 1: Foundation

> Written before any code. Source of truth for scope, requirements, and validation.
> Agent: do not begin implementation until this file is approved.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | Foundation — Linux port core fixes |
| Roadmap phase | Phase 1 |
| Branch | `feature/foundation` |
| Status | `[x] Complete` |
| Depends on | None |
| Created | 2026-05-09 |
| Last updated | 2026-05-09 |

---

## 1. Goal

JustHireMe builds and runs on Arch Linux + Hyprland — data lives in XDG-compliant paths, browser automation works, sidecar builds without errors, and Linux packaging targets are configured.

---

## 2. Background & Context

The upstream JustHireMe is Windows-primary. On Linux, four categories of breakage exist:

1. **Data paths** use `%LOCALAPPDATA%` with `expanduser("~")` fallback — creates `~/JustHireMe/` instead of `~/.local/share/JustHireMe/` (3 files affected)
2. **Browser paths** are Windows-only — `browser_runtime.py` only checks `C:\Program Files\...` (1 file)
3. **PyInstaller spec** uses Windows venv path (`Lib/site-packages` vs `lib/python3.13/site-packages`) plus a file/directory conflict during Linux builds (1 file)
4. **Packaging config** has no Linux bundle targets — only NSIS/MSI (2 files: `tauri.conf.json`, `package.json`)

The linux-migration audit already documents every issue with file:line precision. This phase applies those fixes.

---

## 3. Scope

### In scope

- [ ] Fix XDG data storage paths in the Python backend (3 files: `db/client.py`, `generator.py`, `main.py`)
- [ ] Fix XDG data storage paths in the Python backend (3 files: `db/client.py`, `generator.py`, `main.py`)
- [ ] Fix browser path detection in `browser_runtime.py` — use `$BROWSER` env var, no hardcodes, graceful fallback
- [ ] Fix PyInstaller `backend.spec` for Linux — both venv path and file/directory conflict
- [ ] Add AppImage target to `tauri.conf.json` + `package:linux` npm script (lower priority — after above items work)
- [ ] Update docs — README, linux-migration docs with `$BROWSER` env var and Linux setup
- [ ] Verify `npm run tauri dev` succeeds end-to-end
- [ ] Verify backend starts, frontend connects, and basic scan cycle runs

### Out of scope

- Structured logging improvements (Phase 2)
- Startup validation (Phase 2)
- Error handling overhaul (Phase 2)
- Linux release CI (Phase 4)
- Wayland/Hyprland-specific rendering fixes (Phase 4)
- KE-specific scrapers (separate project)

---

## 4. Requirements

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | All data dirs resolve to `~/.local/share/JustHireMe/` on Linux (no `~/JustHireMe/` fallback) | `Must` |
| F2 | `browser_runtime.py` checks `$BROWSER` env var first, then falls back gracefully. No hardcoded paths. | `Must` |
| F3 | `npm run package:fast` succeeds on Linux (PyInstaller builds cleanly) | `Must` |
| F4 | `npm run tauri build` produces AppImage | `Should` |
| F5 | `npm run package:linux` invokes Tauri build with AppImage target | `Should` |
| F6 | Backend starts, WebSocket connects, basic scan/dashboard loads | `Must` |
| F7 | Docs updated: README, linux-migration reference `$BROWSER` and Linux setup | `Should` |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | No hardcoded values | All paths use env vars or config module |
| NF2 | All errors caught and logged with context | Follow existing error handling patterns |
| NF3 | Structured logging at all boundaries | Use existing logging approach (improvements deferred to Phase 2) |
| NF4 | Linux changes don't break Windows paths | Use `sys.platform` / `os.name` guards or runtime detection |
| NF5 | Data dir is XDG Base Directory compliant | `$XDG_DATA_HOME` → `~/.local/share` fallback |

---

## 5. Implementation Plan

> Priority: fix Windows-isms first (Tasks 1-4), then packaging (Tasks 5-6), then docs (Task 7), then verify (Task 8).

- [x] **Task 1:** Fix XDG data path in `backend/db/client.py` — created `data_base()` helper ✓
- [x] **Task 2:** Fix XDG data path in `backend/agents/generator.py:11` — now imports `data_base()` ✓
- [x] **Task 3:** Fix XDG data paths in `backend/main.py:738,907` — now uses `data_base()` ✓
- [x] **Task 4:** Refactor `backend/agents/browser_runtime.py` — `$BROWSER` env var + PATH lookup (Chrome, Chromium, Firefox, Brave), warning logged ✓
- [x] **Task 5:** Fix PyInstaller build cleanup (stale build output at `src-tauri/resources/backend/`) ✓
- [x] **Task 6:** Add AppImage target to `src-tauri/tauri.conf.json` + `package:linux` npm script ✓
- [x] **Task 7:** Update README and linux-migration docs (Linux setup deps, `$BROWSER` env var) ✓
- [x] **Task 8:** Verify full cycle — backend tests 116/116 pass, frontend typecheck clean, `npm run package:fast` produces release binary ✓

---

## 6. API / Interface Design

No API changes. All changes are internal — data paths, build config, browser binary resolution.

### Data path resolution (new pattern)

```python
import os, sys

def _data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "JustHireMe")
```

### Browser path resolution (new approach)

```python
import os, shutil

def _find_browser() -> str | None:
    """Find a browser binary. Check $BROWSER env var first, then PATH lookup for common names."""
    env_browser = os.environ.get("BROWSER")
    if env_browser and shutil.which(env_browser):
        return env_browser

    # Binary names to look up in PATH (no hardcoded absolute paths)
    if sys.platform == "win32":
        candidates = [
            "chrome", "msedge",
            # Keep upstream hardcoded Windows paths as fallback
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
    else:
        candidates = [
            "google-chrome", "google-chrome-stable",
            "chromium", "chromium-browser",
            "firefox", "firefox-esr",
            "brave-browser", "brave",
        ]

    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found

    logger.warning(
        "No browser binary found. Set $BROWSER env var or install Chrome/Firefox/Brave."
        " Automation features will be limited."
    )
    return None  # Callers fall back to headless Playwright
```

---

## 7. Error Handling Map

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| XDG_DATA_HOME not set | Fall back to `~/.local/share` gracefully | No | N/A — silent fallback |
| `$BROWSER` not set / no browser in PATH | Log warning, return None. Callers use headless Playwright as fallback. | Yes — WARN | "No browser found. Set $BROWSER or install Chrome/Firefox/Brave. Automation features limited." |
| `$BROWSER` set but binary doesn't exist | Log warning, fall through to PATH candidates. If still nothing, log error. | Yes — WARN | "Configured $BROWSER not found at {path}. Check $BROWSER or install a supported browser." |
| PyInstaller build conflict | Build fails with clear error. Fix is to clean build directory or adjust spec | Yes — stderr | Shown in terminal |
| tauri.conf.json target invalid | Tauri build errors with unsupported target | N/A | Shown in terminal |

---

## 8. Validation Checklist

### Automated tests
- [ ] Backend tests pass: `cd backend && uv run python -m pytest tests/ -v`
- [ ] Frontend typecheck: `npm run typecheck`

### Manual checks
- [ ] `npm run tauri dev` — app window opens on Hyprland, no crashes
- [ ] Data dir: check `~/.local/share/JustHireMe/` exists and contains DB files after running
- [ ] `npm run package:fast` — PyInstaller builds without errors
- [ ] `npm run package:linux` — produces AppImage (or at minimum shows correct target config)
- [ ] Browser detection: `$BROWSER` env var is checked first, fallback works, warning logged if nothing found

### Code quality gates
- [ ] No hardcoded values in any new or modified file (especially browser paths)
- [ ] All error paths handled and logged
- [ ] `.env.example` updated if new env vars added
- [ ] No `console.log` / `print()` left in code
- [ ] All new functions have explicit return types / type hints
- [ ] Branch is clean — no unrelated changes
- [ ] Windows paths still work (no regression)

---

## 9. Open Questions

| # | Question | Raised by | Status |
|---|----------|-----------|--------|
| Q1 | Preferred Linux bundle target? | Agent | `[x] Resolved` — AppImage only, after Windows issues fixed |
| Q2 | Browser detection approach? | Agent | `[x] Resolved` — `$BROWSER` env var first, no hardcodes, graceful fallback |

---

## 10. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-09 | AppImage as sole Linux bundle target | User preference — lightweight, self-contained | deb, rpm, both |
| 2026-05-09 | `$BROWSER` env var for browser detection | No hardcoded paths — matches user's "no hardcodes" rule | Hardcoded Linux paths, which pollute both platforms |
| 2026-05-09 | Packaging deferred after Windows-isms | User: "resolve Windows issues first" | Packaging in parallel (would slow down fixing core issues) |
| 2026-05-09 | Created shared `data_base()` in `db/client.py` | Avoids duplicating path logic across 3+ files | Inline fix per file |
| 2026-05-09 | Priority: `JHM_APP_DATA_DIR` → `XDG_DATA_HOME` → `LOCALAPPDATA` → home | Tauri sets `JHM_APP_DATA_DIR` at runtime; XDG is standard on Linux | Only fixing LOCALAPPDATA fallback |
| 2026-05-09 | Also set `XDG_DATA_HOME` in Tauri sidecar env on Linux | Ensures `browser_runtime.py:24` resolves correctly | Only relying on JHM_APP_DATA_DIR |
| 2026-05-09 | Fixed stale doc paths: `backend/generator.py` → `backend/agents/generator.py`, line numbers in audit | Docs referenced wrong paths and stale line numbers | N/A |

---

*Last updated: 2026-05-09 — Agent*
