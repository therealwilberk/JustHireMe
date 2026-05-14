# Map: tauri
**File:** `docs/maps/tauri.md`
**Codebase path(s):** `src-tauri/src/lib.rs`, `src-tauri/src/main.rs`, `src-tauri/tauri.conf.json`, `src-tauri/capabilities/`
**Files in scope:** 5
**Total lines:** ~504
**Generated:** 2026-05-15

---

## 1. Unit summary

The Tauri unit is the desktop shell. It owns the Tauri application lifecycle (build, window, run loop), Python sidecar process management (spawn, stdout protocol parsing, health monitoring, graceful shutdown), IPC commands that the frontend uses to discover the backend's port and API token, and the bundle/updater configuration. It depends on `tauri-plugin-shell` (sidecar spawning), `tauri-plugin-notification` (desktop alerts), `tauri-plugin-updater` (self-update), and `tauri-plugin-process` (app lifecycle). No other unit imports from this one — it is the outermost shell.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `src-tauri/src/lib.rs` | 393 | Core Tauri app: builder, sidecar lifecycle, IPC commands, event loop | 🟠 Sidecar stdout protocol and error handling need attention |
| 2 | `src-tauri/src/main.rs` | 6 | Binary entry point | 🟢 Minimal and correct |
| 3 | `src-tauri/tauri.conf.json` | 78 | App config: window, bundle, updater, CSP, plugins | 🟡 macOS signing, limited Linux targets, CSP reviewed |
| 4 | `src-tauri/capabilities/default.json` | 11 | IPC permission set for main window | 🟡 Missing `shell:default` and `process:default` |
| 5 | `src-tauri/capabilities/desktop.json` | 16 | Desktop-platform IPC permissions | 🟡 Overlaps with default.json |

---

## 3. Detailed breakdown

### `src-tauri/src/lib.rs`

**Purpose:** Single-file implementation of the Tauri application shell. Handles everything: plugin registration, managed state, IPC command handlers, sidecar spawning and stdout protocol parsing, env setup for the Python backend, run-loop event handling. Name and content match well.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `std::path::{Path, PathBuf}` | stdlib | `bundled_python_path`, `local_venv_python_path`, `setup` closure | 🟢 — cfg-gated debug_assertions |
| `std::sync::Mutex` | stdlib | all state wrappers | 🟢 |
| `std::os::windows::process::CommandExt` | stdlib (windows) | `kill_process_tree` | 🟢 — cfg-gated |
| `tauri::{AppHandle, Emitter, Manager, RunEvent, State}` | 3rd-party | throughout | 🟢 |
| `tauri_plugin_shell::process::{CommandChild, CommandEvent}` | 3rd-party | sidecar spawn + stdout handling | 🟢 |
| `tauri_plugin_shell::ShellExt` | 3rd-party | `.shell()` extension | 🟢 |

**Module-level constants & state:**

None (all state is managed via Tauri's `State<>`).

**Structs (managed state):**

#### `SidecarPort(Mutex<Option<u16>>)`
- **Purpose:** Holds the discovered sidecar HTTP port
- **Still needed:** yes
- **Flag:** 🟢

#### `ApiTokenState(Mutex<Option<String>>)`
- **Purpose:** Holds the API token emitted by the sidecar
- **Still needed:** yes
- **Flag:** 🟢

#### `SidecarChild(Mutex<Option<CommandChild>>)`
- **Purpose:** Holds the handle to the running sidecar process
- **Still needed:** yes
- **Flag:** 🟢

#### `SidecarError(Mutex<Option<String>>)`
- **Purpose:** Stores the last error from the sidecar for frontend querying
- **Still needed:** yes
- **Flag:** 🟢

**Functions (IPC commands):**

#### `get_sidecar_port(state: State<SidecarPort>) -> Result<u16, String>`
- **Purpose:** Frontend query — returns the discovered port or an error if not yet set
- **Called by:** Frontend via `invoke('get_sidecar_port')`
- **Calls:** `Mutex::lock`
- **Side effects:** none
- **Flag:** 🟢

#### `get_api_token(state: State<ApiTokenState>) -> Result<String, String>`
- **Purpose:** Frontend query — returns the API token or error
- **Called by:** Frontend via `invoke('get_api_token')`
- **Flag:** 🟢

#### `get_sidecar_error(state: State<SidecarError>) -> Result<String, String>`
- **Purpose:** Frontend query — returns last known sidecar error
- **Called by:** Frontend via `invoke('get_sidecar_error')`
- **Flag:** 🟢

#### `notify_high_score_lead(app, title, body)`
- **Purpose:** Sends a desktop notification via the notification plugin
- **Called by:** Frontend via `invoke('notify_high_score_lead')`
- **Calls:** `app.notification().builder().title().body().show()`
- **Side effects:** OS notification toast
- **Flag:** 🔴 MISNAMED — `notify_high_score_lead` is a game-arcade artifact; rename to `notify_backend` or `notify_user`

**Functions (internal):**

#### `bundled_python_path(app) -> Option<PathBuf>`
- **Purpose:** Returns path to bundled Python runtime in app resources (debug only)
- **Called by:** setup closure
- **Side effects:** filesystem probe
- **Hardcodes:** candidate filenames `["bin/python3", "bin/python", "python"]`
- **Flag:** 🟢 — intentionally debug-gated

#### `local_venv_python_path(backend_dir) -> Option<PathBuf>`
- **Purpose:** Returns path to local `.venv` Python (debug only)
- **Called by:** setup closure
- **Side effects:** filesystem probe
- **Flag:** 🟢 — intentionally debug-gated

#### `kill_process_tree(pid: u32)`
- **Purpose:** Sends TERM/kill to a process and its children
- **Called by:** `shutdown_sidecar`
- **Side effects:** OS process kill
- **Hardcodes:** `CREATE_NO_WINDOW` (Windows), `kill -TERM` (Unix)
- **Flag:** 🟡 SUSPECT — on Unix, `kill -TERM` only hits the immediate child PID; grandchildren survive if the child doesn't propagate. No `SIGKILL` fallback.

#### `shutdown_sidecar(app)`
- **Purpose:** Stops the sidecar process tree and clears all sidecar state
- **Called by:** `RunEvent::ExitRequested`, `RunEvent::Exit`
- **Calls:** `kill_process_tree`, `child.kill()`, state lock + clear
- **Side effects:** process kill, state mutation
- **Flag:** 🟢 — correctly called from both exit paths

#### `run()`
- **Purpose:** Entry point called from `main.rs`. Builds the app, registers plugins, sets up managed state, spawns the sidecar with stdout parsing, then runs the event loop.
- **Called by:** `main.rs:5`
- **Calls:** all plugins init, manage, generate_handler, setup closure, app.run
- **Side effects:** spawns child process, emits events, manages locks
- **Hardcodes:** startup timeout `Duration::from_secs(15)`, `PYTHONUNBUFFERED=1`, `LOCALAPPDATA` / `XDG_DATA_HOME` env mapping
- **Flags:**

##### Setup closure (sidecar spawn and stdout parsing):

| Detail | Flag |
|--------|------|
| Starts a 15s timeout loop parsing `PORT:` and `JHM_TOKEN=` from stdout | 🟢 — reasonable protocol |
| After both received, enters post-startup loop that ignores stdout entirely | 🟡 SUSPECT — post-startup stdout is silently dropped (only stderr forwarded) |
| On timeout, kills child and emits `sidecar-terminated` | 🟢 — correct error handling |
| On `Terminated` before startup complete, emits `sidecar-error` + `sidecar-terminated` | 🟢 |
| Clones app_handle heavily (4+ clones in closure chain) | 🟢 — standard Tauri pattern |
| `env("LOCALAPPDATA", ...)` set on all platforms, not just Windows | 🟡 SUSPECT — LOCALAPPDATA is Windows-specific; it's harmless on other platforms but confusing |
| Sets `PLAYWRIGHT_BROWSERS_PATH` twice: once from resource dir (if exists), then overwritten from app data dir | 🟡 SUSPECT — second assignment always overwrites the first; resource-path block is dead if browser cache always exists |
| Uses `unsafe` unmethodical error unwraps (`.expect("error building tauri application")`) | 🟢 — standard Tauri; this only fails on config error |
| `notify_high_score_lead` registered as IPC command | 🔴 MISNAMED (see above) |

##### Run loop:

| Detail | Flag |
|--------|------|
| `WindowEvent` logging on every window event | 🔵 HARDCODED — verbose; debug only concern |
| `ExitRequested` and `Exit` both call `shutdown_sidecar` | 🟢 — correct double coverage (ExitRequested can be cancelled; Exit is final) |

**Exports:**
| Export | Known importers |
|--------|----------------|
| `run()` | `main.rs:5` |

---

### `src-tauri/src/main.rs`

**Purpose:** Binary crate entry point. Sets `windows_subsystem = "windows"` to suppress console window on MS Windows release builds. Calls `justhireme_lib::run()`. Six lines — exactly right.

**Imports:** none

**Flag:** 🟢 CLEAN

---

### `src-tauri/tauri.conf.json`

**Purpose:** Tauri configuration — window size, build commands, CSP, bundler flags, updater endpoint.

| Key | Value | Flag |
|-----|-------|------|
| `productName` | JustHireMe | 🟢 |
| `version` | 0.1.25 | 🟢 |
| `identifier` | com.vasudev-siddh.justhireme | 🟢 |
| `build.beforeDevCommand` | `npm run dev` | 🟢 |
| `build.devUrl` | `http://localhost:1420` | 🟢 |
| `build.beforeBuildCommand` | `npm run build` | 🟢 |
| `build.frontendDist` | `../dist` | 🟢 |
| `app.windows[0]` | 1440x900, min 960x600 | 🟢 |
| `app.security.csp` | connect-src `http://127.0.0.1:* ws://127.0.0.1:*` | 🟡 SUSPECT — wildcard port on localhost; understood risk for local backend but could be narrowed to known port range |
| `bundle.active` | true | 🟢 |
| `bundle.createUpdaterArtifacts` | true | 🟢 |
| `bundle.externalBin` | `["resources/backend/jhm-sidecar"]` | 🟢 — must exist at bundle time |
| `bundle.targets` | `["appimage", "deb"]` | 🟠 MISSING — no `.rpm` target for Fedora/openSUSE; snapcraft also absent |
| `bundle.macOS.signingIdentity` | `"-"` | 🔵 HARDCODED — ad-hoc signing; not distributable without Apple Developer cert |
| `plugins.updater.pubkey` | hardcoded | 🟢 — expected, key is a public value |
| `plugins.updater.endpoints` | GitHub releases latest.json | 🟢 |
| `plugins.updater.windows.installMode` | passive | 🟢 |

---

### `src-tauri/capabilities/default.json`

**Purpose:** Default capability applied to the `main` window. Grants `core:default`, `opener:default`, `notification:default`.

**Permissions:**

| Permission | Needed? | Flag |
|------------|---------|------|
| `core:default` | yes | 🟢 |
| `opener:default` | yes | 🟢 |
| `notification:default` | yes | 🟢 |
| `shell:default` | needed for sidecar? | 🟠 MISSING — `tauri_plugin_shell` is initialized but `shell:default` not in capabilities (may be intentional if sidecar is Rust-spawned only, but frontend uses shell plugin too via `@tauri-apps/plugin-shell`) |
| `process:default` | needed for process plugin | 🟠 MISSING — `tauri_plugin_process` is initialized but `process:default` not granted |

---

### `src-tauri/capabilities/desktop.json`

**Purpose:** Desktop-specific capability (platforms: macOS, Windows, Linux). Grants `core:default`, `opener:default`, `updater:default`.

**Permissions:**

| Permission | Needed? | Flag |
|------------|---------|------|
| `core:default` | yes (but also in default.json) | 🟡 DUPLICATE — merged at runtime, no harm |
| `opener:default` | yes (but also in default.json) | 🟡 DUPLICATE — same |
| `updater:default` | yes | 🟢 |
| `notification:default` | not listed | 🟢 — inherited from default.json (windows match both capabilities, permissions union) |

**Flag overall:** 🟡 DUPLICATE — `core:default` and `opener:default` are granted in both `default.json` and `desktop.json`. Since window `main` matches both capabilities, the effective permissions are the union, so these are harmless but noisy.

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 MISNAMED | `notify_high_score_lead` | `lib.rs:47` | "high score" is game terminology, irrelevant to hiring domain |
| P1 | 🟡 SUSPECT | Post-startup stdout dropped | `lib.rs:355-371` | After startup phase, sidecar stdout is silently consumed and discarded — if backend sends data there post-startup, it's lost |
| P1 | 🟡 SUSPECT | No SIGKILL fallback on Unix | `lib.rs:110-113` | `kill_process_tree` sends only TERM; stubborn children survive |
| P1 | 🟡 SUSPECT | LOCALAPPDATA set on all platforms | `lib.rs:219` | Windows-specific env var set unconditionally; harmless but confusing |
| P1 | 🟡 SUSPECT | PLAYWRIGHT_BROWSERS_PATH set twice | `lib.rs:238,254` | Second assignment (app data dir) always overwrites first (resource dir); resource-dir path may be dead code |
| P1 | 🟠 MISSING | `shell:default` permission | `capabilities/default.json:7` | Shell plugin initialized but no shell capability granted |
| P1 | 🟠 MISSING | `process:default` permission | `capabilities/default.json:7` | Process plugin initialized but no process capability granted |
| P2 | 🔵 HARDCODED | macOS signing identity | `tauri.conf.json:64` | `"-"` = ad-hoc; not distributable without a real cert |
| P2 | 🟠 MISSING | No RPM bundle target | `tauri.conf.json:62` | Fedora/openSUSE users can't install via system package |
| P2 | 🔵 HARDCODED | CSP connect-src wildcard port | `tauri.conf.json:23` | `http://127.0.0.1:*` — broad but necessary for dynamic sidecar port |
| P2 | 🟡 DUPLICATE | `core:default` + `opener:default` in both capabilities | `desktop.json:12-13` | Granted twice across default.json and desktop.json; harmless union |
| P2 | 🔵 HARDCODED | Verbose window event logging | `lib.rs:381` | Every window event logged on every interaction — debug verbosity leaks into release builds |
| P3 | 🟢 CLEAN | `main.rs` | all | Minimal entry point, correct |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- None. The Tauri unit is the outermost shell; nothing in the Rust workspace imports from it.

**Outbound (this unit depends on others):**
- **backend** (Python): spawned as sidecar, communicates via stdout protocol (`PORT:`, `JHM_TOKEN=`) and HTTP API at the discovered port
- **frontend** (Node/JS): built by `beforeBuildCommand` (Vite/TS), served in `devUrl` or `frontendDist`, invokes IPC commands

**External (third-party crates):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `tauri` 2.x | App framework, window, IPC, events | Cargo.lock | 🟢 |
| `tauri-plugin-shell` | Sidecar spawning, stdout streaming | Cargo.lock | 🟢 |
| `tauri-plugin-notification` | Desktop notifications | Cargo.lock | 🟢 |
| `tauri-plugin-updater` | Self-update via GitHub releases | Cargo.lock | 🟢 |
| `tauri-plugin-opener` | Open URLs/files in OS handler | Cargo.lock | 🟢 |
| `tauri-plugin-process` | App lifecycle (exit, restart) | Cargo.lock | 🟢 |
| `tokio` | Async runtime (indirect via tauri) | Cargo.lock | 🟢 |

---

## 6. First principles assessment

### `src-tauri/src/lib.rs`
1. **Does this file need to exist?** Yes — central Tauri shell logic.
2. **Does it do what it claims?** Mostly yes — name "lib" is generic but standard for Rust library crates.
3. **Is it the right place for this logic?** Yes — sidecar lifecycle belongs in the Tauri layer.
4. **What would break if deleted?** The entire application — no Tauri app, no sidecar spawning, no IPC.

### `src-tauri/src/main.rs`
1. **Does this file need to exist?** Yes — binary entry point.
2. **Does it do what it claims?** Yes — calls `run()`.
3. **Is it the right place for this logic?** Yes — standard Rust binary bootstrap.
4. **What would break if deleted?** No executable entry point; build fails.

### `src-tauri/tauri.conf.json`
1. **Does this file need to exist?** Yes — required by Tauri build.
2. **Does it do what it claims?** Yes — configuration is complete and valid.
3. **Is it the right place for this logic?** Yes — canonical location.
4. **What would break if deleted?** Build fails; no window config, bundle, or updater.

### `src-tauri/capabilities/default.json`
1. **Does this file need to exist?** Yes — required for IPC permission grants in Tauri v2.
2. **Does it do what it claims?** Partially — grants core/opener/notification but misses shell and process.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** IPC calls from the frontend would be denied for opener and notification.

### `src-tauri/capabilities/desktop.json`
1. **Does this file need to exist?** Yes — required for updater permission on desktop.
2. **Does it do what it claims?** Yes — grants updater on desktop platforms.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** Updater plugin calls from frontend would be denied on desktop.
