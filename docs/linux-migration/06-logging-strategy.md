# Logging Strategy

## Current Logging Implementation

### 6.1 Rust/Tauri (`src-tauri/src/lib.rs`)

#### Current Approach
- Uses `eprintln!` for sidecar events
- Sidecar stdout/stderr forwarded via `CommandEvent`
- Tauri events emitted: `sidecar-port`, `sidecar-token`, `sidecar-terminated`

**Current logging points (from `lib.rs`):**
```rust
eprintln!("[tauri] Sidecar PID: {sidecar_pid}");
eprintln!("[tauri] Sidecar port: {port}");
eprintln!("[sidecar] {line}");  // Forwarded from Python stderr
eprintln!("[tauri] Sidecar terminated: {:?}", s.code);
eprintln!("[tauri] Window event on {label}: {event:?}");
eprintln!("[tauri] Exit requested: {code:?}");
eprintln!("[tauri] App exit");
```

#### Enhancement Recommendations

**1. Add Structured Logging with `log` Crate**

Add to `src-tauri/Cargo.toml`:
```toml
[dependencies]
log = "0.4"
simplelog = "0.12"  # Or fern, env_logger, etc.
```

**Implementation:**
```rust
use log::{error, warn, info, debug, trace};

fn setup_logging() {
    use simplelog::*;
    use std::fs::File;
    
    let log_dir = dirs::data_dir()  // Cross-platform data directory
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("JustHireMe")
        .join("logs");
    
    std::fs::create_dir_all(&log_dir).ok();
    
    let log_file = File::create(log_dir.join("tauri.log")).unwrap();
    
    WriteLogger::init(
        LevelFilter::Debug,
        Config::default(),
        log_file
    ).unwrap();
    
    info!("JustHireMe Tauri starting up...");
    info!("Platform: {} {}", std::env::consts::OS, std::env::consts::ARCH);
}
```

**2. Log to File in Addition to stderr**

```rust
fn log_to_file_and_stderr(message: &str) {
    eprintln!("{}", message);  // Still show in console
    
    let log_dir = dirs::data_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("JustHireMe")
        .join("logs");
    
    std::fs::create_dir_all(&log_dir).ok();
    
    let log_file = log_dir.join("tauri.log");
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_file)
        .unwrap();
    
    writeln!(file, "{}", message).ok();
}
```

**3. Include Timestamps in All Log Messages**

```rust
fn log_with_timestamp(prefix: &str, message: &str) {
    let now = chrono::Local::now();  // Add chrono to Cargo.toml
    let timestamp = now.format("%Y-%m-%d %H:%M:%S%.3f");
    eprintln!("[{timestamp}] [{prefix}] {message}");
}
```

### 6.2 Python Backend (`backend/main.py`)

#### Current Approach
- Uses custom `logger.py` with `_log = get_logger(__name__)`
- Log level controlled via environment variable (likely)

**Finding:** Logger configuration is in `backend/logger.py` (not reviewed in detail).

#### Enhancement Recommendations

**1. Log to Both File and stderr**

```python
# In backend/main.py or logger.py
import logging
from pathlib import Path
import sys

def setup_logging():
    """Configure logging to file and stderr."""
    # Ensure log directory exists
    log_dir = Path.home() / ".local" / "share" / "JustHireMe" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (DEBUG and above)
    file_handler = logging.FileHandler(log_dir / "backend.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Call in main
logger = setup_logging()
logger.info("Logging configured. Log file: ~/.local/share/JustHireMe/logs/backend.log")
```

**2. Include Request IDs for Tracing**

```python
import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    with logging.contextualize(request_id=request_id):
        logging.info(f"Request started: {request.method} {request.url}")
        response = await call_next(request)
        logging.info(f"Request completed: {response.status_code}")
        return response
```

**3. Log ML Model Loading Times**

```python
import time
from sentence_transformers import SentenceTransformer

_log.info("Loading sentence transformer model...")
start = time.time()
model = SentenceTransformer('all-MiniLM-L6-v2')
elapsed = time.time() - start
_log.info(f"✅ Model loaded in {elapsed:.2f}s")
```

**4. Structured JSON Logging for Machine Parsing (Optional)**

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Use in setup_logging()
json_formatter = JSONFormatter()
file_handler.setFormatter(json_formatter)
```

### 6.3 Recommended Logging Architecture

```
JustHireMe/
├── ~/.local/share/JustHireMe/logs/  # Or XDG_DATA_HOME
│   ├── tauri.log                   # Rust/Tauri logs
│   ├── backend.log                  # Python FastAPI logs
│   └── sidecar.log                 # Sidecar stdout/stderr (if separated)
└── Console output (stderr/stdout)   # Real-time logs
```

**Get log directory cross-platform:**
```python
# Python
from pathlib import Path
import os

def get_log_dir():
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "JustHireMe" / "logs"
    return Path.home() / ".local" / "share" / "JustHireMe" / "logs"
```

```rust
// Rust
use dirs::data_dir;

fn get_log_dir() -> PathBuf {
    data_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("JustHireMe")
        .join("logs")
}
```

### 6.4 Log Levels for Debugging

| Level | Tauri/Rust | Python/Backend | Purpose |
|-------|-----------|----------------|---------|
| ERROR | `error!()` | `_log.error()` | Failures that need attention |
| WARN | `warn!()` | `_log.warning()` | Recoverable issues |
| INFO | `info!()` | `_log.info()` | Startup, shutdown, key events |
| DEBUG | `debug!()` | `_log.debug()` | Detailed flow (dev mode) |
| TRACE | `trace!()` | `_log.trace()` | Very verbose (troubleshooting) |

**Control log levels via environment variables:**

```bash
# Rust
RUST_LOG=debug npm run tauri dev

# Python
LOG_LEVEL=DEBUG uv run python main.py
```

### 6.5 Key Events to Log

#### Tauri Side (Rust)

```rust
info!("[tauri] Starting JustHireMe v{}", env!("CARGO_PKG_VERSION"));
info!("[tauri] Platform: {} {}", std::env::consts::OS, std::env::consts::ARCH);
info!("[tauri] Sidecar PID: {}", pid);
info!("[tauri] Sidecar port discovered: {}", port);
info!("[tauri] Sidecar terminated with code: {:?}", s.code);
debug!("[tauri] WebSocket connection from frontend");
warn!("[tauri] Sidecar spawn attempt {} failed", attempt);
error!("[tauri] Failed to spawn sidecar: {}", error);
```

#### Backend Side (Python)

```python
_log.info(f"Starting JustHireMe backend v{__version__}")
_log.info(f"Platform: {sys.platform}")
_log.info(f"Python: {sys.version}")
_log.info(f"Loaded profile with {len(skills)} skills")
_log.info(f"SentenceTransformer model loaded: {model_name} in {elapsed:.2f}s")
_log.info(f"FastAPI listening on port {port}")
_log.info(f"WebSocket client connected")
_log.debug(f"Received API request: {request.method} {request.path}")
_log.error(f"Database connection failed: {error}")
```

### 6.6 Log Rotation

**For production, implement log rotation to prevent huge files:**

```python
# Python with RotatingFileHandler
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler(
    log_dir / "backend.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

```rust
// Rust with tracing-appender
use tracing_appender::rolling;

let file_appender = rolling::daily("logs", "tauri.log");
```

### 6.7 Viewing Logs

**Watch logs in real-time:**
```bash
# Tauri logs
tail -f ~/.local/share/JustHireMe/logs/tauri.log

# Backend logs
tail -f ~/.local/share/JustHireMe/logs/backend.log

# Both
tail -f ~/.local/share/JustHireMe/logs/*.log
```

**Search for errors:**
```bash
grep -i "error\|fail\|exception" ~/.local/share/JustHireMe/logs/*.log
```

## Next Steps

1. Implement structured logging in both Rust and Python
2. Add log file output in addition to console
3. Include timestamps in all log messages
4. Test logging by running the app and checking log files
5. Continue to [Migration Steps](07-migration-steps.md) for installation
