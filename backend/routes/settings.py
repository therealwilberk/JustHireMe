import asyncio

from fastapi import APIRouter
from config import settings as cfg_settings
from core.config_constants import _sched
from schemas.requests import SettingsBody
from services.ghost import _ghost_tick
from services.provider_probe import _probe_provider_key, _sensitive, _log_sensitive_deprecation

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings")
async def get_cfg():
    from db.client import get_settings
    s = get_settings()
    _m = "••••••••••••••••••••"
    for k in _sensitive(s):
        if s.get(k):
            s[k] = _m
    return s


@router.get("/settings/validate")
async def validate_settings():
    from db.client import get_settings
    from llm import _KEY_NAMES, _OPENAI_COMPAT_BASE_URLS

    _ENV_NAMES = cfg_settings.llm.env_key_names.model_dump()

    cfg = get_settings()
    probed = {"anthropic", "gemini", "openai", "groq", *_OPENAI_COMPAT_BASE_URLS}
    providers = ["anthropic", "gemini", "openai", "groq", *[p for p in _KEY_NAMES if p not in {"anthropic", "gemini", "openai", "groq"}]]

    async def one(provider: str):
        from config.secrets import resolve_secret
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


@router.post("/settings")
async def save_cfg(body: SettingsBody):
    from db.client import get_settings, save_settings
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
