from pydantic import BaseModel, Field
from typing import Literal


class ScraperTimeouts(BaseModel):
    # from backend/agents/scout.py — httpx clients use various timeouts
    default_http: int = Field(default=30, ge=1, le=300)  # scout.py:563, 607, 659, 712, 876
    apify_run: int = Field(default=60, ge=1, le=600)  # scout.py:360
    page_load: int = Field(default=30000, ge=1000, le=300000)  # scout.py:250 (playwright goto, in ms)
    rss_http: int = Field(default=30, ge=1, le=300)  # scout.py:563
    hn_search: int = Field(default=30, ge=1, le=300)  # scout.py:876
    hn_items: int = Field(default=60, ge=1, le=600)  # scout.py:893
    x_search: int = Field(default=30, ge=1, le=300)  # x_scout.py:364
    custom_connector: int = Field(default=30, ge=1, le=300)  # free_scout.py:116
    json_get: int = Field(default=30, ge=1, le=300)  # free_scout.py:249


class RetryConfig(BaseModel):
    # from backend/agents/scout.py:353-357
    max_attempts: int = 4
    exponential_multiplier: int = 1
    exponential_min: int = 2
    exponential_max: int = 30
    retry_after_default: int = 15  # 429 Retry-After fallback


class ScraperLimits(BaseModel):
    # from backend/agents/scout.py, free_scout.py, x_scout.py
    max_results_per_source: int = 60  # scout.py:432 (default source cap)
    connector_max_items: int = 60  # free_scout.py:44
    apify_max_concurrent: int = 1  # implied by single-run
    hn_story_cutoff_days: int = 35  # scout.py:874
    hn_job_min_text_length: int = 80  # scout.py:787
    hn_comment_min_text_length: int = 60  # free_scout.py:451
    reddit_min_text_length: int = 40  # free_scout.py:491
    free_source_max_requests: int = 20  # free_scout.py:555
    free_source_request_cap: int = 80  # free_scout.py:569
    x_max_requests: int = 5  # x_scout.py:386
    x_max_results: int = 50  # x_scout.py:351
    x_max_results_min: int = 10  # x_scout.py:356
    x_max_results_max: int = 100  # x_scout.py:356
    x_max_requests_min: int = 1  # x_scout.py:406
    x_max_requests_max: int = 50  # x_scout.py:406
    x_min_signal_score: int = 55  # x_scout.py:387
    x_min_signal_score_min: int = 0  # x_scout.py:408
    x_min_signal_score_max: int = 100  # x_scout.py:408
    free_source_min_signal_score: int = 60  # free_scout.py:556
    free_source_min_signal_score_min: int = 0  # free_scout.py:574
    free_source_min_signal_score_max: int = 100  # free_scout.py:574


class SourceCaps(BaseModel):
    # from backend/agents/scout.py:25-33
    hn_hiring: int = 25
    hn: int = 20
    remoteok: int = 45
    remotive: int = 45
    jobicy: int = 45
    weworkremotely: int = 40
    rss: int = 35
    default: int = 60  # scout.py:432 fallback


class APISourceURLs(BaseModel):
    # from backend/agents/scout.py, free_scout.py, x_scout.py
    hn_algolia_search: str = "https://hn.algolia.com/api/v1/search"
    hn_algolia_items: str = "https://hn.algolia.com/api/v1/items/{story_id}"
    hn_algolia_search_by_date: str = "https://hn.algolia.com/api/v1/search_by_date"
    remoteok: str = "https://remoteok.com/api"
    reddit_search: str = "https://www.reddit.com/r/{subreddit}/search.json"
    github_search_issues: str = "https://api.github.com/search/issues"
    google_search: str = "https://www.google.com/search?q={query}&tbs=qdr:w"
    apify_run_sync: str = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
    x_api_base: str = "https://api.x.com/2/tweets/search/recent"


class ApifyKeyNames(BaseModel):
    token: str = "APIFY_TOKEN"
    actor: str = "APIFY_ACTOR_DEFAULT"


class ApifySettingsKeyNames(BaseModel):
    token: str = "apify_token"
    actor: str = "apify_actor"


class HNConfig(BaseModel):
    # from backend/agents/scout.py
    who_is_hiring_title_regex: str = r"^Ask HN:\s*Who is hiring\?"
    hiring_story_tags: str = "story,ask_hn"
    numeric_filter_format: str = "created_at_i>{timestamp}"
    company_max_chars: int = 100  # scout.py:823
    role_max_chars: int = 140  # scout.py:833
    description_max_chars: int = 1200  # scout.py:915
    hn_query_default: str = "jobs remote hiring"  # free_scout.py:437
    hn_hits_per_page: int = 30  # free_scout.py:443
    hn_cutoff_days: int = 30  # free_scout.py:438


class ATSEndpoints(BaseModel):
    # from backend/agents/free_scout.py
    greenhouse: str = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    greenhouse_params: str = "content=true"
    lever: str = "https://api.lever.co/v0/postings/{slug}"
    lever_params: str = "mode=json"
    ashby: str = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
    workable_primary: str = "https://www.workable.com/api/accounts/{slug}"
    workable_primary_params: str = "details=true"
    workable_fallback: str = "https://apply.workable.com/api/v1/widget/accounts/{slug}"
    github_per_page: str = "25"
    reddit_limit: str = "25"


class DescriptionLimits(BaseModel):
    # from backend/agents/scout.py, free_scout.py
    scout_extract: int = 1600  # scout.py:455 (default)
    rss_feed: int = 1400  # scout.py:584
    remotive: int = 1800  # scout.py:687
    jobicy: int = 1800  # scout.py:746
    connection_request: int = 1600  # free_scout.py:166
    ats_generic: int = 1200  # free_scout.py:279, 308, 333, 389
    github: int = 1000  # free_scout.py:419
    hn_generic: int = 1200  # free_scout.py:463
    reddit: int = 1200  # free_scout.py:499


class UserAgentConfig(BaseModel):
    # from backend/agents/scout.py, free_scout.py, x_scout.py
    scout_template: str = "JustHireMe {source} scout"
    free_scout: str = "JustHireMe free-source scout"
    custom_connector: str = "JustHireMe custom connector"
    contact_lookup: str = "JustHireMe/1.0"
    remoteok_fallback: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    accept_json: str = "application/json"
    accept_rss: str = "application/json, application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7"


class ScrapingConfig(BaseModel):
    timeouts: ScraperTimeouts = ScraperTimeouts()
    retry: RetryConfig = RetryConfig()
    limits: ScraperLimits = ScraperLimits()
    source_caps: SourceCaps = SourceCaps()
    api_urls: APISourceURLs = APISourceURLs()
    hn: HNConfig = HNConfig()
    ats_endpoints: ATSEndpoints = ATSEndpoints()
    description_limits: DescriptionLimits = DescriptionLimits()
    user_agents: UserAgentConfig = UserAgentConfig()
    apify_key_names: ApifyKeyNames = ApifyKeyNames()
    apify_settings_key_names: ApifySettingsKeyNames = ApifySettingsKeyNames()

    lead_max_age_days: int = 7  # scout.py:20


config = ScrapingConfig()
