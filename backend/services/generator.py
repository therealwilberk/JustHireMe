"""Resume and cover letter generation with fire blocking.

Provides the generation pipeline (``_generate_one``) and application
submission (``_actuate``), along with the ``_fire_blocker`` guard that
validates lead/asset state before submission.
"""

import asyncio
import os

from fastapi import HTTPException

from core.ws_manager import cm


def _asset_ready(path: str) -> bool:
    """Check whether a file exists at the given path.

    Args:
        path: Filesystem path string.

    Returns:
        True if the path is non-empty and points to an existing file.
    """
    return bool(path) and os.path.isfile(path)


def _fire_blocker(lead: dict, asset: str) -> tuple[int, str]:
    """Validate that a lead is ready for application submission.

    Checks: lead exists, not already applied, has a URL, and both
    resume and cover letter assets exist on disk.

    Args:
        lead: Job lead dictionary with ``status``, ``url``,
            ``cover_letter_asset`` / ``cover_letter_path`` keys.
        asset: Path to the generated resume file.

    Returns:
        A ``(status_code, detail_message)`` tuple.  ``(0, "")`` means
        the lead passed all checks and is clear to fire.
    """
    if not lead:
        return 404, "Lead not found"
    if lead.get("status") == "applied":
        return 409, "Lead is already marked applied"
    if not lead.get("url"):
        return 409, "Lead has no application URL"
    if not _asset_ready(asset):
        return 409, "Generate a resume before firing this application"
    cover = lead.get("cover_letter_asset") or lead.get("cover_letter_path") or ""
    if not _asset_ready(cover):
        return 409, "Generate a cover letter before firing this application"
    return 0, ""


async def _generate_one(jid: str) -> dict:
    """Generate a resume, cover letter, and contact info for a single lead.

    Fetches the lead, delegates to the generator agent, persists assets
    and outreach messages to the database, and performs a contact lookup.

    Args:
        jid: Job lead ID string.

    Returns:
        Enriched lead dictionary with generated asset keys.

    Raises:
        HTTPException 404: If the lead is not found.
        HTTPException 500: If generation fails.
    """
    from agents.generator import run_package as _gen  # lazy: agents module (per-request dep)
    from agents.contact_lookup import run as _contact_lookup  # lazy: agents module (per-request dep)
    from db.client import get_lead_by_id, save_asset_package, save_contact_lookup, get_setting  # lazy: lancedb import takes ~7s
    lead = get_lead_by_id(jid)
    if not lead:
        await cm.broadcast({"type": "agent", "event": "gen_error", "msg": f"Lead {jid} not found"})
        raise HTTPException(status_code=404, detail="Lead not found")
    template = get_setting("resume_template", "")
    await cm.broadcast({"type": "agent", "event": "gen_start",
                        "msg": f"Generating for {lead.get('title','?')} @ {lead.get('company','?')}"})
    try:
        package = await asyncio.to_thread(_gen, lead, template)
        save_asset_package(
            jid,
            package["resume"],
            package["cover_letter"],
            package.get("selected_projects", []),
            package.get("keyword_coverage", {}),
        )
        # Save AI-generated outreach messages alongside the package
        _outreach_fields = {}
        if package.get("founder_message"):
            _outreach_fields["outreach_reply"] = package["founder_message"]
        if package.get("linkedin_note"):
            _outreach_fields["outreach_dm"] = package["linkedin_note"]
        if package.get("cold_email"):
            _outreach_fields["outreach_email"] = package["cold_email"]
        if _outreach_fields:
            from db.client import get_sql_connection  # lazy: lancedb import takes ~7s
            c = get_sql_connection()
            sets = ", ".join(f"{k}=?" for k in _outreach_fields)
            vals = list(_outreach_fields.values()) + [jid]
            c.execute(f"UPDATE leads SET {sets} WHERE job_id=?", vals)
            c.commit()
            c.close()
        enriched_lead = {
            **lead,
            "asset": package["resume"],
            "resume_asset": package["resume"],
            "cover_letter_asset": package["cover_letter"],
            "selected_projects": package.get("selected_projects", []),
            "keyword_coverage": package.get("keyword_coverage", {}),
            "outreach_reply": package.get("founder_message", lead.get("outreach_reply", "")),
            "outreach_dm": package.get("linkedin_note", lead.get("outreach_dm", "")),
            "outreach_email": package.get("cold_email", lead.get("outreach_email", "")),
            "status": "approved",
        }
        contact_lookup = await asyncio.to_thread(_contact_lookup, enriched_lead)
        save_contact_lookup(jid, contact_lookup)
        enriched_lead["contact_lookup"] = contact_lookup
        enriched_meta = dict(enriched_lead.get("source_meta") or {})
        enriched_meta["contact_lookup"] = contact_lookup
        enriched_lead["source_meta"] = enriched_meta
        await cm.broadcast({"type": "LEAD_UPDATED", "data": {
            **enriched_lead,
        }})
        await cm.broadcast({"type": "agent", "event": "gen_done", "msg": f"Resume and cover letter ready: {lead.get('title','?')}"})
        return enriched_lead
    except Exception as exc:
        await cm.broadcast({"type": "agent", "event": "gen_error",
                            "msg": f"Generation failed for {lead.get('title','?')}: {exc}"})
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


async def _actuate(jid: str) -> None:
    """Submit an application for a single job lead via the actuator agent.

    Runs the fire-blocker check before delegating to the actuator.
    Broadcasts success/failure events over the WebSocket.

    Args:
        jid: Job lead ID string.
    """
    from agents.actuator import run as _act  # lazy: agents module (per-request dep)
    from db.client import get_lead_for_fire, mark_applied  # lazy: lancedb import takes ~7s
    try:
        lead, asset = await asyncio.to_thread(get_lead_for_fire, jid)
        _status, detail = _fire_blocker(lead, asset)
        if detail:
            await cm.broadcast({"type": "agent", "event": "failed", "job_id": jid,
                                "msg": f"Submission blocked for {jid}: {detail}"})
            return

        await cm.broadcast({"type": "agent", "event": "actuating", "job_id": jid,
                            "msg": f"Opening browser for {lead.get('title','')} @ {lead.get('company','')}"})
        ok = await asyncio.to_thread(_act, lead, asset)
    except Exception as exc:
        await cm.broadcast({"type": "agent", "event": "failed", "job_id": jid,
                            "msg": f"Submission failed for {jid}: {exc}"})
        return

    if ok:
        await asyncio.to_thread(mark_applied, jid)
        await cm.broadcast({"type": "agent", "event": "applied", "job_id": jid,
                            "msg": f"Application submitted for {jid}"})
    else:
        await cm.broadcast({"type": "agent", "event": "failed", "job_id": jid,
                            "msg": f"Submission failed for {jid}"})
