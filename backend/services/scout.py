import asyncio

from core.ws_manager import cm
from core.config_constants import _log
from services.job_targets import (
    _profile_x_queries, _profile_free_source_targets,
    _has_x_token, _int_cfg, _truthy, _free_sources_enabled,
    _broadcast_x_source_errors,
)
from log_context import new_context, set_context, reset_context
from config import settings as _cfg
from config.secrets import resolve_secret


async def _run_x_signal_scan(cfg: dict, kind_filter: str, profile: dict | None = None) -> list[dict]:
    ctx = new_context(workflow_type="x_signal_scan", subsystem="scout")
    token = set_context(ctx)
    try:
        if not _has_x_token(cfg):
            return []

        from agents import x_scout  # lazy: agents module (per-request dep)

        kind_filter = "job"
        label = "job leads"
        await cm.broadcast({"type": "agent", "event": "x_scout_start", "msg": f"Scanning X for {label}..."})
        leads = await asyncio.to_thread(
            x_scout.run,
            bearer_token=resolve_secret(
                _cfg.app.bearer_tokens.x_bearer_token,
                _cfg.app.settings_key_names.x_bearer_token,
            ) or None,
            raw_queries=cfg.get("x_search_queries", "") or _profile_x_queries(profile or {}, cfg.get("job_market_focus", "global")),
            raw_watchlist=cfg.get("x_watchlist", ""),
            kind_filter=kind_filter,
            max_requests=_int_cfg(cfg, "x_max_requests_per_scan", 5, 1, 50),
            max_results=_int_cfg(cfg, "x_max_results_per_query", 50, 10, 100),
            min_signal_score=_int_cfg(cfg, "x_min_signal_score", 55, 0, 100),
        )
        await cm.broadcast({"type": "agent", "event": "x_scout_done", "msg": f"X scout - {len(leads)} {label} found"})
        usage = getattr(x_scout, "LAST_USAGE", {}) or {}
        if usage.get("executed_queries"):
            await cm.broadcast({
                "type": "agent",
                "event": "x_usage",
                "msg": f"X usage - {usage.get('executed_queries', 0)} requests, {usage.get('tweets_seen', 0)} posts checked, {usage.get('filtered', 0)} filtered",
            })
        if not leads:
            await _broadcast_x_source_errors(getattr(x_scout, "LAST_ERRORS", []))
        hot_threshold = _int_cfg(cfg, "x_hot_lead_threshold", 80, 1, 100)
        notify_hot = _truthy(cfg.get("x_enable_notifications"))
        for lead in leads:
            await cm.broadcast({"type": "LEAD_UPDATED", "data": lead})
            if (lead.get("signal_score") or 0) >= hot_threshold:
                await cm.broadcast({"type": "agent", "event": "x_hot_lead", "msg": f"Hot X lead: {lead.get('title', '')[:90]}"})
                if notify_hot:
                    await cm.broadcast({"type": "HOT_X_LEAD", "data": lead})
        return leads
    finally:
        reset_context(token)


async def _run_free_source_scan(cfg: dict, kind_filter: str | None = None, profile: dict | None = None) -> list[dict]:
    ctx = new_context(workflow_type="free_source_scan", subsystem="scout")
    token = set_context(ctx)
    try:
        if not _free_sources_enabled(cfg):
            return []

        from agents import free_scout  # lazy: agents module (per-request dep)

        kind_filter = "job"
        label = "job leads"
        await cm.broadcast({"type": "agent", "event": "free_scout_start", "msg": f"Scanning free sources for {label}..."})
        leads = await asyncio.to_thread(
            free_scout.run,
            raw_targets=cfg.get("free_source_targets", "") or _profile_free_source_targets(profile or {}),
            raw_watchlist=cfg.get("company_watchlist", ""),
            raw_custom_connectors=cfg.get("custom_connectors", ""),
            raw_custom_headers=cfg.get("custom_connector_headers", ""),
            custom_connectors_enabled=_truthy(cfg.get("custom_connectors_enabled", "false")),
            kind_filter=kind_filter,
            max_requests=_int_cfg(cfg, "free_source_max_requests", 20, 1, 80),
            min_signal_score=_int_cfg(cfg, "free_source_min_signal_score", 60, 0, 100),
        )
        usage = getattr(free_scout, "LAST_USAGE", {}) or {}
        await cm.broadcast({
            "type": "agent",
            "event": "free_scout_done",
            "msg": f"Free scout - {len(leads)} {label} found ({usage.get('executed', 0)} sources checked)",
        })
        if not leads:
            for msg in (getattr(free_scout, "LAST_ERRORS", []) or [])[:4]:
                await cm.broadcast({"type": "agent", "event": "free_source_error", "msg": f"Free source skipped: {msg}"})
        for lead in leads:
            await cm.broadcast({"type": "LEAD_UPDATED", "data": lead})
        return leads
    finally:
        reset_context(token)
