import asyncio

from fastapi import APIRouter, HTTPException

import services.scanner as scanner
from core.ws_manager import cm
from schemas.requests import HelpChatBody

router = APIRouter(prefix="/api/v1", tags=["scan"])


@router.post("/scan")
async def scan():
    if scanner._ghost_lock.locked():
        raise HTTPException(status_code=409, detail="Scan already in progress (ghost mode active)")
    if scanner._scan_task and not scanner._scan_task.done():
        raise HTTPException(status_code=409, detail="Scan already running")
    if scanner._reevaluate_task and not scanner._reevaluate_task.done():
        raise HTTPException(status_code=409, detail="Re-evaluation already running")
    scanner._scan_stop.clear()
    scanner._scan_task = asyncio.create_task(scanner._run_scan_task())
    return {"status": "scanning"}


@router.post("/scan/stop")
async def stop_scan():
    if not scanner._scan_task or scanner._scan_task.done():
        return {"status": "idle"}
    scanner._scan_stop.set()
    await cm.broadcast({"type": "agent", "event": "eval_done", "msg": "Scan stopped by user."})
    return {"status": "stopping"}


@router.post("/leads/reevaluate")
async def reevaluate_jobs():
    if scanner._ghost_lock.locked():
        raise HTTPException(status_code=409, detail="Re-evaluation already in progress (ghost mode active)")
    if scanner._reevaluate_task and not scanner._reevaluate_task.done():
        raise HTTPException(status_code=409, detail="Re-evaluation already running")
    if scanner._scan_task and not scanner._scan_task.done():
        raise HTTPException(status_code=409, detail="Scan already running")
    scanner._reevaluate_stop.clear()
    scanner._reevaluate_task = asyncio.create_task(scanner._run_reevaluate_jobs_task())
    return {"status": "reevaluating"}


@router.post("/leads/reevaluate/stop")
async def stop_reevaluate_jobs():
    if not scanner._reevaluate_task or scanner._reevaluate_task.done():
        return {"status": "idle"}
    scanner._reevaluate_stop.set()
    await cm.broadcast({"type": "agent", "event": "reeval_done", "msg": "Re-evaluation stopped by user."})
    return {"status": "stopping"}


@router.post("/leads/cleanup")
async def cleanup_leads(dry_run: bool = False, limit: int = 1000):
    from db.client import cleanup_bad_leads, get_lead_by_id

    await cm.broadcast({
        "type": "agent",
        "event": "cleanup_start",
        "msg": f"Scanning up to {limit} leads for bad data...",
    })
    result = await asyncio.to_thread(cleanup_bad_leads, limit, dry_run)

    if not dry_run:
        for item in result.get("items", [])[:100]:
            lead = await asyncio.to_thread(get_lead_by_id, item["job_id"])
            if lead:
                await cm.broadcast({"type": "LEAD_UPDATED", "data": lead})

    action = "would discard" if dry_run else "discarded"
    await cm.broadcast({
        "type": "agent",
        "event": "cleanup_done",
        "msg": f"Cleanup scanned {result['scanned']} leads and {action} {result['candidates']} bad rows.",
    })
    return result


@router.post("/free-sources/scan")
async def free_sources_scan():
    from db.client import get_settings, get_profile
    from services.job_targets import _profile_for_discovery
    from services.scout import _run_free_source_scan

    cfg = get_settings()
    profile = _profile_for_discovery(await asyncio.to_thread(get_profile), cfg)
    leads = await _run_free_source_scan(cfg, "job", profile)
    return {"status": "done", "leads": len(leads)}


@router.post("/help/chat")
async def help_chat(body: HelpChatBody):
    from agents.help_agent import answer

    history = [item.model_dump() for item in body.history]
    return await asyncio.to_thread(answer, body.question, history)
