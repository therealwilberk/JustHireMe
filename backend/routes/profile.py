"""Profile CRUD for candidate info, skills, experience, and projects."""

from typing import Any

from fastapi import APIRouter, HTTPException
from schemas.requests import CandidateBody, SkillBody, ExperienceBody, ProjectBody
from schemas.responses import OkResponse
from db.client import (
    get_profile as _gp,
    update_candidate,
    add_skill,
    update_skill,
    delete_skill,
    add_experience,
    update_experience,
    delete_experience,
    add_project,
    update_project,
    delete_project,
)

router = APIRouter(prefix="/api/v1", tags=["profile"])


@router.get("/profile", response_model=dict[str, Any])
async def get_profile_endpoint():
    """GET /api/v1/profile — Retrieve the full user profile.

    Returns:
        Complete profile dict with candidate, skills, experience, projects.
    """
    return _gp()


@router.put("/profile/candidate", response_model=dict[str, Any])
async def update_candidate_endpoint(body: CandidateBody):
    """PUT /api/v1/profile/candidate — Update candidate name and summary.

    Args:
        body: Request body with name and summary.

    Returns:
        Updated candidate dict.

    Raises:
        HTTPException 422: Neither name nor summary provided.
    """
    if not body.n.strip() and not body.s.strip():
        raise HTTPException(status_code=422, detail="Name or summary is required")
    return update_candidate(body.n, body.s)


@router.post("/profile/skill", response_model=dict[str, Any])
async def add_skill_endpoint(body: SkillBody):
    """POST /api/v1/profile/skill — Add a new skill.

    Args:
        body: Request body with skill name and category.

    Returns:
        Created skill dict.

    Raises:
        HTTPException 422: Skill name is empty.
    """
    if not body.n.strip():
        raise HTTPException(status_code=422, detail="Skill name is required")
    return add_skill(body.n, body.cat)


@router.put("/profile/skill/{sid}", response_model=dict[str, Any])
async def update_skill_endpoint(sid: str, body: SkillBody):
    """PUT /api/v1/profile/skill/{sid} — Update an existing skill.

    Args:
        sid: Skill unique identifier.
        body: Request body with updated name and category.

    Returns:
        Updated skill dict.

    Raises:
        HTTPException 422: Skill name is empty.
    """
    if not body.n.strip():
        raise HTTPException(status_code=422, detail="Skill name is required")
    return update_skill(sid, body.n, body.cat)


@router.delete("/profile/skill/{sid}", response_model=OkResponse)
async def delete_skill_endpoint(sid: str):
    """DELETE /api/v1/profile/skill/{sid} — Delete a skill by ID.

    Args:
        sid: Skill unique identifier.

    Returns:
        OkResponse with ok: true.
    """
    delete_skill(sid)
    return {"ok": True}


@router.post("/profile/experience", response_model=dict[str, Any])
async def add_experience_endpoint(body: ExperienceBody):
    """POST /api/v1/profile/experience — Add a new experience entry.

    Args:
        body: Request body with role, company, period, description.

    Returns:
        Created experience dict.

    Raises:
        HTTPException 422: Neither role nor company provided.
    """
    if not body.role.strip() and not body.co.strip():
        raise HTTPException(status_code=422, detail="Role or company is required")
    return add_experience(body.role, body.co, body.period, body.d)


@router.put("/profile/experience/{eid}", response_model=dict[str, Any])
async def update_experience_endpoint(eid: str, body: ExperienceBody):
    """PUT /api/v1/profile/experience/{eid} — Update an existing experience entry.

    Args:
        eid: Experience unique identifier.
        body: Request body with updated role, company, period, description.

    Returns:
        Updated experience dict.

    Raises:
        HTTPException 422: Neither role nor company provided.
    """
    if not body.role.strip() and not body.co.strip():
        raise HTTPException(status_code=422, detail="Role or company is required")
    return update_experience(eid, body.role, body.co, body.period, body.d)


@router.delete("/profile/experience/{eid}", response_model=OkResponse)
async def delete_experience_endpoint(eid: str):
    """DELETE /api/v1/profile/experience/{eid} — Delete an experience entry by ID.

    Args:
        eid: Experience unique identifier.

    Returns:
        OkResponse with ok: true.
    """
    delete_experience(eid)
    return {"ok": True}


@router.post("/profile/project", response_model=dict[str, Any])
async def add_project_endpoint(body: ProjectBody):
    """POST /api/v1/profile/project — Add a new project entry.

    Args:
        body: Request body with title, stack, repo, impact.

    Returns:
        Created project dict.

    Raises:
        HTTPException 422: Project title is empty.
    """
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Project title is required")
    return add_project(body.title, body.stack, body.repo, body.impact)


@router.put("/profile/project/{pid}", response_model=dict[str, Any])
async def update_project_endpoint(pid: str, body: ProjectBody):
    """PUT /api/v1/profile/project/{pid} — Update an existing project entry.

    Args:
        pid: Project unique identifier.
        body: Request body with updated title, stack, repo, impact.

    Returns:
        Updated project dict.

    Raises:
        HTTPException 422: Project title is empty.
    """
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Project title is required")
    return update_project(pid, body.title, body.stack, body.repo, body.impact)


@router.delete("/profile/project/{pid}", response_model=OkResponse)
async def delete_project_endpoint(pid: str):
    """DELETE /api/v1/profile/project/{pid} — Delete a project entry by ID.

    Args:
        pid: Project unique identifier.

    Returns:
        OkResponse with ok: true.
    """
    delete_project(pid)
    return {"ok": True}
