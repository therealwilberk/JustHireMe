import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agents.github_ingestor import ingest_github
from agents.ingestor import ingest as _ingest
from agents.linkedin_parser import parse_linkedin_export
from agents.portfolio_ingestor import ingest_portfolio_url

from core.config_constants import _log
from core.ws_manager import cm
from db.client import (
    add_achievement,
    add_certification,
    add_education,
    add_experience,
    add_project,
    add_skill,
    refresh_profile_snapshot,
    save_settings,
    update_candidate,
)
from schemas.requests import (
    GithubIngestBody,
    PortfolioIngestBody,
    ProfileCandidate,
    ProfileEntry,
    ProfileImportBody,
    ProfileProject,
    ProfileSkill,
)

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest")
async def ingest(
    raw: str = Form(""),
    file: UploadFile | None = File(None),
):
    pdf_path = None
    if file and file.filename:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        shutil.copyfileobj(file.file, tmp)
        tmp.close()
        pdf_path = tmp.name
    try:
        p = await asyncio.to_thread(_ingest, raw, pdf_path)
        try:
            await asyncio.to_thread(refresh_profile_snapshot)
        except Exception:
            _log.warning("ingestion snapshot refresh failed for lead %s", p.n if hasattr(p, 'n') else 'unknown')
        await cm.broadcast({"type": "agent", "event": "ingested",
                            "msg": f"Profile ingested: {p.n} — {len(p.skills)} skills"})
        return p.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)


@router.post("/ingest/linkedin")
async def ingest_linkedin(file: UploadFile = File(...)):
    if not (file.filename or "").endswith(".zip"):
        raise HTTPException(400, "expected a .zip file from LinkedIn data export")
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(413, "file too large")
    try:
        parsed = await asyncio.to_thread(parse_linkedin_export, raw)
    except Exception as exc:
        _log.error("linkedin parse failed: %s", exc)
        raise HTTPException(422, f"could not parse linkedin export: {exc}")

    errors = []
    try:
        c = parsed["candidate"]
        if c["n"]:
            await asyncio.to_thread(update_candidate, c["n"], c["s"])
    except Exception as e:
        errors.append(f"candidate: {e}")

    for skill in parsed["skills"]:
        try:
            await asyncio.to_thread(add_skill, skill["n"], skill["cat"])
        except Exception:
            _log.warning("skill import failed — %s", skill.get("n", "unknown"))

    for exp in parsed["experience"]:
        try:
            await asyncio.to_thread(add_experience, exp["role"], exp["co"], exp["period"], exp["d"])
        except Exception as e:
            errors.append(f"exp {exp.get('role')}: {e}")

    for edu in parsed["education"]:
        try:
            await asyncio.to_thread(add_education, edu["title"])
        except Exception as e:
            errors.append(f"edu: {e}")

    for proj in parsed["projects"]:
        try:
            await asyncio.to_thread(add_project, proj["title"], proj["stack"], proj["repo"], proj["impact"])
        except Exception as e:
            errors.append(f"proj {proj.get('title')}: {e}")

    for cert in parsed["certifications"]:
        try:
            await asyncio.to_thread(add_certification, cert["title"])
        except Exception as e:
            errors.append(f"cert: {e}")

    return {
        "status":   "ok" if not errors else "partial",
        "stats":    parsed["stats"],
        "location": parsed["location"],
        "errors":   errors,
    }


@router.post("/ingest/github")
async def ingest_github_endpoint(body: GithubIngestBody):
    result = await ingest_github(
        body.username,
        token=body.token or None,
        max_repos=body.max_repos,
    )
    if "error" in result:
        raise HTTPException(404, result["error"])

    errors = list(result.get("errors", []))

    for skill in result["skills"]:
        try:
            await asyncio.to_thread(add_skill, skill["n"], skill["cat"])
        except Exception:
            _log.warning("GitHub skill import failed — %s", body.username)

    for proj in result["projects"]:
        try:
            await asyncio.to_thread(add_project, proj["title"], proj["stack"], proj["repo"], proj["impact"])
        except Exception as e:
            errors.append(f"proj {proj.get('title')}: {e}")

    gu = result.get("github_user", {})
    settings_update: dict = {}
    if gu.get("login"):
        settings_update["github_username"] = gu["login"]
    if gu.get("blog"):
        settings_update["website_url"] = gu["blog"]
    if settings_update:
        await asyncio.to_thread(save_settings, settings_update)

    return {
        "status":      "ok" if not errors else "partial",
        "github_user": result["github_user"],
        "stats":       result["stats"],
        "errors":      errors,
    }


@router.post("/ingest/profile")
async def import_profile_json(body: ProfileImportBody):
    errors = []

    stats = {k: 0 for k in [
        "skills", "experience", "projects", "education",
        "certifications", "achievements",
    ]}

    c = body.candidate
    if c.name or c.summary:
        try:
            await asyncio.to_thread(update_candidate, c.name, c.summary)
        except Exception as e:
            errors.append(f"candidate: {e}")

    id_ = body.identity
    identity_map = {
        "email": id_.email,
        "phone": id_.phone,
        "linkedin_url": id_.linkedin_url,
        "github_url": id_.github_url,
        "website_url": id_.website_url,
        "city": id_.city,
    }
    for key, val in identity_map.items():
        if val:
            try:
                await asyncio.to_thread(save_settings, {key: val})
            except Exception as e:
                errors.append(f"identity.{key}: {e}")

    for s in body.skills:
        try:
            await asyncio.to_thread(add_skill, s.name, s.category)
            stats["skills"] += 1
        except Exception:
            _log.warning("skill add from identity form failed")

    for ex in body.experience:
        try:
            await asyncio.to_thread(
                add_experience, ex.role, ex.company, ex.period, ex.description,
            )
            stats["experience"] += 1
        except Exception as e:
            errors.append(f"exp {ex.role}: {e}")

    for p in body.projects:
        try:
            await asyncio.to_thread(add_project, p.title, p.stack, p.repo, p.impact)
            stats["projects"] += 1
        except Exception as e:
            errors.append(f"proj {p.title}: {e}")

    for e in body.education:
        try:
            await asyncio.to_thread(add_education, e.title)
            stats["education"] += 1
        except Exception as exc:
            errors.append(f"edu: {exc}")

    for cert in body.certifications:
        try:
            await asyncio.to_thread(add_certification, cert.title)
            stats["certifications"] += 1
        except Exception as exc:
            errors.append(f"cert: {exc}")

    for ach in body.achievements:
        try:
            await asyncio.to_thread(add_achievement, ach.title)
            stats["achievements"] += 1
        except Exception as exc:
            errors.append(f"achievement: {exc}")

    return {
        "status": "ok" if not errors else "partial",
        "stats": stats,
        "errors": errors,
    }


@router.get("/ingest/profile/template")
async def get_profile_template():
    template_path = Path(__file__).resolve().parent.parent / "data" / "profile_schema_example.json"
    with open(template_path, encoding="utf-8") as f:
        return json.load(f)


@router.post("/ingest/portfolio")
async def ingest_portfolio_endpoint(body: PortfolioIngestBody):
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must start with http:// or https://")
    result = await ingest_portfolio_url(body.url)
    if result.get("error") and not result.get("screenshot_b64"):
        raise HTTPException(422, result["error"])

    if body.auto_import and result.get("candidate") is not None:
        import_body = ProfileImportBody(
            candidate=ProfileCandidate(**(result["candidate"] or {})),
            skills=[
                ProfileSkill(name=s["name"], category=s.get("category", "general"))
                for s in result.get("skills", [])
            ],
            projects=[ProfileProject(**p) for p in result.get("projects", [])],
            achievements=[
                ProfileEntry(title=a["title"])
                for a in result.get("achievements", [])
            ],
        )
        import_result = await import_profile_json(import_body)
        result["import_stats"] = import_result["stats"]
        result["import_errors"] = import_result["errors"]

    return result
