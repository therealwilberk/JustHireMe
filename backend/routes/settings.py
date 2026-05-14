"""Settings CRUD, API key validation, and job-targets management."""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from config import settings as cfg_settings
from core.config_constants import _sched
from schemas.requests import SettingsBody, JobTargetsUpdateBody
from schemas.responses import OkResponse, JobTargetsResponse
from services.job_targets import get_job_targets, get_blocked_markers, save_job_targets, validate_job_targets, validate_blocked_markers
from services.ghost import _ghost_tick
from config.secrets import resolve_secret
from services.provider_probe import _sensitive, _probe_provider_key, _log_sensitive_deprecation

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings", response_model=dict[str, Any])
async def get_cfg():
    """GET /api/v1/settings — Retrieve all settings with sensitive values masked.

    Returns:
        Dict of all settings with API keys masked.
    """
    from db.client import get_settings  # lazy: lancedb import takes ~7s
    s = get_settings()
    _m = "••••••••••••••••••••"
    for k in _sensitive(s):
        if s.get(k):
            s[k] = _m
    return s


@router.get("/settings/validate", response_model=dict[str, Any])
async def validate_settings():
    """GET /api/v1/settings/validate — Probe all configured API providers for validity.

    Checks each provider's key by making a lightweight API call.

    Returns:
        Dict mapping provider names to probe results (status, latency).
    """
    from db.client import get_settings  # lazy: lancedb import takes ~7s
    from llm import _KEY_NAMES, _OPENAI_COMPAT_BASE_URLS  # lazy: anthropic/instructor/openai import takes ~7s total

    _ENV_NAMES = cfg_settings.llm.env_key_names.model_dump()

    cfg = get_settings()
    probed = {"anthropic", "gemini", "openai", "groq", *_OPENAI_COMPAT_BASE_URLS}
    providers = ["anthropic", "gemini", "openai", "groq", *[p for p in _KEY_NAMES if p not in {"anthropic", "gemini", "openai", "groq"}]]

    async def one(provider: str):
        """Probe a single provider's API key and return status."""
        gemini_fallback = cfg_settings.llm.provider_specific.gemini_env_key_fallback
        env_name = _ENV_NAMES.get(provider, "")
        settings_key = _KEY_NAMES.get(provider, "")
        key = resolve_secret(env_name, settings_key) or ""
        if not key and provider == "gemini":
            key = resolve_secret(gemini_fallback, None) or ""
        key = str(key).strip()
        if not key:
            return provider, {"status": "not_configured", "latency_ms": 0}
        if provider not in probed:
            return provider, {"status": "unchecked", "latency_ms": 0}
        return provider, await _probe_provider_key(provider, key)

    pairs = await asyncio.gather(*(one(provider) for provider in providers))
    return {provider: result for provider, result in pairs}


@router.post("/settings", response_model=OkResponse)
async def save_cfg(body: SettingsBody):
    """POST /api/v1/settings — Save settings and auto-start ghost mode if enabled.

    Preserves masked sensitive values from the existing config.

    Args:
        body: Settings body with key-value pairs.

    Returns:
        OkResponse with ok: true.
    """
    from db.client import get_settings, save_settings  # lazy: lancedb import takes ~7s
    payload = {k: "" if v is None else str(v) for k, v in body.model_dump().items()}
    old = get_settings()
    _m = "••••••••••••••••••••"
    for k in _sensitive({**old, **payload}):
        if payload.get(k) == _m:
            payload[k] = old.get(k, "")
    save_settings(payload)
    _log_sensitive_deprecation(payload)
    ghost = payload.get("ghost_mode") == "true"
    if ghost and not _sched.get_job("ghost"):
        _sched.add_job(_ghost_tick, "interval", hours=6, id="ghost")
    return {"ok": True}


@router.get("/settings/job-targets", response_model=JobTargetsResponse)
async def get_job_targets_endpoint():
    """GET /api/v1/settings/job-targets — Retrieve configured job targets and blocked markers.

    Returns:
        JobTargetsResponse with targets and blocked lists.
    """
    return JobTargetsResponse(
        targets=get_job_targets(),
        blocked=get_blocked_markers(),
    )


@router.put("/settings/job-targets", response_model=JobTargetsResponse)
async def update_job_targets(body: JobTargetsUpdateBody):
    """PUT /api/v1/settings/job-targets — Replace job targets and/or blocked markers.

    Validates input before saving; partial updates allowed.

    Args:
        body: Update body with optional targets and blocked lists.

    Returns:
        JobTargetsResponse with updated targets and blocked lists.

    Raises:
        HTTPException 422: Validation failed.
    """
    targets = body.targets
    blocked = body.blocked

    if targets is not None:
        errs = validate_job_targets(targets)
        if errs:
            raise HTTPException(status_code=422, detail="; ".join(errs))
    if blocked is not None:
        errs = validate_blocked_markers(blocked)
        if errs:
            raise HTTPException(status_code=422, detail="; ".join(errs))

    current_targets = get_job_targets()
    current_blocked = get_blocked_markers()

    save_job_targets(
        targets if targets is not None else current_targets,
        blocked if blocked is not None else current_blocked,
    )
    return JobTargetsResponse(
        targets=targets if targets is not None else current_targets,
        blocked=blocked if blocked is not None else current_blocked,
    )


@router.delete("/settings/job-targets", response_model=JobTargetsResponse)
async def clear_job_targets():
    """DELETE /api/v1/settings/job-targets — Clear all job targets and blocked markers.

    Returns:
        JobTargetsResponse with empty targets and blocked lists.
    """
    save_job_targets([], [])
    return JobTargetsResponse(targets=[], blocked=[])
