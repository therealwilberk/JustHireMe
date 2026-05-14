"""Health check, events, graph stats, resume template, and help chat."""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse


from config import settings
from schemas.requests import TemplateBody, HelpChatBody
from schemas.responses import HealthResponse, OkResponse, TemplateResponse
from core.config_constants import _log, _UP

router = APIRouter(tags=["misc"])


def _configured_api_providers(settings: dict) -> list:
    """Return names of API providers that have a key configured."""
    providers = []
    for key, val in settings.items():
        if key.endswith("_api_key") or key.endswith("_key") or key.endswith("_token"):
            if val:
                provider = key.replace("_api_key", "").replace("_key", "").replace("_token", "")
                providers.append(provider)
    return providers


@router.get("/health", dependencies=[], response_model=HealthResponse)
async def health():
    """Lightweight health check with real dependency probes.

    Returns alive/uptime plus per-dependency status for database,
    browser binary, and configured API keys.
    """
    from agents.browser_runtime import chromium_executable  # lazy: agents module (per-request dep)
    from db.client import get_settings, get_sql_connection  # lazy: lancedb import takes ~7s

    db_status = "ok"
    db_latency = 0.0
    try:
        t0 = time.monotonic()
        get_sql_connection().execute("SELECT 1")
        db_latency = round((time.monotonic() - t0) * 1000, 1)
    except Exception as exc:
        db_status = "error"
        _log.warning("health: db probe failed — %s", exc)

    browser_path = chromium_executable()
    browser_status = "found" if browser_path else "not_found"

    cfg = get_settings()
    configured_providers = _configured_api_providers(cfg)

    return {
        "status": "alive",
        "uptime_seconds": round(time.monotonic() - _UP, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "log_level": os.environ.get(settings.logging.env_var, settings.logging.default_level),
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
                "status": "configured" if configured_providers else "missing",
                "configured_providers": configured_providers,
            },
        },
    }


@router.get("/api/v1/events", response_model=list[dict[str, Any]])
async def get_events_endpoint(limit: int = 100, job_id: str | None = None):
    """GET /api/v1/events — Retrieve recent application events.

    Args:
        limit: Maximum number of events to return.
        job_id: Optional job ID to filter events.

    Returns:
        List of event dicts.
    """
    from db.client import get_events  # lazy: lancedb import takes ~7s
    return get_events(limit=limit, job_id=job_id)


@router.get("/api/v1/graph", response_model=dict[str, Any])
async def graph_stats():
    """GET /api/v1/graph — Retrieve aggregate graph/dashboard counts.

    Returns:
        Dict of count statistics from the database.
    """
    from db.client import graph_counts  # lazy: lancedb import takes ~7s
    return graph_counts()


@router.get("/api/v1/template", response_model=TemplateResponse)
async def get_template():
    """GET /api/v1/template — Retrieve the saved resume template.

    Returns:
        TemplateResponse with template string.
    """
    from db.client import get_setting  # lazy: lancedb import takes ~7s
    return {"template": get_setting("resume_template", "")}


@router.post("/api/v1/template", response_model=OkResponse)
async def save_template(body: TemplateBody):
    """POST /api/v1/template — Save the resume template.

    Args:
        body: Request body with template content.

    Returns:
        OkResponse with ok: true.
    """
    from db.client import save_settings  # lazy: lancedb import takes ~7s
    save_settings({"resume_template": body.template})
    return {"ok": True}


@router.post("/api/v1/help/chat", response_model=dict[str, Any])
async def help_chat(body: HelpChatBody):
    """POST /api/v1/help/chat — Ask a question to the help agent.

    Args:
        body: Request body with question and chat history.

    Returns:
        Help agent response dict.
    """
    from agents.help_agent import answer  # lazy: agents module (per-request dep)

    history = [item.model_dump() for item in body.history]
    return await asyncio.to_thread(answer, body.question, history)
