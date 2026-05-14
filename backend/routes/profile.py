from fastapi import APIRouter, HTTPException
from schemas.requests import CandidateBody, SkillBody, ExperienceBody, ProjectBody
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


@router.get("/profile")
async def get_profile_endpoint():
    return _gp()


@router.put("/profile/candidate")
async def update_candidate_endpoint(body: CandidateBody):
    if not body.n.strip() and not body.s.strip():
        raise HTTPException(status_code=422, detail="Name or summary is required")
    return update_candidate(body.n, body.s)


@router.post("/profile/skill")
async def add_skill_endpoint(body: SkillBody):
    if not body.n.strip():
        raise HTTPException(status_code=422, detail="Skill name is required")
    return add_skill(body.n, body.cat)


@router.put("/profile/skill/{sid}")
async def update_skill_endpoint(sid: str, body: SkillBody):
    if not body.n.strip():
        raise HTTPException(status_code=422, detail="Skill name is required")
    return update_skill(sid, body.n, body.cat)


@router.delete("/profile/skill/{sid}")
async def delete_skill_endpoint(sid: str):
    delete_skill(sid)
    return {"ok": True}


@router.post("/profile/experience")
async def add_experience_endpoint(body: ExperienceBody):
    if not body.role.strip() and not body.co.strip():
        raise HTTPException(status_code=422, detail="Role or company is required")
    return add_experience(body.role, body.co, body.period, body.d)


@router.put("/profile/experience/{eid}")
async def update_experience_endpoint(eid: str, body: ExperienceBody):
    if not body.role.strip() and not body.co.strip():
        raise HTTPException(status_code=422, detail="Role or company is required")
    return update_experience(eid, body.role, body.co, body.period, body.d)


@router.delete("/profile/experience/{eid}")
async def delete_experience_endpoint(eid: str):
    delete_experience(eid)
    return {"ok": True}


@router.post("/profile/project")
async def add_project_endpoint(body: ProjectBody):
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Project title is required")
    return add_project(body.title, body.stack, body.repo, body.impact)


@router.put("/profile/project/{pid}")
async def update_project_endpoint(pid: str, body: ProjectBody):
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Project title is required")
    return update_project(pid, body.title, body.stack, body.repo, body.impact)


@router.delete("/profile/project/{pid}")
async def delete_project_endpoint(pid: str):
    delete_project(pid)
    return {"ok": True}
