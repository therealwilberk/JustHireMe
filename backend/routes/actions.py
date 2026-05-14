"""Fire actions, PDF downloads, applicant form reading, and identity/selectors."""

import asyncio
import os

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from schemas.requests import FormReadBody
from schemas.responses import FireResponse, IdentityResponse, SelectorsRefreshResponse

router = APIRouter(prefix="/api/v1", tags=["actions"])


@router.get("/leads/{job_id}/pdf")
async def get_lead_pdf(job_id: str, kind: str = "resume", version: int | None = None):
    """GET /api/v1/leads/{job_id}/pdf — Download resume or cover letter PDF.

    Supports versioned asset retrieval via the ``version`` parameter.

    Args:
        job_id: Unique job identifier.
        kind: Asset type — ``resume`` or ``cover_letter``.
        version: Optional specific version number.

    Returns:
        FileResponse with the PDF file.

    Raises:
        HTTPException 404: Lead not found or asset not generated.
    """
    from db.client import get_lead_by_id, data_base  # lazy: lancedb import takes ~7s

    lead = get_lead_by_id(job_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    is_cover = kind in {"cover", "cover_letter", "cover-letter"}
    if version is not None:
        paths = [
            lead.get("resume_asset") or lead.get("asset") or "",
            lead.get("cover_letter_asset") or "",
        ]
        base_dir = next((os.path.dirname(path) for path in paths if path), None)
        if not base_dir:
            base_dir = os.path.join(data_base(), "assets")
        filename = f"{job_id}_cl_v{version}.pdf" if is_cover else f"{job_id}_v{version}.pdf"
        path = os.path.join(base_dir, filename)
        missing = "Cover letter not generated yet" if is_cover else "Resume not generated yet"
    elif is_cover:
        path = lead.get("cover_letter_asset") or ""
        filename = f"{job_id}_cover_letter.pdf"
        missing = "Cover letter not generated yet"
    else:
        path = lead.get("resume_asset") or lead.get("asset") or ""
        filename = f"{job_id}_resume.pdf"
        missing = "Resume not generated yet"
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=missing)
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/fire/{job_id}", response_model=FireResponse)
async def fire(job_id: str, bt: BackgroundTasks):
    """POST /api/v1/fire/{job_id} — Submit an application for a lead in the background.

    Checks for blockers via ``_fire_blocker``, then schedules ``_actuate``.

    Args:
        job_id: Unique job identifier.
        bt: FastAPI BackgroundTasks handle for deferred execution.

    Returns:
        FireResponse with firing status.

    Raises:
        HTTPException 4xx: Blocker prevents firing (see detail).
    """
    from db.client import get_lead_for_fire  # lazy: lancedb import takes ~7s
    from services.generator import _fire_blocker, _actuate  # lazy: generator pulls in llm deps
    lead, asset = await asyncio.to_thread(get_lead_for_fire, job_id)
    status, detail = _fire_blocker(lead, asset)
    if detail:
        raise HTTPException(status_code=status, detail=detail)
    bt.add_task(_actuate, job_id)
    return {"status": "firing", "job_id": job_id}


@router.post("/leads/{job_id}/form/read", response_model=dict[str, Any])
async def read_lead_form(job_id: str, body: FormReadBody):
    """POST /api/v1/leads/{job_id}/form/read — Read and parse an external application form.

    Uses the actuator agent to fill form fields with profile identity data.

    Args:
        job_id: Unique job identifier.
        body: Request body with optional URL override.

    Returns:
        Parsed form data from the external page.

    Raises:
        HTTPException 404: Lead not found.
        HTTPException 400: No URL available for this lead.
    """
    from agents.actuator import read_form  # lazy: agents module (per-request dep)
    from db.client import get_lead_by_id, get_profile, get_settings  # lazy: lancedb import takes ~7s

    lead = get_lead_by_id(job_id)
    if not lead:
        raise HTTPException(404, "lead not found")

    url = (body.url or lead.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "no url available for this lead")

    profile = get_profile()
    candidate = profile.get("candidate") or {}

    cfg = get_settings()
    identity = {
        "name":            cfg.get("full_name", "") or candidate.get("n", ""),
        "email":           cfg.get("email", ""),
        "phone":           cfg.get("phone", ""),
        "linkedin_url":    cfg.get("linkedin_url", ""),
        "github":          cfg.get("github_url", ""),
        "website":         cfg.get("website_url", ""),
        "city":            cfg.get("city", ""),
        "current_company": cfg.get("current_company", ""),
    }

    cover_letter = lead.get("cover_letter_asset", "")
    if cover_letter and os.path.isfile(cover_letter):
        try:
            md_path = cover_letter.replace(".pdf", ".md")
            if os.path.isfile(md_path):
                with open(md_path, encoding="utf-8") as f:
                    cover_letter = f.read()
            else:
                cover_letter = ""
        except Exception:
            cover_letter = ""

    result = await read_form(url, identity, cover_letter=cover_letter)
    return result


@router.get("/identity", response_model=IdentityResponse)
async def get_identity():
    """GET /api/v1/identity — Retrieve the user's identity/profile settings.

    Returns:
        IdentityResponse with name, email, phone, URLs, and location.
    """
    from db.client import get_settings  # lazy: lancedb import takes ~7s
    cfg = get_settings()
    return {
        "full_name":       cfg.get("full_name", ""),
        "email":           cfg.get("email", ""),
        "phone":           cfg.get("phone", ""),
        "linkedin_url":    cfg.get("linkedin_url", ""),
        "github_url":      cfg.get("github_url", ""),
        "website_url":     cfg.get("website_url", ""),
        "city":            cfg.get("city", ""),
        "current_company": cfg.get("current_company", ""),
    }


@router.post("/selectors/refresh", response_model=SelectorsRefreshResponse)
async def refresh_selectors():
    """POST /api/v1/selectors/refresh — Force-refresh cached CSS selectors.

    Resets the fetched-at timestamp and re-downloads selectors.

    Returns:
        SelectorsRefreshResponse with version and platform list.
    """
    from agents.selectors import get_selectors  # lazy: agents module (per-request dep)

    from db.client import save_settings  # lazy: lancedb import takes ~7s
    save_settings({"selectors_fetched_at": "0"})
    data = await asyncio.to_thread(get_selectors)
    return {"version": data.get("version"), "platforms": list(data.get("platforms", {}).keys())}


@router.post("/leads/{job_id}/apply/preview", response_model=dict[str, Any])
async def preview_apply(job_id: str):
    """POST /api/v1/leads/{job_id}/apply/preview — Dry-run application submission.

    Runs the actuator in preview mode without actually submitting.

    Args:
        job_id: Unique job identifier.

    Returns:
        Preview output from the actuator agent.

    Raises:
        HTTPException 4xx: Blocker prevents preview (see detail).
    """
    from agents.actuator import run as _act  # lazy: agents module (per-request dep)
    from db.client import get_lead_for_fire  # lazy: lancedb import takes ~7s
    from services.generator import _fire_blocker  # lazy: generator pulls in llm deps

    lead, asset = await asyncio.to_thread(get_lead_for_fire, job_id)
    status_code, detail = _fire_blocker(lead, asset)
    if detail:
        raise HTTPException(status_code=status_code, detail=detail)
    return await asyncio.to_thread(_act, lead, asset, True)
