import asyncio

from core.ws_manager import cm
from core.config_constants import _log
from config import settings
from services.job_targets import _job_targets, _profile_for_discovery, _has_x_token, _free_sources_enabled
from services.scanner import ScanManager, scan_manager, _job_eval_document
from services.scout import _run_x_signal_scan, _run_free_source_scan
from log_context import new_context, set_context, reset_context
from config.secrets import resolve_secret


class GhostService:
    def __init__(self, scan_manager: ScanManager) -> None:
        self._scan_manager = scan_manager

    async def run(self) -> None:
        ctx = new_context(workflow_type="ghost_scan", subsystem="scheduler")
        token = set_context(ctx)
        try:
            result = await self._phase_preflight()
            if result is None:
                return
            cfg, profile, boards = result
            await self._phase_x_scan(cfg, profile)
            await self._phase_free_scan(cfg, profile)
            await self._phase_scout(cfg, profile, boards)
            approved = await self._phase_eval(cfg, profile)
            if not approved:
                return
            generated = await self._phase_gen(approved)
            await self._phase_apply(generated)
        finally:
            reset_context(token)

    async def _phase_preflight(self) -> tuple[dict, dict, list[str]] | None:
        from db.client import get_setting, get_settings, get_profile  # lazy: lancedb import takes ~7s

        cfg = get_settings()
        if get_setting("ghost_mode") != "true":
            return None

        profile = _profile_for_discovery(await asyncio.to_thread(get_profile), cfg)
        boards = _job_targets(cfg.get("job_boards", ""), cfg.get("job_market_focus", "global"))
        has_x = _has_x_token(cfg)
        has_free = _free_sources_enabled(cfg)
        if not boards and not has_x and not has_free:
            await cm.broadcast({"type": "agent", "event": "ghost_warn", "msg": "Ghost Mode: no job targets configured — add targets in Settings"})
            return None

        return (cfg, profile, boards)

    async def _phase_x_scan(self, cfg: dict, profile: dict) -> None:
        if _has_x_token(cfg):
            await _run_x_signal_scan(cfg, "job", profile)

    async def _phase_free_scan(self, cfg: dict, profile: dict) -> None:
        if _free_sources_enabled(cfg):
            await _run_free_source_scan(cfg, "job", profile)

    async def _phase_scout(self, cfg: dict, profile: dict, boards: list[str]) -> None:
        from agents.query_gen import generate as _gen_queries  # lazy: agents module (per-request dep)
        from agents.scout import run as _scout  # lazy: agents module (per-request dep)

        await cm.broadcast({"type": "agent", "event": "ghost_scout", "msg": "Ghost Mode: scout cycle starting"})
        try:
            boards = await asyncio.to_thread(_gen_queries, profile, boards, cfg.get("job_market_focus", "global"))
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

    async def _phase_eval(self, cfg: dict, profile: dict) -> list[dict]:
        from db.client import get_discovered_leads, update_lead_score, get_profile  # lazy: lancedb import takes ~7s
        from agents.evaluator import score as _score  # lazy: agents module (per-request dep)

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

        return approved

    async def _phase_gen(self, approved: list[dict]) -> list[dict]:
        from agents.generator import run_package as _gen  # lazy: agents module (per-request dep)
        from db.client import save_asset_package  # lazy: lancedb import takes ~7s

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
        return generated

    async def _phase_apply(self, generated: list[dict]) -> None:
        from db.client import get_setting  # lazy: lancedb import takes ~7s
        if get_setting("auto_apply", "false") != "true":
            await cm.broadcast({"type": "agent", "event": "ghost_done",
                                "msg": f"Ghost cycle complete — {len(generated)} leads ready. Auto-apply is OFF."})
            return

        from agents.actuator import run as _act  # lazy: agents module (per-request dep)
        from db.client import get_lead_for_fire, mark_applied  # lazy: lancedb import takes ~7s
        await cm.broadcast({"type": "agent", "event": "ghost_apply",
                            "msg": f"Ghost Mode: auto-applying to {len(generated)} leads"})
        for item in generated:
            try:
                lead, asset = await asyncio.to_thread(get_lead_for_fire, item["job_id"])
                from main import _fire_blocker  # lazy: avoids circular import
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


async def _ghost_tick() -> None:
    """Run one ghost cycle. Skips if another scan/reevaluate is active."""
    try:
        await asyncio.wait_for(scan_manager._ghost_lock.acquire(), timeout=0)
    except asyncio.TimeoutError:
        _log.info("ghost tick skipped — another scan or re-evaluation is running")
        return
    try:
        await GhostService(scan_manager).run()
    finally:
        scan_manager._ghost_lock.release()
