from pydantic import BaseModel, Field
from typing import Literal


class GhostModeConfig(BaseModel):
    # from backend/main.py:620
    interval_hours: int = Field(default=6, ge=1, le=168)
    scheduler_job_id: str = "ghost"


class WebSocketConfig(BaseModel):
    # from backend/main.py:2017
    heartbeat_timeout: float = Field(default=2.0, ge=0.5, le=60.0)


class PortConfig(BaseModel):
    # from backend/main.py:28-31, 2036
    dev_frontend_port: int = Field(default=1420, ge=1024, le=65535)
    bind_host: str = "127.0.0.1"
    uvicorn_log_level: str = "warning"


class TokenConfig(BaseModel):
    # from backend/main.py:36
    token_hex_bytes: int = Field(default=32, ge=16, le=128)


class CORSConfig(BaseModel):
    # from backend/main.py:37
    local_origin_regex: str = r"^(tauri://localhost|https?://(localhost|127\.0\.0\.1|tauri\.localhost|\[::1\])(?::\d+)?)$"


class LeadFreshnessConfig(BaseModel):
    # from backend/agents/scout.py:20 (used in main.py's ghost mode too)
    max_age_days: int = 7


class AutoApproveConfig(BaseModel):
    # from backend/main.py:542
    threshold: int = 85


class JobTargetDefaults(BaseModel):
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

    india_targets: list[str] = [
        "site:wellfound.com/jobs India",
        "site:cutshort.io/jobs India startup",
        "site:instahyre.com jobs India",
        "site:naukri.com jobs India",
        "site:foundit.in jobs India",
        "site:internshala.com/jobs India",
        "site:linkedin.com/jobs India",
        "site:indeed.com/jobs India",
        "site:glassdoor.co.in Job India",
        "site:boards.greenhouse.io India",
        "site:jobs.lever.co India",
        "site:jobs.ashbyhq.com India",
        "site:apply.workable.com India",
    ]

    blocked_markers: tuple[str, ...] = (
        "freelance", "upwork", "freelancer.com", "fiverr", "contra.com",
        "peopleperhour", "guru.com", "truelancer", "codementor", "toptal",
    )

    india_markers: tuple[str, ...] = (
        "india", "indian", "bangalore", "bengaluru", "mumbai", "delhi",
        "gurgaon", "gurugram", "hyderabad", "pune", "chennai", "noida",
        "cutshort", "instahyre", "naukri", "foundit", "internshala",
        "glassdoor.co.in",
    )


class MarketFocusConfig(BaseModel):
    # from backend/main.py:244-246
    valid_focus_values: set[str] = {"global", "india", "in", "indian", "indian_startups"}
    default_focus: str = "global"


class DiscoveryConfig(BaseModel):
    # from backend/main.py:306-325
    terms_limit: int = 4
    terms_summary_words: int = 5
    free_source_terms_limit: int = 3
    x_queries_terms_limit: int = 4
    hint_limit: int = 4  # backend/main.py:306 parameter default


class IdentityKeys(BaseModel):
    # from backend/main.py:1843-1851
    settings_keys: list[str] = [
        "full_name", "email", "phone", "linkedin_url",
        "github_url", "website_url", "city", "current_company",
    ]


class SensitiveKeys(BaseModel):
    # from backend/main.py:1354
    fixed: set[str] = {"anthropic_key", "linkedin_cookie", "x_bearer_token", "custom_connector_headers"}
    suffixes: tuple[str, ...] = ("_api_key", "_key", "_token")


class EvaluatorProfileKeys(BaseModel):
    # from backend/agents/evaluator.py:157-161
    ordered_keys: list[str] = [
        "n", "s", "skills", "exp", "projects",
        "certifications", "certs", "education", "achievements", "awards",
        "publications", "links", "github", "website", "portfolio",
    ]


class ReEvaluationConfig(BaseModel):
    # from backend/main.py:458
    status_locks: set[str] = {"approved", "applied", "interviewing", "rejected", "accepted", "discarded"}


class ScanConfig(BaseModel):
    # from backend/main.py:1282-1349
    max_leads_per_scan: int = 1000  # backend/main.py:1149 default limit for cleanup


class AppDataEnvConfig(BaseModel):
    # from backend/db/client.py:32-38
    app_data_dir: str = "JHM_APP_DATA_DIR"
    localappdata: str = "LOCALAPPDATA"
    xdg_data_home: str = "XDG_DATA_HOME"


class BrowserEnvConfig(BaseModel):
    # from backend/agents/browser_runtime.py:20,24,28,46,53,60
    runtime_dir: str = "JHM_BROWSER_RUNTIME_DIR"
    playwright_browsers_path: str = "PLAYWRIGHT_BROWSERS_PATH"
    browser: str = "BROWSER"
    playwright_chromium_executable: str = "PLAYWRIGHT_CHROMIUM_EXECUTABLE"
    runtime_url: str = "JHM_BROWSER_RUNTIME_URL"


class AutoApplyEnvConfig(BaseModel):
    # from backend/agents/actuator.py:12
    env_var: str = "JHM_AUTO_APPLY"


class BearerTokenEnvConfig(BaseModel):
    # from backend/main.py:363, x_scout.py:400
    x_bearer_token: str = "X_BEARER_TOKEN"
    twitter_bearer_token: str = "TWITTER_BEARER_TOKEN"


class AppConfig(BaseModel):
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
    app_data: AppDataEnvConfig = AppDataEnvConfig()
    browser: BrowserEnvConfig = BrowserEnvConfig()
    auto_apply: AutoApplyEnvConfig = AutoApplyEnvConfig()
    bearer_tokens: BearerTokenEnvConfig = BearerTokenEnvConfig()


config = AppConfig()
