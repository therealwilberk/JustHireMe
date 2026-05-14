import asyncio

from core.ws_manager import cm
from core.config_constants import _log
from config import settings
from services.job_targets import _job_targets, _profile_for_discovery, _has_x_token, _free_sources_enabled
from services.scanner import _ghost_lock, _job_eval_document
from services.scout import _run_x_signal_scan, _run_free_source_scan
from log_context import new_context, set_context, reset_context


async def _ghost_tick():
    """Run one ghost cycle. Skips if another scan/reevaluate is active."""
    try:
        await asyncio.wait_for(_ghost_lock.acquire(), timeout=0)
    except asyncio.TimeoutError:
        _log.info("ghost tick skipped — another scan or re-evaluation is running")
        return
    try:
        await _ghost_tick_impl()
    finally:
        _ghost_lock.release()


async def _ghost_tick_impl():
    ctx = new_context(workflow_type="ghost_scan", subsystem="scheduler")
    token = set_context(ctx)
    try:
        from db.client import get_setting, get_settings, get_discovered_leads, update_lead_score, get_profile, save_asset_package
        from agents.scout import run as _scout
        from agents.evaluator import score as _score
        from agents.generator import run_package as _gen
        from agents.query_gen import generate as _gen_queries

        cfg = get_settings()
        if get_setting("ghost_mode") != "true":
            return

        profile = _profile_for_discovery(await asyncio.to_thread(get_profile), cfg)
        boards = _job_targets(cfg.get("job_boards", ""), cfg.get("job_market_focus", "global"))
        has_x = _has_x_token(cfg)
        has_free = _free_sources_enabled(cfg)
        if has_x:
            await _run_x_signal_scan(cfg, "job", profile)
        if has_free:
            await _run_free_source_scan(cfg, "job", profile)
        if not boards and not has_x and not has_free:
            await cm.broadcast({"type": "agent", "event": "ghost_warn", "msg": "Ghost Mode: no job boards configured — skipping"})
            return

        await cm.broadcast({"type": "agent", "event": "ghost_scout", "msg": "Ghost Mode: scout cycle starting"})
        try:
            boards = await asyncio.to_thread(_gen_queries, profile, boards, cfg.get("job_market_focus", "global"))
            from config.secrets import resolve_secret
            leads = await asyncio.to_thread(
                _scout,
                urls=boards,
                apify_token=resolve_secret(
                    settings.scraping.apify_key_names.token,
                    settings.scraping.apify_settings_key_names.token,
                ) or None,
                apify_actor=resolve_secret(
                    settings.scraping.apify_key_names.actor,
                    settings.scraping.apify_settings_key_names.actor,
                ) or None,
            )
            await cm.broadcast({"type": "agent", "event": "ghost_scout",
                                "msg": f"Ghost scout complete — {len(leads)} new leads found"})
        except Exception as exc:
            await cm.broadcast({"type": "agent", "event": "ghost_error", "msg": f"Scout failed: {exc}"})
            return

        profile = _profile_for_discovery(await asyncio.to_thread(get_profile), cfg)
        discovered = await asyncio.to_thread(get_discovered_leads)
        await cm.broadcast({"type": "agent", "event": "ghost_eval",
                            "msg": f"Ghost Mode: evaluating {len(discovered)} leads"})

        approved = []
        for lead in discovered:
            try:
                jd = _job_eval_document(lead)
                result = await asyncio.to_thread(_score, jd, profile)
                await asyncio.to_thread(
                    update_lead_score,
                    lead["job_id"], result["score"], result["reason"],
                    result.get("match_points", []), result.get("gaps", []),
                )
                await cm.broadcast({"type": "LEAD_UPDATED", "data": {**lead, **result}})
                if result["score"] >= 85:
                    approved.append({**lead, **result})
                    await cm.broadcast({"type": "agent", "event": "ghost_approved",
                                        "msg": f"Approved: {lead.get('title','')} @ {lead.get('company','')} [{result['score']}/100]"})
            except Exception as exc:
                await cm.broadcast({"type": "agent", "event": "ghost_error",
                                    "msg": f"Eval failed for {lead.get('title','?')}: {exc}"})

        await cm.broadcast({"type": "agent", "event": "ghost_eval",
                            "msg": f"Evaluation done — {len(approved)}/{len(discovered)} approved"})

        if not approved:
            await cm.broadcast({"type": "agent", "event": "ghost_done", "msg": "Ghost Mode: no approved leads this cycle"})
            return

        await cm.broadcast({"type": "agent", "event": "ghost_gen",
                            "msg": f"Ghost Mode: generating assets for {len(approved)} leads"})
        generated = []
        for lead in approved:
            try:
                package = await asyncio.to_thread(_gen, lead)
                await asyncio.to_thread(
                    save_asset_package,
                    lead["job_id"],
                    package["resume"],
                    package["cover_letter"],
                    package.get("selected_projects", []),
                    package.get("keyword_coverage", {}),
                )
                generated.append({
                    **lead,
                    "asset": package["resume"],
                    "resume_asset": package["resume"],
                    "cover_letter_asset": package["cover_letter"],
                    "selected_projects": package.get("selected_projects", []),
                    "keyword_coverage": package.get("keyword_coverage", {}),
                })
                await cm.broadcast({"type": "agent", "event": "ghost_gen",
                                    "msg": f"Generated resume and cover letter for {lead.get('title','?')}"})
            except Exception as exc:
                await cm.broadcast({"type": "agent", "event": "ghost_error",
                                    "msg": f"Generation failed for {lead.get('title','?')}: {exc}"})

        if get_setting("auto_apply", "false") != "true":
            await cm.broadcast({"type": "agent", "event": "ghost_done",
                                "msg": f"Ghost cycle complete — {len(generated)} leads ready. Auto-apply is OFF."})
            return

        from agents.actuator import run as _act
        from db.client import get_lead_for_fire, mark_applied
        await cm.broadcast({"type": "agent", "event": "ghost_apply",
                            "msg": f"Ghost Mode: auto-applying to {len(generated)} leads"})
        for item in generated:
            try:
                lead, asset = await asyncio.to_thread(get_lead_for_fire, item["job_id"])
                from main import _fire_blocker
                _status, detail = _fire_blocker(lead, asset)
                if detail:
                    await cm.broadcast({"type": "agent", "event": "ghost_error",
                                        "msg": f"Submission blocked: {item.get('title','?')} - {detail}"})
                    continue

                ok = await asyncio.to_thread(_act, lead, asset)
                if ok:
                    await asyncio.to_thread(mark_applied, item["job_id"])
                    await cm.broadcast({"type": "agent", "event": "ghost_applied",
                                        "msg": f"Applied: {item.get('title','?')} @ {item.get('company','?')}"})
                else:
                    await cm.broadcast({"type": "agent", "event": "ghost_error",
                                        "msg": f"Submission failed: {item.get('title','?')}"})
            except Exception as exc:
                await cm.broadcast({"type": "agent", "event": "ghost_error",
                                    "msg": f"Actuator error for {item.get('title','?')}: {exc}"})

        await cm.broadcast({"type": "agent", "event": "ghost_done", "msg": "Ghost cycle complete."})
    finally:
        reset_context(token)
