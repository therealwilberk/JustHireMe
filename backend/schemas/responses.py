"""Response models for all API endpoints.

Each model defines the outbound contract for a specific endpoint.
"""

from pydantic import BaseModel, Field
from typing import Any


class OkResponse(BaseModel):
    """Generic success response with an ``ok`` flag."""

    ok: bool


class StatusResponse(BaseModel):
    """Generic response carrying a status string."""

    status: str


class HealthResponse(BaseModel):
    """Response for the ``/health`` endpoint."""

    status: str
    uptime_seconds: float
    timestamp: str
    log_level: str
    dependencies: dict[str, Any]


class TemplateResponse(BaseModel):
    """Response containing the tailoring template."""

    template: str


class FireResponse(BaseModel):
    """Response for triggering a lead generation action."""

    status: str
    job_id: str


class IdentityResponse(BaseModel):
    """Response containing the user's identity information."""

    full_name: str
    email: str
    phone: str
    linkedin_url: str
    github_url: str
    website_url: str
    city: str
    current_company: str


class SelectorsRefreshResponse(BaseModel):
    """Response after refreshing scraper selectors."""

    version: str
    platforms: list[str]


class FreeSourcesScanResponse(BaseModel):
    """Response for a free-sources scan result."""

    status: str
    leads: int


class LeadGenerateResponse(BaseModel):
    """Response after generating a single lead."""

    status: str
    job_id: str
    lead: dict[str, Any]


class PipelineRunResponse(BaseModel):
    """Response after triggering a pipeline run."""

    status: str
    job_id: str


class IngestLinkedinResponse(BaseModel):
    """Response after importing a LinkedIn profile."""

    status: str
    stats: dict[str, Any]
    location: str
    errors: list[str]


class IngestGithubResponse(BaseModel):
    """Response after importing a GitHub profile."""

    status: str
    github_user: dict[str, Any]
    stats: dict[str, Any]
    errors: list[str]


class IngestProfileResponse(BaseModel):
    """Response after importing a portfolio or personal website."""

    status: str
    stats: dict[str, Any]
    errors: list[str]


class JobTargetsResponse(BaseModel):
    """Response containing the current job targets and blocked markers."""

    targets: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)
