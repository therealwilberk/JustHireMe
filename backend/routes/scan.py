import asyncio
from typing import Any

from fastapi import APIRouter

import services.scanner as scanner
from core.ws_manager import cm
from schemas.requests import HelpChatBody
from schemas.responses import StatusResponse, FreeSourcesScanResponse
from services.job_targets import _profile_for_discovery
from services.scout import _run_free_source_scan

router = APIRouter(prefix="/api/v1", tags=["scan"])


@router.post("/scan", response_model=StatusResponse)
async def scan():
    return await scanner.scan_manager.start_scan()


@router.post("/scan/stop", response_model=StatusResponse)
async def stop_scan():
    return await scanner.scan_manager.stop_scan()


@router.post("/leads/reevaluate", response_model=StatusResponse)
async def reevaluate_jobs():
    return await scanner.scan_manager.start_reevaluate()


@router.post("/leads/reevaluate/stop", response_model=StatusResponse)
async def stop_reevaluate_jobs():
    return await scanner.scan_manager.stop_reevaluate()


@router.post("/leads/cleanup", response_model=dict[str, Any])
async def cleanup_leads(dry_run: bool = False, limit: int = 1000):
    from db.client import cleanup_bad_leads, get_lead_by_id  # lazy: lancedb import takes ~7s

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


@router.post("/free-sources/scan", response_model=FreeSourcesScanResponse)
async def free_sources_scan():
    from db.client import get_settings, get_profile  # lazy: lancedb import takes ~7s

    cfg = get_settings()
    profile = _profile_for_discovery(await asyncio.to_thread(get_profile), cfg)
    leads = await _run_free_source_scan(cfg, "job", profile)
    return {"status": "done", "leads": len(leads)}


@router.post("/help/chat", response_model=dict[str, Any])
async def help_chat(body: HelpChatBody):
    from agents.help_agent import answer  # lazy: agents module (per-request dep)

    history = [item.model_dump() for item in body.history]
    return await asyncio.to_thread(answer, body.question, history)
