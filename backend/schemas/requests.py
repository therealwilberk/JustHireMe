from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


LeadStatus = Literal[
    "discovered", "evaluating", "tailoring", "approved", "applied",
    "interviewing", "rejected", "accepted", "discarded",
    "matched", "bidding", "proposal_sent", "awarded", "completed",
]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StatusBody(StrictBody):
    status: LeadStatus


class FeedbackBody(StrictBody):
    feedback: Literal[
        "good", "trash", "too_generic", "not_ai",
        "already_contacted", "relevant", "not_relevant", "duplicate",
        "low_quality", "incorrect_category",
    ]
    note: str = Field(default="", max_length=1000)


class FollowupBody(StrictBody):
    days: int = Field(default=5, ge=1, le=60)


class ManualLeadBody(StrictBody):
    text: str = Field(default="", max_length=20000)
    url: str = Field(default="", max_length=2000)
    kind: Literal["job"] = "job"


class HelpMessage(StrictBody):
    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=4000)


class HelpChatBody(StrictBody):
    question: str = Field(max_length=2000)
    history: list[HelpMessage] = Field(default_factory=list, max_length=12)


class TemplateBody(StrictBody):
    template: str = Field(default="", max_length=20000)


class CandidateBody(StrictBody):
    n: str = Field(default="", max_length=160)
    s: str = Field(default="", max_length=4000)


class SkillBody(StrictBody):
    id: str | None = Field(default=None, max_length=160)
    n: str = Field(default="", max_length=160)
    cat: str = Field(default="general", max_length=80)


class ExperienceBody(StrictBody):
    id: str | None = Field(default=None, max_length=160)
    role: str = Field(default="", max_length=180)
    co: str = Field(default="", max_length=180)
    period: str = Field(default="", max_length=120)
    d: str = Field(default="", max_length=8000)


class ProjectBody(StrictBody):
    id: str | None = Field(default=None, max_length=160)
    title: str = Field(default="", max_length=220)
    stack: str = Field(default="", max_length=2000)
    repo: str = Field(default="", max_length=1000)
    impact: str = Field(default="", max_length=8000)


class SettingsBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _validate_extra_settings(self):
        for key, value in (self.model_extra or {}).items():
            if len(key) > 120 or any(not (ch.isalnum() or ch in "_.-") for ch in key):
                raise ValueError(f"Invalid settings key: {key}")
            if value is not None and not isinstance(value, (str, bool, int, float)):
                raise ValueError(f"Invalid value for settings key: {key}")
        return self


class GithubIngestBody(StrictBody):
    username:  str = Field(min_length=1, max_length=100)
    token:     str = Field(default="", max_length=200)
    max_repos: int = Field(default=12, ge=1, le=30)


class PortfolioIngestBody(StrictBody):
    url: str = Field(max_length=2000)
    auto_import: bool = Field(
        default=False,
        description="if true, immediately write extracted data to the graph",
    )


class ProfileSkill(BaseModel):
    name: str = Field(max_length=160)
    category: str = Field(default="general", max_length=80)


class ProfileExperience(BaseModel):
    role: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    period: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=5000)


class ProfileProject(BaseModel):
    title: str = Field(default="", max_length=200)
    stack: str = Field(default="", max_length=500)
    repo: str = Field(default="", max_length=500)
    impact: str = Field(default="", max_length=1000)


class ProfileEntry(BaseModel):
    title: str = Field(max_length=500)


class ProfileIdentity(BaseModel):
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    linkedin_url: str = Field(default="", max_length=500)
    github_url: str = Field(default="", max_length=500)
    website_url: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=200)


class ProfileCandidate(BaseModel):
    name: str = Field(default="", max_length=160)
    summary: str = Field(default="", max_length=4000)


class ProfileImportBody(BaseModel):
    candidate: ProfileCandidate = Field(default_factory=ProfileCandidate)
    identity: ProfileIdentity = Field(default_factory=ProfileIdentity)
    skills: list[ProfileSkill] = Field(default_factory=list)
    experience: list[ProfileExperience] = Field(default_factory=list)
    projects: list[ProfileProject] = Field(default_factory=list)
    education: list[ProfileEntry] = Field(default_factory=list)
    certifications: list[ProfileEntry] = Field(default_factory=list)
    achievements: list[ProfileEntry] = Field(default_factory=list)


class FormReadBody(StrictBody):
    url: str = Field(default="", max_length=2000)
