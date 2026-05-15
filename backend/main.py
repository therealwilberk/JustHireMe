"""FastAPI application entrypoint for JustHireMe.

The first ``if __name__ == "__main__"`` block emits the API token
and bound port to stdout before slow imports load, so Tauri's sidecar
can read them quickly. The second ``if __name__ == "__main__"`` block
starts uvicorn after all imports are ready.
"""

import secrets
import socket
import sys

from core.config_constants import _API_TOKEN
from config import validate_all
from config.secrets import resolve_secret


def _bind_port() -> int:
    """Bind an ephemeral port and return the socket. The socket stays open to
    prevent TOCTOU races where another process grabs the port between
    discovery and use.

    Returns:
        A socket bound to 127.0.0.1 on an OS-assigned ephemeral port.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    return s


if __name__ == "__main__":
    _sock = _bind_port()
    _port = _sock.getsockname()[1]
    sys.stdout.write(f"JHM_TOKEN={_API_TOKEN}\n")
    sys.stdout.write(f"PORT:{_port}\n")
    sys.stdout.flush()


# ── Full application imports below this line ──────────────────────
# These are slow (db.client ~7s, llm, agents). The sidecar output
# above is written immediately so Tauri sees JHM_TOKEN/PORT within
# ~2s even when total import time is 15s+.

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from logger import get_logger
from config import settings
from log_context import new_context, set_context, reset_context
from core.config_constants import _log, _sched, _LOCAL_ORIGIN_RE, _bearer
from routes import (
    misc, settings as settings_router, leads, profile, scan,
    ingest, actions, ws,
)
from services.ghost import _ghost_tick


def _validate_config_on_startup():
    """Run configuration validation and exit the process on failure.

    Calls ``validate_all()`` and logs each error at CRITICAL level
    before calling ``sys.exit(1)``. Exits immediately on exceptions
    during config loading as well.
    """
    try:
        errs = validate_all()
        if errs:
            for e in errs:
                _log.critical("Config validation failed: %s", e)
            sys.exit(1)
        _log.info("Config validation passed — all domains OK")
    except Exception as exc:
        _log.critical("Config layer failed to load: %s", exc)
        sys.exit(1)


def _log_startup_secret_diagnostics() -> None:
    """Log which secrets are configured at DEBUG level.

    Iterates over known secret keys, resolves each via
    :func:`resolve_secret`, and logs a debug line for every
    secret that is present.
    """
    secrets_to_check = [
        (settings.scraping.apify_key_names.token, settings.scraping.apify_settings_key_names.token),
        (settings.scraping.apify_key_names.actor, settings.scraping.apify_settings_key_names.actor),
        (settings.contact.api_key_names.hunter, settings.contact.settings_key_names.hunter),
        (settings.contact.api_key_names.proxycurl, settings.contact.settings_key_names.proxycurl),
        (settings.app.bearer_tokens.x_bearer_token, settings.app.settings_key_names.x_bearer_token),
    ]
    for env_name, settings_key in secrets_to_check:
        val = resolve_secret(env_name, settings_key, warn_once=False)
        if val:
            _log.debug("Secret %s configured via env var.", env_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown.

    On startup: validates config, logs secret diagnostics, starts the
    ghost-mode background scheduler. On shutdown: stops the scheduler.
    """
    _validate_config_on_startup()
    _log_startup_secret_diagnostics()
    if _sched.get_job("ghost"):
        _sched.remove_job("ghost")
    _sched.add_job(_ghost_tick, "interval", hours=settings.app.ghost_mode.interval_hours, id="ghost")
    _sched.start()
    _log.info("FastAPI live.")
    yield
    _sched.shutdown(wait=False)
    _log.info("FastAPI shutdown.")


app = FastAPI(
    title="JustHireMe",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=_LOCAL_ORIGIN_RE,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_context_middleware(request: Request, call_next):
    """Attach a correlation ID to every HTTP request.

    Reads ``X-Correlation-ID`` from the request headers when present,
    or generates a new one. Sets the same ID on the response headers.
    """
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
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


@app.middleware("http")
async def require_http_token(request: Request, call_next):
    """Authenticate requests via bearer token.

    Skips authentication for OPTIONS requests and the ``/health``
    endpoint. Returns 401 if the bearer token is missing or invalid.
    """
    if request.method == "OPTIONS" or request.url.path == "/health":
        return await call_next(request)
    creds = await _bearer(request)
    if creds is None or creds.credentials != _API_TOKEN:
        return JSONResponse(
            {"detail": "invalid token"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return await call_next(request)


app.include_router(misc.router)
app.include_router(settings_router.router)
app.include_router(leads.router)
app.include_router(profile.router)
app.include_router(scan.router)
app.include_router(ingest.router)
app.include_router(actions.router)
app.include_router(ws.router)


# Backward-compatible re-exports for tests (remove after test imports updated)
from core.ws_manager import _agent_event_action
from services.job_targets import _job_targets, _profile_for_discovery
from services.scanner import _should_preserve_job_status, _job_eval_document
from services.generator import _fire_blocker, _generate_one
from services.provider_probe import _sensitive
from schemas.requests import FeedbackBody, SettingsBody, ExperienceBody, ProjectBody, ProfileImportBody

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=_port, log_level="warning")
