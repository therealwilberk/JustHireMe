import asyncio
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from schemas.requests import FormReadBody

router = APIRouter(prefix="/api/v1", tags=["actions"])


@router.get("/leads/{job_id}/pdf")
async def get_lead_pdf(job_id: str, kind: str = "resume", version: int | None = None):
    from fastapi import HTTPException
    from db.client import get_lead_by_id, data_base

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


@router.post("/fire/{job_id}")
async def fire(job_id: str, bt: BackgroundTasks):
    from db.client import get_lead_for_fire
    from services.generator import _fire_blocker, _actuate
    lead, asset = await asyncio.to_thread(get_lead_for_fire, job_id)
    status, detail = _fire_blocker(lead, asset)
    if detail:
        raise HTTPException(status_code=status, detail=detail)
    bt.add_task(_actuate, job_id)
    return {"status": "firing", "job_id": job_id}


@router.post("/leads/{job_id}/form/read")
async def read_lead_form(job_id: str, body: FormReadBody):
    from agents.actuator import read_form
    from db.client import get_lead_by_id, get_profile, get_settings

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


@router.get("/identity")
async def get_identity():
    from db.client import get_settings
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


@router.post("/selectors/refresh")
async def refresh_selectors():
    from agents.selectors import get_selectors

    from db.client import save_settings
    save_settings({"selectors_fetched_at": "0"})
    data = await asyncio.to_thread(get_selectors)
    return {"version": data.get("version"), "platforms": list(data.get("platforms", {}).keys())}


@router.post("/leads/{job_id}/apply/preview")
async def preview_apply(job_id: str):
    from agents.actuator import run as _act
    from db.client import get_lead_for_fire
    from services.generator import _fire_blocker

    lead, asset = await asyncio.to_thread(get_lead_for_fire, job_id)
    status_code, detail = _fire_blocker(lead, asset)
    if detail:
        raise HTTPException(status_code=status_code, detail=detail)
    return await asyncio.to_thread(_act, lead, asset, True)
