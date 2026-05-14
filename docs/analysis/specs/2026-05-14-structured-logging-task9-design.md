# Design — Structured Logging Completion (Task 9)

## Status

Approved. Awaiting implementation.

## Problem

Task 9 has core infrastructure in place (`get_logger()` in `logger.py`, all agents use it, zero `print()` in production code) but is missing:

1. **Correlation ID propagation** — no way to trace an execution flow across log lines
2. **Contextual fields** — no `workflow_type`, `lead_id`, `job_id`, etc. in log records
3. **File handler** — logs go to stderr only; no persistent file output

## Design

### 1. `backend/log_context.py` — Context Management (new)

A `contextvars`-based module for async-safe per-task context. No external dependencies (stdlib only).

```python
@dataclass
class CorrelationContext:
    correlation_id: str        # UUID4 — always set in operational paths
    workflow_type: str | None  # "http_request", "ghost_scan", "pipeline_run", etc.
    lead_id: str | None
    job_id: str | None
    node: str | None           # graph node name
    subsystem: str | None      # "ingestor", "evaluator", "api", etc.
    degraded: bool = False
    retrying: bool = False
```

#### Functions

| Function | Purpose |
|----------|---------|
| `new_context(**overrides)` | Generate UUID4, return `CorrelationContext` |
| `get_context()` | Return current context or `None` |
| `set_context(ctx)` | Set for current task, return `Token` |
| `reset_context(token)` | Restore prior state |
| `enrich(**fields)` | Replace context via `dataclasses.replace()`, return `Token` |

**Lifecycle discipline:** Every entrypoint (middleware, background job) follows:
```python
ctx = new_context(workflow_type="...")
token = set_context(ctx)
try:
    ...
finally:
    reset_context(token)
```

**Immutability:** `enrich()` uses `dataclasses.replace()` to produce a new instance. Never mutates in place. Returns a `Token` so callers can chain cleanup if needed.

### 2. Enhanced `backend/logger.py`

Two new classes plus file handler support:

**`CorrelationFilter(logging.Filter)`** — Injects context into every `LogRecord`:
- `correlation_id`: from context, or `"-"` when no context exists
- `degraded` / `retrying`: appended as flags when `True`

**`ContextFormatter(logging.Formatter)`** — Appends extra fields dynamically:
```
16:30:45 [WARNING] [abc-...] agents.ingestor: upsert update failed | lead=s1 flow=ingest
```

When no context exists:
```
16:30:45 [WARNING] [-] agents.ingestor: upsert update failed
```

**File handler** — New config fields drive optional `RotatingFileHandler`:
```python
settings.logging.log_file      # "" = disabled
settings.logging.log_file_max_bytes  # 10MB default
settings.logging.log_file_backup_count  # 3 default
```

Added in `get_logger()` alongside the stderr handler. Same format, same level.

### 3. `backend/config/logging.py` — Config additions

```python
log_file: str = ""
log_file_max_bytes: int = 10 * 1024 * 1024
log_file_backup_count: int = 3
```

### 4. `backend/main.py` — Integration points

**HTTP middleware** (before `require_http_token`):
- Sets `workflow_type="http_request"`, `subsystem="api"`
- Injects `X-Correlation-ID` response header
- `try/finally` on every request

**Background job entrypoints** — Same pattern at:
- `_ghost_tick_impl()` — `workflow_type="ghost_scan"`
- `run_pipeline()` — `workflow_type="pipeline_run"`
- `_run_x_signal_scan()` — `workflow_type="x_signal_scan"`
- `_run_free_source_scan()` — `workflow_type="free_source_scan"`

### 5. Testing

- Context isolation between concurrent asyncio tasks
- `enrich()` produces immutable copies
- Formatter output with/without context
- Middleware sets `X-Correlation-ID`
- File handler creates and rotates
- Existing 23 observability tests untouched (they bypass `get_logger()`)

## Files changed/created

| File | Action |
|------|--------|
| `backend/log_context.py` | **Create** — context management |
| `backend/logger.py` | **Modify** — Filter, Formatter, file handler |
| `backend/config/logging.py` | **Modify** — file handler config fields |
| `backend/main.py` | **Modify** — middleware + entrypoint wrappers |
| `backend/tests/test_log_context.py` | **Create** — context, formatter, middleware tests |
| `backend/tests/test_observability.py` | **NO CHANGE** |

## Non-goals

- JSON log format (deferred — not needed until log aggregation tooling)
- User-identity tracing (explicitly out of scope per design decision)
- Full structured exception schemas (current `exc_info=True` pattern is sufficient)
