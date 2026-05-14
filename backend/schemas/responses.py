from pydantic import BaseModel, Field
from typing import Any


class OkResponse(BaseModel):
    ok: bool


class StatusResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    timestamp: str
    log_level: str
    dependencies: dict[str, Any]


class TemplateResponse(BaseModel):
    template: str


class FireResponse(BaseModel):
    status: str
    job_id: str


class IdentityResponse(BaseModel):
    full_name: str
    email: str
    phone: str
    linkedin_url: str
    github_url: str
    website_url: str
    city: str
    current_company: str


class SelectorsRefreshResponse(BaseModel):
    version: str
    platforms: list[str]


class FreeSourcesScanResponse(BaseModel):
    status: str
    leads: int


class LeadGenerateResponse(BaseModel):
    status: str
    job_id: str
    lead: dict[str, Any]


class PipelineRunResponse(BaseModel):
    status: str
    job_id: str


class IngestLinkedinResponse(BaseModel):
    status: str
    stats: dict[str, Any]
    location: str
    errors: list[str]


class IngestGithubResponse(BaseModel):
    status: str
    github_user: dict[str, Any]
    stats: dict[str, Any]
    errors: list[str]


class IngestProfileResponse(BaseModel):
    status: str
    stats: dict[str, Any]
    errors: list[str]


class JobTargetsResponse(BaseModel):
    targets: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)
