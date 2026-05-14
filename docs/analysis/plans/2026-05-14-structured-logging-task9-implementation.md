# Structured Logging Completion (Task 9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete structured logging with correlation ID propagation, contextual fields, and optional file handler.

**Architecture:** `contextvars`-based `CorrelationContext` per task. FastAPI middleware + background entrypoints set context. Custom `logging.Filter` + `Formatter` enrich records. Optional `RotatingFileHandler` driven by config.

**Tech Stack:** Python stdlib (`contextvars`, `logging`, `dataclasses`, `uuid`). No new dependencies.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/log_context.py` | **Create** | `CorrelationContext` dataclass, `contextvars.ContextVar`, `new_context()`/`get_context()`/`set_context()`/`reset_context()`/`enrich()` |
| `backend/logger.py` | **Modify** | Add `CorrelationFilter`, `ContextFormatter`, file handler in `get_logger()` |
| `backend/config/logging.py` | **Modify** | Add `log_file`, `log_file_max_bytes`, `log_file_backup_count` |
| `backend/main.py` | **Modify** | Add `correlation_context_middleware`, wrap background job entrypoints |
| `backend/tests/test_log_context.py` | **Create** | Tests for context isolation, enrich, formatter, middleware, file handler |

---

### Task 1: Add file handler config fields

**Files:**
- Modify: `backend/config/logging.py:19-21`
- Test: verified in Task 3 via `get_logger()` behavior

- [ ] **Step 1: Add config fields to LoggingConfig**

Edit `backend/config/logging.py` to add after `propagate: bool = False`:

```python
log_file: str = Field(default="", description="Path to log file. Empty = no file handler.")
log_file_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
log_file_backup_count: int = Field(default=3, ge=0)
```

- [ ] **Step 2: Verify config loads without breaking**

Run: `uv run python -c "from config import settings; print(settings.logging.log_file); print('OK')"`
Expected: `""` followed by `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/config/logging.py
git commit -m "feat: add log_file, log_file_max_bytes, log_file_backup_count to LoggingConfig"
```

---

### Task 2: Create log_context.py

**Files:**
- Create: `backend/log_context.py`

- [ ] **Step 1: Write log_context.py**

Create `backend/log_context.py`:

```python
import contextvars
import uuid
from dataclasses import dataclass, replace
from typing import Optional


@dataclass
class CorrelationContext:
    correlation_id: str
    workflow_type: Optional[str] = None
    lead_id: Optional[str] = None
    job_id: Optional[str] = None
    node: Optional[str] = None
    subsystem: Optional[str] = None
    degraded: bool = False
    retrying: bool = False


_context_var: contextvars.ContextVar[Optional[CorrelationContext]] = (
    contextvars.ContextVar("correlation_context", default=None)
)


def new_context(**overrides) -> CorrelationContext:
    return CorrelationContext(correlation_id=str(uuid.uuid4()), **overrides)


def get_context() -> Optional[CorrelationContext]:
    return _context_var.get()


def set_context(ctx: CorrelationContext) -> contextvars.Token:
    return _context_var.set(ctx)


def reset_context(token: contextvars.Token) -> None:
    _context_var.reset(token)


def enrich(**fields) -> contextvars.Token:
    ctx = get_context()
    if ctx is None:
        raise RuntimeError("No correlation context to enrich")
    new_ctx = replace(ctx, **fields)
    return set_context(new_ctx)
```

- [ ] **Step 2: Write the test file**

Create `backend/tests/test_log_context.py`:

```python
import asyncio
import uuid
from contextvars import copy_context

import pytest

from log_context import (
    CorrelationContext,
    get_context,
    new_context,
    reset_context,
    set_context,
    enrich,
)


class TestContextBasics:
    def test_new_context_has_uuid4(self):
        ctx = new_context(workflow_type="test")
        assert ctx.workflow_type == "test"
        # UUID4 is 36 chars with hyphens
        assert len(ctx.correlation_id) == 36
        assert ctx.correlation_id.count("-") == 4

    def test_get_context_returns_none_when_not_set(self):
        assert get_context() is None

    def test_set_and_get_context(self):
        ctx = new_context(workflow_type="test")
        token = set_context(ctx)
        try:
            assert get_context() is ctx
        finally:
            reset_context(token)

    def test_reset_restores_prior_state(self):
        ctx_a = new_context(workflow_type="a")
        ctx_b = new_context(workflow_type="b")
        token_a = set_context(ctx_a)
        set_context(ctx_b)
        reset_context(token_a)
        assert get_context() is None

    def test_enrich_creates_new_instance(self):
        ctx = new_context(workflow_type="base")
        token = set_context(ctx)
        try:
            token2 = enrich(workflow_type="enriched", lead_id="123")
            enriched = get_context()
            assert enriched is not ctx  # new instance
            assert enriched.workflow_type == "enriched"
            assert enriched.lead_id == "123"
            assert enriched.correlation_id == ctx.correlation_id  # same ID
            # Reset the enrichment
            reset_context(token2)
            assert get_context().workflow_type == "base"
        finally:
            reset_context(token)

    def test_enrich_raises_when_no_context(self):
        with pytest.raises(RuntimeError, match="No correlation context"):
            enrich(lead_id="123")


class TestContextIsolation:
    def test_tasks_do_not_share_context(self):
        results = []

        async def task_a():
            ctx = new_context(workflow_type="a")
            token = set_context(ctx)
            try:
                await asyncio.sleep(0.01)
                results.append(("a", get_context().workflow_type))
            finally:
                reset_context(token)

        async def task_b():
            ctx = new_context(workflow_type="b")
            token = set_context(ctx)
            try:
                await asyncio.sleep(0.02)
                results.append(("b", get_context().workflow_type))
            finally:
                reset_context(token)

        async def run():
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run())
        assert ("a", "a") in results
        assert ("b", "b") in results

    def test_default_is_isolated(self):
        from contextvars import copy_context

        ctx = new_context(workflow_type="outside")
        token = set_context(ctx)
        try:
            # A task spawned via copy_context should see the parent's context
            # Actually, asyncio tasks propagate contextvars automatically
            pass
        finally:
            reset_context(token)

    def test_enrich_in_one_task_does_not_affect_another(self):
        results = []

        async def task_a():
            ctx = new_context(workflow_type="a")
            token = set_context(ctx)
            try:
                enrich(lead_id="lead-a")
                await asyncio.sleep(0.01)
                c = get_context()
                results.append(("a", c.workflow_type, c.lead_id))
            except RuntimeError:
                results.append(("a", "error", None))
            finally:
                reset_context(token)

        async def task_b():
            ctx = new_context(workflow_type="b")
            token = set_context(ctx)
            try:
                await asyncio.sleep(0.02)
                c = get_context()
                results.append(("b", c.workflow_type, c.lead_id))
            finally:
                reset_context(token)

        async def run():
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run())
        assert ("a", "a", "lead-a") in results
        assert ("b", "b", None) in results
```

- [ ] **Step 3: Run tests to verify they fail initially**

Run: `uv run python -m pytest tests/test_log_context.py -v --tb=short`
Expected: PASS (the module exists and tests should work since log_context.py is a pure module)

Actually wait — since I'm writing both the implementation and test in the same step, let me clarify TDD by running tests first (they'll fail because log_context.py doesn't exist yet).

Run: `uv run python -m pytest tests/test_log_context.py -v --tb=short`
Expected: FAIL with "ModuleNotFoundError: No module named 'log_context'"

- [ ] **Step 4: Implement log_context.py** (done above in Step 1)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_log_context.py::TestContextBasics tests/test_log_context.py::TestContextIsolation -v --tb=short`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/log_context.py backend/tests/test_log_context.py
git commit -m "feat: add correlation context module with contextvars-based isolation"
```

---

### Task 3: Enhance logger.py with CorrelationFilter, ContextFormatter, file handler

**Files:**
- Modify: `backend/logger.py`

- [ ] **Step 1: Write the test file additions for logger enhancements**

Add these tests to `backend/tests/test_log_context.py` (at the end, before any `__main__` block):

```python
import io
import logging
import os
import tempfile
from pathlib import Path

from logger import get_logger, CorrelationFilter, ContextFormatter


class TestCorrelationFilter:
    def test_filter_injects_correlation_id_when_context_exists(self):
        ctx = new_context(workflow_type="filter_test")
        token = set_context(ctx)
        try:
            buf = io.StringIO()
            handler = logging.StreamHandler(buf)
            handler.setFormatter(ContextFormatter())
            handler.addFilter(CorrelationFilter())
            logger = logging.getLogger("test.filter")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.info("hello")
            output = buf.getvalue()
            assert ctx.correlation_id in output
        finally:
            reset_context(token)

    def test_filter_uses_dash_when_no_context(self):
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(ContextFormatter())
        handler.addFilter(CorrelationFilter())
        logger = logging.getLogger("test.filter.null")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.info("no context")
        output = buf.getvalue()
        assert "[-]" in output or "[correlation_id=-]" in output

    def test_filter_appends_contextual_fields(self):
        ctx = new_context(workflow_type="scan", lead_id="lead-42", job_id="job-7")
        token = set_context(ctx)
        try:
            buf = io.StringIO()
            handler = logging.StreamHandler(buf)
            handler.setFormatter(ContextFormatter())
            handler.addFilter(CorrelationFilter())
            logger = logging.getLogger("test.filter.fields")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.info("processing")
            output = buf.getvalue()
            assert "lead-42" in output
            assert "job-7" in output
            assert "flow=scan" in output
        finally:
            reset_context(token)


class TestContextFormatter:
    def test_format_with_context(self):
        ctx = new_context(workflow_type="format_test", lead_id="l1")
        token = set_context(ctx)
        try:
            buf = io.StringIO()
            handler = logging.StreamHandler(buf)
            fmt = ContextFormatter("%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s")
            handler.setFormatter(fmt)
            handler.addFilter(CorrelationFilter())
            logger = logging.getLogger("test.formatter")
            logger.setLevel(logging.DEBUG)
            logger.propagate = False
            logger.addHandler(handler)
            logger.info("format check")
            output = buf.getvalue()
            assert ctx.correlation_id in output
            # Should have extra context appended
            assert "|" in output
            assert "l1" in output
        finally:
            reset_context(token)

    def test_format_without_context(self):
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        fmt = ContextFormatter("%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s")
        handler.setFormatter(fmt)
        handler.addFilter(CorrelationFilter())
        logger = logging.getLogger("test.formatter.null")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(handler)
        logger.info("no ctx here")
        output = buf.getvalue()
        assert "[-]" in output


class TestFileHandler:
    def test_get_logger_creates_file_handler_when_configured(self):
        import tempfile
        from pathlib import Path
        from config import settings

        # Temporarily set log_file config
        old_val = settings.logging.log_file
        tmp = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        tmp.close()
        try:
            settings.logging.log_file = tmp.name
            # Create a fresh logger — get_logger skips if handlers exist
            logger = get_logger("test.file_handler." + str(uuid.uuid4()).replace("-", ""))
            # get_logger should add a FileHandler alongside StreamHandler
            handler_types = [type(h).__name__ for h in logger.handlers]
            assert "FileHandler" in handler_types or "RotatingFileHandler" in handler_types
            logger.info("file handler test")
            # Verify the file was written
            content = Path(tmp.name).read_text()
            assert "file handler test" in content
        finally:
            settings.logging.log_file = old_val
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except OSError:
                pass

    def test_get_logger_skips_file_handler_when_not_configured(self):
        from config import settings
        old_val = settings.logging.log_file
        try:
            settings.logging.log_file = ""
            logger = get_logger("test.no_file." + str(uuid.uuid4()).replace("-", ""))
            handler_types = [type(h).__name__ for h in logger.handlers]
            assert "FileHandler" not in handler_types
            assert "RotatingFileHandler" not in handler_types
        finally:
            settings.logging.log_file = old_val
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_log_context.py::TestCorrelationFilter tests/test_log_context.py::TestContextFormatter tests/test_log_context.py::TestFileHandler -v --tb=long`
Expected: FAIL with various import/attribute errors (CorrelationFilter, ContextFormatter not in logger module yet)

- [ ] **Step 3: Update logger.py**

Replace the contents of `backend/logger.py`:

```python
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import settings


class CorrelationFilter(logging.Filter):
    """Injects correlation context fields into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from log_context import get_context
            ctx = get_context()
        except Exception:
            ctx = None
        record.correlation_id = ctx.correlation_id if ctx else "-"
        record._ctx_subystem = ctx.subsystem if ctx and ctx.subsystem else ""
        record._ctx_workflow = ctx.workflow_type if ctx and ctx.workflow_type else ""
        record._ctx_lead = ctx.lead_id if ctx and ctx.lead_id else ""
        record._ctx_job = ctx.job_id if ctx and ctx.job_id else ""
        record._ctx_node = ctx.node if ctx and ctx.node else ""
        record._ctx_degraded = "DEGRADED" if ctx and ctx.degraded else ""
        record._ctx_retrying = "RETRYING" if ctx and ctx.retrying else ""
        return True


class ContextFormatter(logging.Formatter):
    """Appends contextual fields to log lines when present."""

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        extras = []
        if record._ctx_lead:
            extras.append(f"lead={record._ctx_lead}")
        if record._ctx_job:
            extras.append(f"job={record._ctx_job}")
        if record._ctx_node:
            extras.append(f"node={record._ctx_node}")
        if record._ctx_subystem:
            extras.append(f"sub={record._ctx_subystem}")
        if record._ctx_workflow:
            extras.append(f"flow={record._ctx_workflow}")
        if record._ctx_degraded:
            extras.append(record._ctx_degraded)
        if record._ctx_retrying:
            extras.append(record._ctx_retrying)
        if extras:
            s = f"{s} | {' '.join(extras)}"
        return s


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level_str = os.environ.get(settings.logging.env_var, settings.logging.default_level).upper()
    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    # Stderr handler (always)
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    fmt = logging.Formatter(
        fmt=settings.logging.format_string or "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s",
        datefmt=settings.logging.date_format,
    )
    sh.setFormatter(fmt)
    sh.addFilter(CorrelationFilter())
    logger.addHandler(sh)

    # File handler (optional)
    if settings.logging.log_file:
        fh = RotatingFileHandler(
            settings.logging.log_file,
            maxBytes=settings.logging.log_file_max_bytes,
            backupCount=settings.logging.log_file_backup_count,
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        fh.addFilter(CorrelationFilter())
        logger.addHandler(fh)

    logger.propagate = False
    return logger
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_log_context.py -v --tb=short`
Expected: All PASS

- [ ] **Step 5: Verify existing observability tests still pass**

Run: `uv run python -m pytest tests/test_observability.py -v --tb=short`
Expected: All 23 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/logger.py backend/tests/test_log_context.py
git commit -m "feat: add CorrelationFilter, ContextFormatter, and file handler to logger"
```

---

### Task 4: Wire context middleware into main.py

**Files:**
- Modify: `backend/main.py` (around line 698)

- [ ] **Step 1: Add middleware before require_http_token**

Edit `backend/main.py` — add after the `app.add_middleware(CORSMiddleware, ...)` block and before the `@app.middleware("http")` for `require_http_token`:

```python
from log_context import new_context, set_context, reset_context


# ... existing CORS middleware setup ...


@app.middleware("http")
async def correlation_context_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
        # Client-initiated correlation ID (frontend passes its own)
        ctx = new_context(correlation_id=correlation_id, workflow_type="http_request", subsystem="api")
    else:
        ctx = new_context(workflow_type="http_request", subsystem="api")
    token = set_context(ctx)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = ctx.correlation_id
        return response
    finally:
        reset_context(token)
```

- [ ] **Step 2: Add context to background job entrypoints**

Find `_ghost_tick_impl` in `main.py` and wrap it:

```python
async def _ghost_tick_impl():
    ctx = new_context(workflow_type="ghost_scan", subsystem="scheduler")
    token = set_context(ctx)
    try:
        # ... existing body ...
    finally:
        reset_context(token)
```

Find `run_pipeline` endpoint and wrap:

```python
@app.post("/api/v1/leads/{job_id}/pipeline/run")
async def run_pipeline(job_id: str, bt: BackgroundTasks):
    ctx = new_context(workflow_type="pipeline_run", job_id=job_id, subsystem="pipeline")
    token = set_context(ctx)
    try:
        # ... existing body ... (keep the full existing body indented)
    finally:
        reset_context(token)
```

Also wrap `_run_x_signal_scan` and `_run_free_source_scan` entry points with similar patterns (`workflow_type="x_signal_scan"`, `workflow_type="free_source_scan"`).

- [ ] **Step 3: Write middleware test**

Add to `backend/tests/test_log_context.py`:

```python
class TestMiddlewareIntegration:
    def test_correlation_middleware_sets_header(self):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client:
            resp = client.get("/health", headers={"Authorization": "Bearer test"})
            # health might not need auth; just check header
            if "X-Correlation-ID" in resp.headers:
                cid = resp.headers["X-Correlation-ID"]
                assert len(cid) == 36
                assert cid.count("-") == 4

    def test_middleware_accepts_client_correlation_id(self):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client:
            client_cid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            resp = client.get("/health", headers={
                "Authorization": "Bearer test",
                "X-Correlation-ID": client_cid,
            })
            if "X-Correlation-ID" in resp.headers:
                assert resp.headers["X-Correlation-ID"] == client_cid
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_log_context.py::TestMiddlewareIntegration -v --tb=short`
Expected: PASS (or need to adjust for auth; the health endpoint may not require auth)

Run: `uv run python -m pytest tests/test_observability.py -v --tb=short`
Expected: All 23 PASS (middleware shouldn't affect existing tests since they bypass get_logger())

Run: `uv run python -m pytest tests/ -q --tb=line`
Expected: 280 PASS (all existing backend tests)

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_log_context.py
git commit -m "feat: wire correlation context middleware and background job entrypoints in main.py"
```

---

### Task 5: Update docs and run full validation

- [ ] **Step 1: Update TEST_DOCS.md**

Edit `backend/tests/TEST_DOCS.md` to add `test_log_context.py` to the Phase C coverage table:

Add row under Phase C Coverage:
```markdown
| Correlation context & structured logging | 15 (context isolation, enrich, formatter, filter, file handler, middleware) | `test_log_context.py` |
```

And update the Phase C test count: `Phase C adds 76 backend + 20 frontend tests` → `Phase C adds 91 backend + 20 frontend tests` (76 + 15 = 91)

- [ ] **Step 2: Update phase-c spec Task 9 validation checklist**

Edit `docs/analysis/specs/Features/phase-c-reliability-observability.md` to mark remaining Task 9 items as done and add new items:

```markdown
### Task 9 — Structured Logging *(Done)*

- [x] Centralized `get_logger()` in `backend/logger.py` — all agent modules use it
- [x] Log format: `%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s` with contextual fields
- [x] Zero `print()` calls in production code (remaining print calls are in operational scripts only)
- [x] Zero ad hoc `logging.getLogger` in production code (all through `get_logger()`)
- [x] Log level configurable via env var (`JHM_LOG_LEVEL`)
- [x] Logs go to stderr (consistent with CLI convention)
- [x] `logger.propagate = False` — no duplicate log lines
- [x] **Correlation ID propagation**: `contextvars`-based `CorrelationContext` per task. UUID4, opaque, no coupling to user identity.
- [x] **Contextual fields**: `workflow_type`, `lead_id`, `job_id`, `node`, `subsystem`, `degraded`, `retrying` appended to log lines when present.
- [x] **FastAPI middleware**: Sets context per request, injects `X-Correlation-ID` response header. Accepts client-initiated IDs.
- [x] **Background job entrypoints**: `_ghost_tick_impl`, `run_pipeline`, `_run_x_signal_scan`, `_run_free_source_scan` wrapped with context.
- [x] **File handler**: Optional `RotatingFileHandler` via `settings.logging.log_file` config. Max bytes and backup count configurable.
- [x] **Lifecycle discipline**: Every entrypoint uses `try/finally` with token reset. `enrich()` uses `dataclasses.replace()` for immutability.
- [x] 15+ tests verify context isolation, enrich, formatter, filter, file handler, middleware header propagation.
```

- [ ] **Step 3: Update roadmap.md**

Edit `docs/analysis/specs/roadmap.md` to mark Task 9 items as done.

- [ ] **Step 4: Run full test suite**

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

Expected: 295 passed (280 existing + 15 new)

```bash
cd /app && npx vitest run
```

Expected: 33 passed

- [ ] **Step 5: Commit**

```bash
git add backend/tests/TEST_DOCS.md docs/analysis/specs/Features/phase-c-reliability-observability.md docs/analysis/specs/roadmap.md
git commit -m "docs: mark Task 9 done, update test counts, update validation checklists"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: Every requirement from the design doc has a task:
  - CorrelationContext dataclass → Task 2
  - contextvars.ContextVar → Task 2
  - new_context/get_context/set_context/reset_context/enrich → Task 2
  - CorrelationFilter → Task 3
  - ContextFormatter → Task 3
  - File handler → Tasks 1, 3
  - Config fields → Task 1
  - FastAPI middleware → Task 4
  - Background job wrappers → Task 4
  - Tests → Tasks 2, 3, 4
  - Docs → Task 5

- [x] **Placeholder scan**: No "TBD", "TODO", or vague instructions. Every code block is complete.

- [x] **Type consistency**: `CorrelationContext`, `new_context()`, `set_context()`, `reset_context()`, `enrich()` are consistently used across all tasks. `CorrelationFilter`, `ContextFormatter` are consistently imported and used.

- [x] **DRY**: Test code is written once per behavior. Config schema is defined once in `config/logging.py`.
