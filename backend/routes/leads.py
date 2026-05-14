"""Lead CRUD, pipeline execution, CSV export, and follow-up management."""

import asyncio
import csv
import io
import os
import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from core.ws_manager import cm
from log_context import new_context, reset_context, set_context
from schemas.requests import (
    FeedbackBody,
    FollowupBody,
    ManualLeadBody,
    StatusBody,
)
from schemas.responses import OkResponse, LeadGenerateResponse, PipelineRunResponse

router = APIRouter(prefix="/api/v1", tags=["leads"])


def _annotate_job_lead(lead: dict) -> dict:
    """Classify seniority level and enrich lead metadata inline.

    Args:
        lead: Raw lead dict from the database.

    Returns:
        Lead dict with source_meta enriched and seniority_level set.
    """
    from agents.scout import classify_job_seniority  # lazy: agents module (per-request dep)
    meta = dict(lead.get("source_meta") or {})
    level = str(meta.get("seniority_level") or lead.get("seniority_level") or "").strip().lower()
    if level not in {"fresher", "junior", "mid", "senior", "unknown"}:
        level = classify_job_seniority(lead)
    meta["seniority_level"] = level
    meta["is_beginner"] = level in {"fresher", "junior"}
    return {**lead, "source_meta": meta, "seniority_level": level}


def _versioned_assets(job_id: str, base_dir: str) -> list[dict]:
    """Discover versioned resume and cover letter PDFs on disk.

    Args:
        job_id: Unique job identifier used in asset filenames.
        base_dir: Directory to scan for asset files.

    Returns:
        List of version dicts sorted newest-first, each with optional
        ``resume`` and ``cover_letter`` keys.
    """
    versions: dict[int, dict] = {}
    patterns = [
        ("resume", re.compile(rf"^{re.escape(job_id)}_v(\d+)\.pdf$")),
        ("cover_letter", re.compile(rf"^{re.escape(job_id)}_cl_v(\d+)\.pdf$")),
    ]
    try:
        names = os.listdir(base_dir)
    except Exception:
        return []
    for name in names:
        full = os.path.join(base_dir, name)
        if not os.path.isfile(full):
            continue
        for key, pattern in patterns:
            match = pattern.match(name)
            if match:
                version = int(match.group(1))
                versions.setdefault(version, {"version": version})[key] = full
    return [versions[v] for v in sorted(versions, reverse=True)]


@router.get("/leads", response_model=list[dict[str, Any]])
async def leads(beginner_only: bool = False, seniority: str | None = None):
    """GET /api/v1/leads — Retrieve all job leads, optionally filtered by seniority.

    Args:
        beginner_only: When true, return only fresher/junior leads.
        seniority: Optional seniority level filter string.

    Returns:
        List of annotated lead dicts.
    """
    from db.client import get_all_leads  # lazy: lancedb import takes ~7s
    jobs = [_annotate_job_lead(lead) for lead in get_all_leads() if (lead.get("kind") or "job") == "job"]
    requested = str(seniority or "").strip().lower()
    if beginner_only or requested == "beginner":
        return [lead for lead in jobs if lead.get("seniority_level") in {"fresher", "junior"}]
    if requested in {"fresher", "junior", "mid", "senior", "unknown"}:
        return [lead for lead in jobs if lead.get("seniority_level") == requested]
    return jobs


@router.get("/leads/export.csv")
async def export_leads_csv():
    """GET /api/v1/leads/export.csv — Export all leads as a CSV download.

    Returns:
        StreamingResponse with CSV content.
    """
    from db.client import get_all_leads  # lazy: lancedb import takes ~7s
    rows = get_all_leads()
    fields = [
        "job_id", "title", "company", "url", "platform", "status",
        "score", "signal_score", "seniority_level", "location",
        "reason", "created_at",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jhm_pipeline.csv"},
    )


@router.get("/leads/{job_id}/versions", response_model=list[dict[str, Any]])
async def get_lead_versions(job_id: str):
    """GET /api/v1/leads/{job_id}/versions — List versioned PDF assets for a lead.

    Args:
        job_id: Unique job identifier.

    Returns:
        List of version dicts with resume/cover_letter paths.

    Raises:
        HTTPException 404: Lead not found.
    """
    from db.client import get_lead_by_id, data_base  # lazy: lancedb import takes ~7s
    lead = get_lead_by_id(job_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    paths = [
        lead.get("resume_asset") or lead.get("asset") or "",
        lead.get("cover_letter_asset") or "",
    ]
    base_dir = next((os.path.dirname(path) for path in paths if path), None)
    if not base_dir:
        base_dir = os.path.join(data_base(), "assets")
    return _versioned_assets(job_id, base_dir)


@router.get("/leads/{job_id}", response_model=dict[str, Any])
async def get_lead(job_id: str):
    """GET /api/v1/leads/{job_id} — Retrieve a single lead by ID.

    Args:
        job_id: Unique job identifier.

    Returns:
        Lead dict, annotated with seniority for job leads.

    Raises:
        HTTPException 404: Lead not found.
    """
    from db.client import get_lead_by_id  # lazy: lancedb import takes ~7s
    lead = get_lead_by_id(job_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _annotate_job_lead(lead) if (lead.get("kind") or "job") == "job" else lead


@router.delete("/leads/{job_id}", response_model=OkResponse)
async def delete_lead_endpoint(job_id: str):
    """DELETE /api/v1/leads/{job_id} — Delete a lead by ID.

    Args:
        job_id: Unique job identifier.

    Returns:
        OkResponse with ok: true.

    Raises:
        HTTPException 404: Lead not found.
    """
    from db.client import delete_lead  # lazy: lancedb import takes ~7s
    try:
        delete_lead(job_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="lead not found")
    return {"ok": True}


@router.put("/leads/{job_id}/status", response_model=OkResponse)
async def update_status(job_id: str, body: StatusBody):
    """PUT /api/v1/leads/{job_id}/status — Update lead status and broadcast change.

    Args:
        job_id: Unique job identifier.
        body: Request body with new status value.

    Returns:
        OkResponse with ok: true.

    Raises:
        HTTPException 404: Lead not found.
        HTTPException 400: Invalid status value.
    """
    from db.client import update_lead_status  # lazy: lancedb import takes ~7s
    try:
        update_lead_status(job_id, body.status)
        await cm.broadcast({"type": "LEAD_UPDATED", "data": {"job_id": job_id, "status": body.status}})
        return {"ok": True}
    except LookupError:
        raise HTTPException(status_code=404, detail="lead not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/leads/{job_id}/feedback", response_model=dict[str, Any])
async def update_feedback(job_id: str, body: FeedbackBody):
    """PUT /api/v1/leads/{job_id}/feedback — Save feedback note for a lead.

    Args:
        job_id: Unique job identifier.
        body: Request body with feedback and optional note.

    Returns:
        Updated lead dict.

    Raises:
        HTTPException 400: Invalid feedback value.
        HTTPException 404: Lead not found.
    """
    from db.client import save_lead_feedback  # lazy: lancedb import takes ~7s
    try:
        lead = save_lead_feedback(job_id, body.feedback, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await cm.broadcast({"type": "LEAD_UPDATED", "data": lead})
    return lead


@router.put("/leads/{job_id}/followup", response_model=dict[str, Any])
async def update_followup(job_id: str, body: FollowupBody):
    """PUT /api/v1/leads/{job_id}/followup — Set follow-up interval for a lead.

    Args:
        job_id: Unique job identifier.
        body: Request body with days until next follow-up.

    Returns:
        Updated lead dict.

    Raises:
        HTTPException 404: Lead not found.
    """
    from db.client import update_lead_followup  # lazy: lancedb import takes ~7s
    lead = update_lead_followup(job_id, body.days)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await cm.broadcast({"type": "LEAD_UPDATED", "data": lead})
    return lead


@router.post("/leads/manual", response_model=dict[str, Any])
async def create_manual_lead(body: ManualLeadBody):
    """POST /api/v1/leads/manual — Create a lead from pasted text or URL.

    Args:
        body: Request body with text and/or url fields.

    Returns:
        Saved lead dict.

    Raises:
        HTTPException 400: Neither text nor URL provided.
        HTTPException 422: Non-job lead content rejected.
    """
    if not body.text.strip() and not body.url.strip():
        raise HTTPException(status_code=400, detail="Paste lead text or a URL")
    from db.client import rank_lead_by_feedback, get_lead_by_id, save_lead  # lazy: lancedb import takes ~7s
    from agents.lead_intel import manual_lead_from_text  # lazy: agents module (per-request dep)
    lead = rank_lead_by_feedback(manual_lead_from_text(body.text, body.url, "job"))
    if lead.get("kind") != "job":
        raise HTTPException(status_code=422, detail="Only job leads are accepted right now")
    lead = _annotate_job_lead(lead)
    save_lead(
        lead["job_id"],
        lead["title"],
        lead["company"],
        lead["url"],
        lead["platform"],
        lead["description"],
        kind=lead["kind"],
        budget=lead["budget"],
        signal_score=lead["signal_score"],
        signal_reason=lead["signal_reason"],
        signal_tags=lead["signal_tags"],
        outreach_reply=lead["outreach_reply"],
        outreach_dm=lead["outreach_dm"],
        outreach_email=lead.get("outreach_email", ""),
        proposal_draft=lead.get("proposal_draft", ""),
        fit_bullets=lead.get("fit_bullets", []),
        followup_sequence=lead.get("followup_sequence", []),
        proof_snippet=lead.get("proof_snippet", ""),
        tech_stack=lead.get("tech_stack", []),
        location=lead.get("location", ""),
        urgency=lead.get("urgency", ""),
        base_signal_score=lead.get("base_signal_score"),
        learning_delta=lead.get("learning_delta"),
        learning_reason=lead.get("learning_reason", ""),
        source_meta=lead["source_meta"],
    )
    saved = get_lead_by_id(lead["job_id"]) or lead
    await cm.broadcast({"type": "LEAD_UPDATED", "data": saved})
    return saved


@router.get("/followups/due", response_model=list[dict[str, Any]])
async def due_followups(limit: int = 25):
    """GET /api/v1/followups/due — Retrieve leads with past-due follow-ups.

    Args:
        limit: Maximum number of leads to return.

    Returns:
        List of lead dicts with past-due follow-up dates.
    """
    from db.client import get_due_followups  # lazy: lancedb import takes ~7s
    return get_due_followups(limit)


@router.post("/leads/{job_id}/generate", response_model=LeadGenerateResponse)
async def generate_for_lead(job_id: str):
    """POST /api/v1/leads/{job_id}/generate — Trigger asset generation for a lead.

    Args:
        job_id: Unique job identifier.

    Returns:
        LeadGenerateResponse with status and lead data.
    """
    from services.generator import _generate_one  # lazy: generator pulls in llm deps
    lead = await _generate_one(job_id)
    return {"status": "ready", "job_id": job_id, "lead": lead}


@router.post("/leads/{job_id}/pipeline/run", response_model=PipelineRunResponse)
async def run_pipeline(job_id: str, bt: BackgroundTasks):
    """POST /api/v1/leads/{job_id}/pipeline/run — Start pipeline evaluation in background.

    Kicks off a LangGraph evaluation via BackgroundTasks and broadcasts
    the result on completion.

    Args:
        job_id: Unique job identifier.
        bt: FastAPI BackgroundTasks handle for deferred execution.

    Returns:
        PipelineRunResponse with started status.

    Raises:
        HTTPException 404: Lead not found.
    """
    ctx = new_context(workflow_type="pipeline_run", job_id=job_id, subsystem="pipeline")
    token = set_context(ctx)
    try:
        from db.client import get_lead_by_id, get_profile, get_settings  # lazy: lancedb import takes ~7s
        from graph import PipelineState, eval_graph  # lazy: langgraph import takes ~1.6s
        lead = await asyncio.to_thread(get_lead_by_id, job_id)
        if not lead:
            raise HTTPException(status_code=404, detail="lead not found")
        profile = await asyncio.to_thread(get_profile)
        cfg = await asyncio.to_thread(get_settings)

        async def _run():
            """Execute the pipeline graph for a single lead and broadcast result."""
            state: PipelineState = {
                "job_id": job_id,
                "lead": lead,
                "profile": profile,
                "cfg": cfg,
                "score": 0,
                "reason": "",
                "match_points": [],
                "gaps": [],
                "asset_path": "",
                "cover_letter_path": "",
                "error": None,
            }
            result = await asyncio.to_thread(eval_graph.invoke, state)
            await cm.broadcast({
                "type": "agent",
                "kind": "agent",
                "src": "pipeline",
                "event": "pipeline_done",
                "msg": f"Pipeline done for {job_id}: score={result['score']}, error={result['error']}",
            })

        bt.add_task(_run)
        return {"status": "started", "job_id": job_id}
    finally:
        reset_context(token)
