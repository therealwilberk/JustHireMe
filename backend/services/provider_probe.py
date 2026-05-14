"""LLM provider API key health checking.

Provides a lightweight probe that sends a minimal request to each
supported provider (Anthropic, OpenAI, Groq, Gemini, and OpenAI-compatible
endpoints) and reports connectivity status and latency.
"""

import time

import httpx

from config import settings
from core.config_constants import _log


async def _probe_provider_key(provider: str, key: str) -> dict:
    """Check whether an API key is valid for a given LLM provider.

    Sends the cheapest possible request (model listing or minimal message)
    and classifies the response as ``ok``, ``invalid_key``, ``unreachable``,
    or ``unchecked``.

    Args:
        provider: Provider name (``"anthropic"``, ``"openai"``,
            ``"groq"``, ``"gemini"``, or a key in
            ``_OPENAI_COMPAT_BASE_URLS``).
        key: The API key string to test.

    Returns:
        A dict with ``status`` (str) and ``latency_ms`` (int).
    """
    from llm import _OPENAI_COMPAT_BASE_URLS  # lazy: anthropic/instructor/openai import takes ~7s total
    started = time.perf_counter()
    try:
        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "anthropic":
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                )
                status = "ok" if r.status_code in {200, 400} else "invalid_key" if r.status_code == 401 else "unreachable"
            elif provider == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                status = "ok" if r.status_code == 200 else "invalid_key" if r.status_code == 401 else "unreachable"
            elif provider == "groq":
                r = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                status = "ok" if r.status_code == 200 else "invalid_key" if r.status_code == 401 else "unreachable"
            elif provider == "gemini":
                r = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/openai/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                status = "ok" if r.status_code == 200 else "invalid_key" if r.status_code in {401, 403} else "unreachable"
            elif provider in _OPENAI_COMPAT_BASE_URLS:
                r = await client.get(
                    f"{_OPENAI_COMPAT_BASE_URLS[provider].rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                status = "ok" if r.status_code == 200 else "invalid_key" if r.status_code in {401, 403} else "unreachable"
            else:
                status = "unchecked"
    except Exception:
        status = "unreachable"
    return {"status": status, "latency_ms": round((time.perf_counter() - started) * 1000)}


def _sensitive(d: dict) -> set[str]:
    """Keys that should be masked on reads and preserved on writes."""
    fixed = {"anthropic_key", "linkedin_cookie", "x_bearer_token", "custom_connector_headers"}
    dynamic = {k for k in d if k.endswith("_api_key") or k.endswith("_key") or k.endswith("_token")}
    return fixed | dynamic


def _log_sensitive_deprecation(payload: dict) -> None:
    """Log a deprecation warning for each secret written to SQLite.

    Environment variables are the preferred storage mechanism; writing
    secrets to the settings database is deprecated.

    Args:
        payload: Settings payload dict that may contain deprecated
            secret keys.
    """
    sensitive_key_map = {
        "apify_token": settings.scraping.apify_key_names.token,
        "apify_actor": settings.scraping.apify_key_names.actor,
        "hunter_api_key": settings.contact.api_key_names.hunter,
        "proxycurl_api_key": settings.contact.api_key_names.proxycurl,
        "x_bearer_token": settings.app.bearer_tokens.x_bearer_token,
        "linkedin_cookie": "LINKEDIN_COOKIE",
        "custom_connector_headers": "CUSTOM_CONNECTOR_HEADERS",
    }
    for settings_key, env_var in sensitive_key_map.items():
        if settings_key in payload and payload[settings_key]:
            _log.warning(
                "Secret '%s' written to SQLite \u2014 deprecated. "
                "Set %s environment variable instead.",
                settings_key, env_var,
            )
