# Error Handling Strategy

## Current Error Handling Gaps

### 5.1 Tauri Sidecar Management (`src-tauri/src/lib.rs`)

#### Issue 1: Sidecar Spawn Failures Not Always Logged with Context

**Location:** `src-tauri/src/lib.rs:208`

**Current Code:**
```rust
let (mut rx, child) = sidecar_cmd.spawn().expect("Failed to spawn Python sidecar");
```

**Problem:** The `expect()` panics with minimal context. If the Python binary doesn't exist or permissions are wrong, the error message is generic.

**Recommended Improvement (for future implementation):**
```rust
let sidecar_result = sidecar_cmd.spawn();

match &sidecar_result {
    Ok(_) => eprintln!("[tauri] Sidecar spawned successfully"),
    Err(e) => {
        eprintln!("[tauri] ERROR: Failed to spawn sidecar: {}", e);
        eprintln!("[tauri] Check that backend binary exists and is executable");
        eprintln!("[tauri] Python path: {:?}", sidecar_cmd);
    }
}

let (mut rx, child) = sidecar_result.expect("Failed to spawn Python sidecar");
```

#### Issue 2: Port Discovery Has No Timeout

**Location:** `src-tauri/src/lib.rs:222-230`

**Current Code:**
```rust
if let Some(port_str) = line.strip_prefix("PORT:") {
    if let Ok(port) = port_str.parse::<u16>() {
        if let Ok(mut g) = app_handle.state::<SidecarPort>().0.lock() {
            *g = Some(port);
        }
        let _ = app_handle.emit("sidecar-port", port);
        eprintln!("[tauri] Sidecar port: {port}");
    }
}
```

**Problem:** If the Python backend never outputs `PORT:`, the app hangs indefinitely waiting.

**Recommended Improvement:**
```rust
// Add timeout for port discovery
let port_timeout = std::time::Duration::from_secs(30);
let start_time = std::time::Instant::now();
let mut port_discovered = false;

while let Some(event) = rx.recv().await {
    match event {
        CommandEvent::Stdout(b) => {
            let line = String::from_utf8_lossy(&b).trim().to_string();
            if let Some(port_str) = line.strip_prefix("PORT:") {
                // ... parse port ...
                port_discovered = true;
                break;
            }
        }
        // ... other events ...
    }
    
    if start_time.elapsed() > port_timeout && !port_discovered {
        eprintln!("[tauri] ERROR: Timeout waiting for sidecar port after 30s");
        break;
    }
}
```

#### Issue 3: API Token Discovery Has No Timeout

**Location:** `src-tauri/src/lib.rs:231-236`

**Similar to port discovery - no timeout for `JHM_TOKEN=` line.**

#### Issue 4: No Retry Logic for Sidecar Spawn Failures

**Problem:** If sidecar fails to start (e.g., Python not found), the app crashes immediately.

**Recommended Improvement:**
```rust
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

### 5.2 Python Backend (`backend/main.py`)

#### Issue 1: No Global Exception Handler for Unhandled Errors

**Location:** `backend/main.py:1-100`

**Problem:** Unhandled exceptions in FastAPI/uvicorn will crash the backend without detailed logging.

**Recommended Improvement:**
```python
import traceback
import sys

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    _log.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Write to file as well
    with open("/tmp/justhireme_crash.log", "a") as f:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

sys.excepthook = handle_exception
```

#### Issue 2: FastAPI Startup Doesn't Validate Critical Dependencies

**Location:** `backend/main.py` (startup event)

**Problem:** If critical imports fail (e.g., `sentence_transformers` not installed), the app starts but fails later.

**Recommended Improvement:**
```python
@app.on_event("startup")
async def startup_event():
    """Validate dependencies on startup."""
    _log.info("Starting JustHireMe backend...")
    
    # Validate critical dependencies
    critical_deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("torch", "torch"),
        ("sentence_transformers", "sentence_transformers"),
        ("kuzu", "kuzu"),
        ("lancedb", "lancedb"),
    ]
    
    for name, import_name in critical_deps:
        try:
            __import__(import_name)
            _log.info(f"✅ {name} imported successfully")
        except ImportError as e:
            _log.error(f"❌ Critical dependency missing: {name}")
            _log.error(f"Error: {e}")
            raise RuntimeError(f"Cannot start: missing dependency: {name}")
    
    # Validate database connections
    try:
        from db.client import init_db
        init_db()
        _log.info("✅ Database initialized successfully")
    except Exception as e:
        _log.error(f"❌ Database initialization failed: {e}")
        raise
    
    _log.info("✅ Startup validation complete")
```

#### Issue 3: Database Connection Failures Not Caught Early

**Problem:** Database errors may only appear when first query is executed.

**Solution:** Initialize database in startup event (see above).

#### Issue 4: WebSocket Errors Not Always Logged

**Location:** `backend/main.py` (WebSocket endpoints)

**Recommended Improvement:**
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _log.info(f"WebSocket client connected from {websocket.client}")
    
    try:
        while True:
            data = await websocket.receive_text()
            # ... handle message ...
    except WebSocketDisconnect:
        _log.info("WebSocket client disconnected")
    except Exception as e:
        _log.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        _log.info("WebSocket connection closed")
```

### 5.3 Error Handling Checklist

For Linux migration, ensure these are logged:

- [ ] Tauri sidecar spawn success/failure (with detailed error)
- [ ] Sidecar port discovery (with timeout)
- [ ] Sidecar API token discovery (with timeout)
- [ ] Python backend startup errors (with dependency check)
- [ ] Database connection status (with retry logic)
- [ ] ML model loading (with timing and error details)
- [ ] FastAPI startup completion (log port number)
- [ ] WebSocket connection errors (with client info)
- [ ] File system permission errors (for `resources/` dirs)
- [ ] PyTorch CUDA availability (log if using CPU fallback)

### 5.4 Error Recovery Strategies

| Error Type | Strategy | Implementation |
|-----------|----------|-----------------|
| Sidecar spawn fails | Retry 3 times with delay | `spawn_sidecar_with_retry()` |
| Port not discovered | Timeout after 30s, show error UI | Loop with `Instant::now()` check |
| Database connection fails | Retry with exponential backoff | Wrap `init_db()` in retry loop |
| ML model download fails | Fallback to smaller model | Try `all-MiniLM-L6-v2` first |
| WebSocket disconnects | Reconnect with backoff | Frontend: implement reconnect logic |
| File permission denied | Log path and required permissions | Use `os.access(path, os.W_OK)` |

### 5.5 Logging Errors to File

**Create a central log file for errors:**

```python
# In backend/main.py
import logging
from pathlib import Path

# Ensure log directory exists
log_dir = Path.home() / ".local" / "share" / "JustHireMe" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging to file
file_handler = logging.FileHandler(log_dir / "backend.log")
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)
```

**For Rust/Tauri (future implementation):**
```rust
// Use the `log` and `simplelog` crates
use log::{error, warn, info, debug, trace};

// Write to file
use simplelog::*;
use std::fs::File;

let log_file = File::create("/home/user/.local/share/JustHireMe/logs/tauri.log").unwrap();
WriteLogger::init(LevelFilter::Debug, Config::default(), log_file).unwrap();
```

### Stdout-Based Port Discovery Fragility

**Location:** `src-tauri/src/lib.rs:222-235`

**Problem:** Tauri reads Python stdout to find `PORT:` and `JHM_TOKEN=` lines. If the Python backend prints anything else to stdout (e.g., from a library, logging misconfiguration, or `print()` debugging), parsing breaks silently.

**Current Code:**
```rust
CommandEvent::Stdout(b) => {
    let line = String::from_utf8_lossy(&b).trim().to_string();
    if let Some(port_str) = line.strip_prefix("PORT:") {
        // ... parse port
    } else if let Some(token) = line.strip_prefix("JHM_TOKEN=") {
        // ... parse token
    }
    // Other lines are ignored (potential parsing issues)
}
```

**Risk:** HIGH - Sidecar never starts properly from the user's perspective, with only `eprintln!` messages to stderr for diagnostics.

**Recommended Fix:**
```rust
// Use a sidecar handshake file, environment variable, or Tauri sidecar protocol
// Alternative: Write port to a known file instead of stdout
// Example: Write to $XDG_RUNTIME_DIR/justhireme-sidecar.json
```

**Reference:** Audit finding 6.1 - Stdout-Based Port Discovery.

---

## Next Steps

1. Review [Logging Strategy](06-logging-strategy.md) for detailed logging recommendations
2. Implement critical error handling improvements in `lib.rs` and `main.py`
3. Test error scenarios (e.g., delete Python binary, remove DB permissions)
4. Continue to [Migration Steps](07-migration-steps.md) for installation
