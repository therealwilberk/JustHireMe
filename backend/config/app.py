"""Application-level configuration domain.

These models map to settings used across ``backend/main.py``,
``backend/agents/``, and ``backend/db/`` modules. Each class
carries source-location comments referencing the original
hardcoded constant it replaced.
"""

from pydantic import BaseModel, Field
from typing import Literal


class GhostModeConfig(BaseModel):
    """Settings for the background ghost-mode scheduler."""

    # from backend/main.py:620
    interval_hours: int = Field(default=6, ge=1, le=168)
    scheduler_job_id: str = "ghost"


class WebSocketConfig(BaseModel):
    """Settings for WebSocket heartbeat behaviour."""

    # from backend/main.py:2017
    heartbeat_timeout: float = Field(default=2.0, ge=0.5, le=60.0)


class PortConfig(BaseModel):
    """Settings for the FastAPI dev server port and host."""

    # from backend/main.py:28-31, 2036
    dev_frontend_port: int = Field(default=1420, ge=1024, le=65535)
    bind_host: str = "127.0.0.1"
    uvicorn_log_level: str = "warning"


class TokenConfig(BaseModel):
    """Settings for the API bearer token generation."""

    # from backend/main.py:36
    token_hex_bytes: int = Field(default=32, ge=16, le=128)


class CORSConfig(BaseModel):
    """Settings for CORS origin allow-listing."""

    # from backend/main.py:37
    local_origin_regex: str = r"^(tauri://localhost|https?://(localhost|127\.0\.0\.1|tauri\.localhost|\[::1\])(?::\d+)?)$"


class LeadFreshnessConfig(BaseModel):
    """Settings for how long discovered leads stay fresh."""

    # from backend/agents/scout.py:20 (used in main.py's ghost mode too)
    max_age_days: int = 7


class AutoApproveConfig(BaseModel):
    """Settings for the auto-approval scoring threshold."""

    # from backend/main.py:542
    threshold: int = 85


class JobTargetDefaults(BaseModel):
    """Default job-board target URLs and blocked-marker keywords."""

    # from backend/main.py:176-196
    global_targets: list[str] = [
        "hn-hiring",
        "https://remoteok.com/api",
        "https://remotive.com/api/remote-jobs",
        "https://jobicy.com/api/v2/remote-jobs?count=50",
        "https://jobicy.com/feed/newjobs",
        "https://weworkremotely.com/remote-jobs.rss",
        "site:boards.greenhouse.io",
        "site:jobs.lever.co",
        "site:jobs.ashbyhq.com",
        "site:apply.workable.com",
        "site:wellfound.com/jobs",
        "site:linkedin.com/jobs",
        "site:indeed.com/jobs",
        "site:glassdoor.com/Job",
        "site:jobs.smartrecruiters.com",
        "site:workdayjobs.com",
        "site:naukri.com",
        "site:instahyre.com",
        "site:cutshort.io/jobs",
    ]

    blocked_markers: tuple[str, ...] = (
        "freelance", "upwork", "freelancer.com", "fiverr", "contra.com",
        "peopleperhour", "guru.com", "truelancer", "codementor", "toptal",
    )


class MarketFocusConfig(BaseModel):
    """Settings for the market focus (regional targeting)."""

    valid_focus_values: set[str] = {"global"}
    default_focus: str = "global"


class DiscoveryConfig(BaseModel):
    """Settings for lead-discovery term limits and hints."""

    # from backend/main.py:306-325
    terms_limit: int = 4
    terms_summary_words: int = 5
    free_source_terms_limit: int = 3
    x_queries_terms_limit: int = 4
    hint_limit: int = 4  # backend/main.py:306 parameter default


class IdentityKeys(BaseModel):
    """Settings key names for identity/profile fields."""

    # from backend/main.py:1843-1851
    settings_keys: list[str] = [
        "full_name", "email", "phone", "linkedin_url",
        "github_url", "website_url", "city", "current_company",
    ]


class SensitiveKeys(BaseModel):
    """Key patterns for sensitive settings that should be masked."""

    # from backend/main.py:1354
    fixed: set[str] = {"anthropic_key", "linkedin_cookie", "x_bearer_token", "custom_connector_headers"}
    suffixes: tuple[str, ...] = ("_api_key", "_key", "_token")


class EvaluatorProfileKeys(BaseModel):
    """Ordered profile keys used by the evaluator agent."""

    # from backend/agents/evaluator.py:157-161
    ordered_keys: list[str] = [
        "n", "s", "skills", "exp", "projects",
        "certifications", "certs", "education", "achievements", "awards",
        "publications", "links", "github", "website", "portfolio",
    ]


class ReEvaluationConfig(BaseModel):
    """Status values that lock a lead from re-evaluation."""

    # from backend/main.py:458
    status_locks: set[str] = {"approved", "applied", "interviewing", "rejected", "accepted", "discarded"}


class ScanConfig(BaseModel):
    """Limits and defaults for scanning runs."""

    # from backend/main.py:1282-1349
    max_leads_per_scan: int = 1000  # backend/main.py:1149 default limit for cleanup


class UploadLimits(BaseModel):
    """Limits for file uploads."""

    # from backend/routes/ingest.py:95
    max_linkedin_export_size: int = Field(default=50 * 1024 * 1024, ge=1024, le=500 * 1024 * 1024)  # 50 MB


class ScanBroadcastLimits(BaseModel):
    """Limits for broadcast batching during scan operations."""

    # from backend/routes/scan.py:81
    cleanup_broadcast_cap: int = Field(default=100, ge=1, le=1000)


class AppDataEnvConfig(BaseModel):
    """Environment variables controlling the app data directory."""

    # from backend/db/client.py:32-38
    app_data_dir: str = "JHM_APP_DATA_DIR"
    localappdata: str = "LOCALAPPDATA"
    xdg_data_home: str = "XDG_DATA_HOME"


class BrowserEnvConfig(BaseModel):
    """Environment variables for browser runtime configuration."""

    # from backend/agents/browser_runtime.py:20,24,28,46,53,60
    runtime_dir: str = "JHM_BROWSER_RUNTIME_DIR"
    playwright_browsers_path: str = "PLAYWRIGHT_BROWSERS_PATH"
    browser: str = "BROWSER"
    playwright_chromium_executable: str = "PLAYWRIGHT_CHROMIUM_EXECUTABLE"
    runtime_url: str = "JHM_BROWSER_RUNTIME_URL"


class AutoApplyEnvConfig(BaseModel):
    """Environment variable for enabling auto-apply mode."""

    # from backend/agents/actuator.py:12
    env_var: str = "JHM_AUTO_APPLY"


class BearerTokenEnvConfig(BaseModel):
    """Environment variable names for X/Twitter bearer tokens."""

    # from backend/main.py:363, x_scout.py:400
    x_bearer_token: str = "X_BEARER_TOKEN"
    twitter_bearer_token: str = "TWITTER_BEARER_TOKEN"


class AppSettingsKeyNames(BaseModel):
    """Settings key names for app-level secrets."""

    # from backend/agents/x_scout.py:400-401, backend/main.py:1372, backend/agents/free_scout.py:89-96
    x_bearer_token: str = "x_bearer_token"
    linkedin_cookie: str = "linkedin_cookie"
    custom_connector_headers: str = "custom_connector_headers"


class AppConfig(BaseModel):
    """Aggregate config root for the application domain."""

    ghost_mode: GhostModeConfig = GhostModeConfig()
    websocket: WebSocketConfig = WebSocketConfig()
    port: PortConfig = PortConfig()
    cors: CORSConfig = CORSConfig()
    token: TokenConfig = TokenConfig()
    lead_freshness: LeadFreshnessConfig = LeadFreshnessConfig()
    auto_approve: AutoApproveConfig = AutoApproveConfig()
    job_targets: JobTargetDefaults = JobTargetDefaults()
    market_focus: MarketFocusConfig = MarketFocusConfig()
    discovery: DiscoveryConfig = DiscoveryConfig()
    identity: IdentityKeys = IdentityKeys()
    sensitive_keys: SensitiveKeys = SensitiveKeys()
    evaluator_profile_keys: EvaluatorProfileKeys = EvaluatorProfileKeys()
    reevaluation: ReEvaluationConfig = ReEvaluationConfig()
    scan: ScanConfig = ScanConfig()
    upload_limits: UploadLimits = UploadLimits()
    scan_broadcast: ScanBroadcastLimits = ScanBroadcastLimits()
    app_data: AppDataEnvConfig = AppDataEnvConfig()
    browser: BrowserEnvConfig = BrowserEnvConfig()
    auto_apply: AutoApplyEnvConfig = AutoApplyEnvConfig()
    bearer_tokens: BearerTokenEnvConfig = BearerTokenEnvConfig()
    settings_key_names: AppSettingsKeyNames = AppSettingsKeyNames()


config = AppConfig()
