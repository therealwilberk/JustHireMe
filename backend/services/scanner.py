"""Scan orchestration and state management.

Provides the ScanManager lifecycle state machine for scan, re-evaluate,
and ghost mode coordination, plus the core scan and re-evaluate pipelines.
"""

import asyncio

from fastapi import HTTPException

from core.ws_manager import cm
from core.config_constants import _log
from config import settings
from services.job_targets import (
    _job_targets, _profile_for_discovery,
)
from services.scout import _run_x_signal_scan, _run_free_source_scan
from config.secrets import resolve_secret


class ScanManager:
    """Lifecycle state machine for scan/reevaluate/ghost operations.

    Manages concurrent access to scan and re-evaluation tasks via an
    asyncio lock and dedicated stop events.  Only one scan, one
    re-evaluation, or one ghost cycle may run at a time.
    """

    def __init__(self) -> None:
        """Initialize scan manager with idle task/event/lock state."""
        self._scan_task: asyncio.Task | None = None
        self._scan_stop: asyncio.Event = asyncio.Event()
        self._reevaluate_task: asyncio.Task | None = None
        self._reevaluate_stop: asyncio.Event = asyncio.Event()
        self._ghost_lock: asyncio.Lock = asyncio.Lock()

    async def start_scan(self) -> dict:
        """Start a new scan cycle.

        Raises:
            HTTPException 409: If ghost mode is active, a scan is already
                running, or a re-evaluation is already running.

        Returns:
            dict: ``{"status": "scanning"}`` on success.
        """
        if self._ghost_lock.locked():
            raise HTTPException(status_code=409, detail="Scan already in progress (ghost mode active)")
        if self._scan_task and not self._scan_task.done():
            raise HTTPException(status_code=409, detail="Scan already running")
        if self._reevaluate_task and not self._reevaluate_task.done():
            raise HTTPException(status_code=409, detail="Re-evaluation already running")
        self._scan_stop.clear()
        self._scan_task = asyncio.create_task(self._run_scan_task())
        return {"status": "scanning"}

    async def stop_scan(self) -> dict:
        """Request cancellation of the currently running scan.

        Returns:
            dict: ``{"status": "stopping"}`` if a scan was running,
            ``{"status": "idle"}`` otherwise.
        """
        if not self._scan_task or self._scan_task.done():
            return {"status": "idle"}
        self._scan_stop.set()
        self._scan_task.cancel()
        await cm.broadcast({"type": "agent", "event": "eval_done", "msg": "Scan stopped by user."})
        return {"status": "stopping"}

    async def start_reevaluate(self) -> dict:
        """Start a new re-evaluation cycle.

        Raises:
            HTTPException 409: If ghost mode is active, a re-evaluation
                is already running, or a scan is already running.

        Returns:
            dict: ``{"status": "reevaluating"}`` on success.
        """
        if self._ghost_lock.locked():
            raise HTTPException(status_code=409, detail="Re-evaluation already in progress (ghost mode active)")
        if self._reevaluate_task and not self._reevaluate_task.done():
            raise HTTPException(status_code=409, detail="Re-evaluation already running")
        if self._scan_task and not self._scan_task.done():
            raise HTTPException(status_code=409, detail="Scan already running")
        self._reevaluate_stop.clear()
        self._reevaluate_task = asyncio.create_task(self._run_reevaluate_jobs_task())
        return {"status": "reevaluating"}

    async def stop_reevaluate(self) -> dict:
        """Request cancellation of the running re-evaluation.

        Returns:
            dict: ``{"status": "stopping"}`` if a re-evaluation was
            running, ``{"status": "idle"}`` otherwise.
        """
        if not self._reevaluate_task or self._reevaluate_task.done():
            return {"status": "idle"}
        self._reevaluate_stop.set()
        self._reevaluate_task.cancel()
        await cm.broadcast({"type": "agent", "event": "reeval_done", "msg": "Re-evaluation stopped by user."})
        return {"status": "stopping"}

    def is_scanning(self) -> bool:
        """Check whether a scan is currently running.

        Returns:
            bool: True if a scan task exists and has not completed.
        """
        return bool(self._scan_task and not self._scan_task.done())

    def is_reevaluating(self) -> bool:
        """Check whether a re-evaluation is currently running.

        Returns:
            bool: True if a re-evaluation task exists and has not completed.
        """
        return bool(self._reevaluate_task and not self._reevaluate_task.done())

    async def _run_scan_task(self) -> None:
        """Acquire the ghost lock and delegate to ``_run_scan``.

        Catches ``CancelledError`` for clean user-initiated stops and
        broadcasts failure messages on unexpected exceptions.
        """
        try:
            await asyncio.wait_for(self._ghost_lock.acquire(), timeout=0)
        except asyncio.TimeoutError:
            _log.warning("scan task skipped — ghost lock held")
            return
        try:
            await _run_scan()
        except asyncio.CancelledError:
            _log.info("scan cancelled by user")
        except Exception as exc:
            _log.error("scan failed: %s", exc)
            await cm.broadcast({"type": "agent", "event": "eval_done", "msg": f"Scan failed: {exc}"})
        finally:
            self._scan_task = None
            self._ghost_lock.release()

    async def _run_reevaluate_jobs_task(self) -> None:
        """Acquire the ghost lock and delegate to ``_run_reevaluate_jobs``.

        Catches ``CancelledError`` for clean user-initiated stops and
        broadcasts failure messages on unexpected exceptions.
        """
        try:
            await asyncio.wait_for(self._ghost_lock.acquire(), timeout=0)
        except asyncio.TimeoutError:
            _log.warning("reevaluate task skipped — ghost lock held")
            return
        try:
            await _run_reevaluate_jobs()
        except asyncio.CancelledError:
            _log.info("reevaluate cancelled by user")
        except Exception as exc:
            _log.error("reevaluate failed: %s", exc)
            await cm.broadcast({"type": "agent", "event": "reeval_done", "msg": f"Re-evaluation failed: {exc}"})
        finally:
            self._reevaluate_task = None
            self._ghost_lock.release()


scan_manager = ScanManager()

_REEVALUATION_STATUS_LOCKS = {
    "active", "approved", "applied", "interviewing", "offer", "hired", "archived",
    "rejected", "accepted", "discarded",
}


def _should_preserve_job_status(status: str) -> bool:
    """Determine whether a job status should be preserved during re-evaluation.

    Terminal or actionable statuses (approved, applied, interviewing, etc.)
    should not be overwritten by a re-score.

    Args:
        status: The current job lead status string.

    Returns:
        True if the status is in the preserved set.
    """
    return status in _REEVALUATION_STATUS_LOCKS


def _job_eval_document(lead: dict) -> str:
    """Format a job lead into a plain-text evaluation document.

    Args:
        lead: A job lead dictionary with keys ``title``, ``company``,
            ``url``, and optionally ``description``.

    Returns:
        A multi-line string suitable for consumption by the evaluator agent.
    """
    desc = (lead.get("description") or "").strip()
    return (
        f"Job Title: {lead.get('title','')}\n"
        f"Company: {lead.get('company','')}\n"
        f"URL: {lead.get('url','')}\n"
        + (f"Description: {desc}" if desc else "")
    )


async def _run_reevaluate_jobs() -> None:
    """Re-evaluate all stored job leads against the current profile.

    Iterates over leads returned by ``get_job_leads_for_evaluation``,
    submits each as an evaluation document to the scoring agent, and
    persists updated scores.  Respects the re-evaluation stop event for
    early termination.
    """
    from db.client import get_settings, get_job_leads_for_evaluation, get_lead_by_id, update_lead_score, get_profile  # lazy: lancedb import takes ~7s
    from agents.evaluator import score as _score  # lazy: agents module (per-request dep)

    cfg = await asyncio.to_thread(get_settings)
    profile = await asyncio.to_thread(get_profile)
    jobs = await asyncio.to_thread(get_job_leads_for_evaluation)
    total = len(jobs)
    scored = 0
    failed = 0

    await cm.broadcast({
        "type": "agent",
        "event": "reeval_start",
        "msg": f"Re-evaluating {total} job leads via {cfg.get('llm_provider', 'ollama')}",
    })

    for index, lead in enumerate(jobs, start=1):
        if scan_manager._reevaluate_stop.is_set():
            await cm.broadcast({
                "type": "agent",
                "event": "reeval_done",
                "msg": f"Re-evaluation stopped after {scored}/{total} jobs.",
            })
            return

        try:
            result = await asyncio.to_thread(_score, _job_eval_document(lead), profile)
            preserve_status = _should_preserve_job_status(lead.get("status", ""))
            await asyncio.to_thread(
                update_lead_score,
                lead["job_id"], result["score"], result["reason"],
                result.get("match_points", []), result.get("gaps", []),
                preserve_status,
            )
            saved = await asyncio.to_thread(get_lead_by_id, lead["job_id"])
            await cm.broadcast({"type": "LEAD_UPDATED", "data": saved or {**lead, **result}})
            scored += 1
            await cm.broadcast({
                "type": "agent",
                "event": "reeval_scored",
                "msg": f"[{index}/{total}] Re-scored {lead.get('title','')} = {result['score']}/100",
            })
        except Exception as e:
            failed += 1
            await cm.broadcast({
                "type": "agent",
                "event": "reeval_error",
                "msg": f"Re-eval failed for {lead.get('title','')}: {e}",
            })

    summary = f"Re-evaluation complete - {scored}/{total} jobs scored"
    if failed:
        summary += f", {failed} failed"
    await cm.broadcast({"type": "agent", "event": "reeval_done", "msg": summary})


async def _run_scan() -> None:
    """Execute a full scan cycle.

    Pipeline steps:
        1. X/Twitter signal scan
        2. Free source signal scan
        3. Profile-tailored search query generation
        4. Scout (job board scraping via Apify)
        5. LLM evaluation of discovered leads

    Respects ``scan_manager._scan_stop`` for early termination between
    phases and during evaluation.
    """
    from db.client import get_settings, get_discovered_leads, update_lead_score, get_profile  # lazy: lancedb import takes ~7s
    from agents.scout import run as _scout  # lazy: agents module (per-request dep)
    from agents.evaluator import score as _score  # lazy: agents module (per-request dep)
    from agents.query_gen import generate as _gen_queries  # lazy: agents module (per-request dep)

    cfg     = get_settings()
    profile = _profile_for_discovery(get_profile(), cfg)
    market_focus = cfg.get("job_market_focus", "global")
    raw_urls = _job_targets(cfg.get("job_boards", ""), market_focus)
    if not raw_urls:
        await cm.broadcast({"type": "agent", "event": "eval_done",
                            "msg": "No job targets configured — add targets in Settings to start scanning."})
        _log.warning("Scan skipped: no job targets configured")
        return
    await _run_x_signal_scan(cfg, "job", profile)
    await _run_free_source_scan(cfg, "job", profile)

    await cm.broadcast({"type": "agent", "event": "query_gen_start",
                        "msg": "Generating profile-tailored search queries\u2026"})
    try:
        urls = await asyncio.to_thread(_gen_queries, profile, raw_urls, market_focus)
        await cm.broadcast({"type": "agent", "event": "query_gen_done",
                            "msg": f"Search plan ready \u2014 {len(urls)} targets"})
        for u in urls:
            await cm.broadcast({"type": "agent", "event": "query_gen_target", "msg": u})
    except Exception as exc:
        urls = raw_urls
        await cm.broadcast({"type": "agent", "event": "query_gen_error",
                            "msg": f"Query generation failed ({exc}), using raw URLs"})

    await cm.broadcast({"type": "agent", "event": "scout_start", "msg": f"Launching scan for {len(urls)} targets\u2026"})

    leads = await asyncio.to_thread(
        _scout,
        urls=urls,
        apify_token=resolve_secret(
            settings.scraping.apify_key_names.token,
            settings.scraping.apify_settings_key_names.token,
        ) or None,
        apify_actor=resolve_secret(
            settings.scraping.apify_key_names.actor,
            settings.scraping.apify_settings_key_names.actor,
        ) or None,
    )
    await cm.broadcast({"type": "agent", "event": "scout_done", "msg": f"Scout finished \u2014 {len(leads)} new leads found"})

    if scan_manager._scan_stop.is_set():
        await cm.broadcast({"type": "agent", "event": "eval_done", "msg": "Scan stopped after scouting."})
        return

    discovered = await asyncio.to_thread(get_discovered_leads)
    await cm.broadcast({"type": "agent", "event": "eval_start", "msg": f"Evaluating {len(discovered)} leads via {cfg.get('llm_provider', 'ollama')}"})

    for lead in discovered:
        if scan_manager._scan_stop.is_set():
            await cm.broadcast({"type": "agent", "event": "eval_done", "msg": "Scan stopped during evaluation."})
            return
        try:
            desc = (lead.get("description") or "").strip()
            jd = (
                f"Job Title: {lead.get('title','')}\n"
                f"Company: {lead.get('company','')}\n"
                f"URL: {lead.get('url','')}\n"
                + (f"Description: {desc}" if desc else "")
            )
            result = await asyncio.to_thread(_score, jd, profile)
            await asyncio.to_thread(
                update_lead_score,
                lead["job_id"], result["score"], result["reason"],
                result.get("match_points", []), result.get("gaps", []),
            )
            await cm.broadcast({"type": "LEAD_UPDATED", "data": {**lead, **result}})
            await cm.broadcast({"type": "agent", "event": "eval_scored", "msg": f"Scored {lead.get('title','')} = {result['score']}/100"})
        except Exception as e:
            await cm.broadcast({"type": "agent", "event": "eval_error", "msg": f"Eval failed for {lead.get('title','')}: {e}"})

    await cm.broadcast({"type": "agent", "event": "eval_done", "msg": "Evaluation cycle complete"})
