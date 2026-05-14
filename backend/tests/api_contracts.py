"""Per-endpoint response contract schemas.

Each endpoint's response shape is defined here as TypedDict/dataclass/tuple
so that tests import schema knowledge from a single source of truth.
"""

from typing import Any

# ── Assertion helpers — keep here or in conftest ─────────────────────────


def _assert_body_type(body: Any, expected_type: type) -> None:
    assert isinstance(body, expected_type), (
        f"Expected {expected_type.__name__}, got {type(body).__name__}"
    )


def error_detail_fields_ok(body: dict) -> bool:
    """FastAPI-style {"detail": str}."""
    return "detail" in body and isinstance(body["detail"], str)


def validation_error_detail_ok(body: dict) -> bool:
    """Pydantic 422 detail shape: list of {loc, msg, type}."""
    detail = body.get("detail")
    if not isinstance(detail, list):
        return False
    for item in detail:
        if not isinstance(item, dict):
            return False
        if "loc" not in item or "msg" not in item or "type" not in item:
            return False
        if not isinstance(item["loc"], list):
            return False
        if not isinstance(item["msg"], str):
            return False
        if not isinstance(item["type"], str):
            return False
    return True


# ── Contract definitions ────────────────────────────────────────────────


class HealthContract:
    """GET /health → 200"""
    STATUS = "alive"
    REQUIRED_ROOT_KEYS = {"status", "uptime_seconds", "timestamp", "log_level", "dependencies"}
    REQUIRED_DEP_KEYS = {"database", "browser", "api_keys"}
    DB_KEYS = {"status", "latency_ms"}
    BROWSER_KEYS = {"status", "path"}
    API_KEYS = {"status", "configured_providers"}


class AuthContract:
    """Common auth error responses"""
    UNAUTHORIZED_DETAIL = True          # detail must be a str
    HEALTH_UNPROTECTED_STATUS = 200


class NotFoundContract:
    """404: {"detail": str}"""
    REQUIRED_KEYS = {"detail"}
    DETAIL_TYPE = str


class ValidationContract:
    """422: Pydantic validation error shape"""
    DETAIL_IS_LIST = True
    ERROR_ITEM_KEYS = {"loc", "msg", "type"}
    LOC_IS_LIST = True
    MSG_IS_STR = True
    TYPE_IS_STR = True


class OkContract:
    """DELETE/PUT/POST returning {"ok": true}"""
    STATUS = 200
    REQUIRED_KEYS = {"ok"}
    OK_VALUE = True


class LeadsListContract:
    """GET /api/v1/leads → 200: list of dicts"""
    STATUS = 200
    RESPONSE_TYPE = list
    ITEM_TYPE = dict


class ExportCsvContract:
    """GET /api/v1/leads/export.csv → 200: text/csv"""
    STATUS = 200
    CONTENT_TYPE_PREFIX = "text/csv"
    REQUIRED_HEADER_FIELDS = {"job_id", "title", "company", "url"}


class TemplateContract:
    """GET /api/v1/template → 200: {"template": str}"""
    STATUS = 200
    REQUIRED_KEYS = {"template"}
    TEMPLATE_TYPE = str


class SettingsValidateContract:
    """GET /api/v1/settings/validate → 200: dict of provider results"""
    STATUS = 200
    RESPONSE_TYPE = dict
    PROVIDER_RESULT_KEYS = {"status", "latency_ms"}
    VALID_STATUSES = {"ok", "invalid_key", "unreachable", "not_configured", "unchecked"}


class SettingsSaveContract:
    """POST /api/v1/settings → 200: {"ok": true}"""
    STATUS = 200
    REQUIRED_KEYS = {"ok"}


class FollowupsContract:
    """GET /api/v1/followups/due → 200: list"""
    STATUS = 200
    RESPONSE_TYPE = list


class PipelineRunContract:
    """POST /api/v1/leads/{job_id}/pipeline/run → 200: {"status": "started", "job_id": str}"""
    STATUS = 200
    REQUIRED_KEYS = {"status", "job_id"}
    STATUS_VALUE = "started"


class GenerateContract:
    """POST /api/v1/leads/{job_id}/generate → 200: {"status": "ready", "job_id": str, "lead": dict}"""
    STATUS = 200
    REQUIRED_KEYS = {"status", "job_id", "lead"}
    STATUS_VALUE = "ready"
    LEAD_TYPE = dict


class FormReadContract:
    """POST /api/v1/leads/{job_id}/form/read → 200: dict result from read_form()"""
    STATUS = 200
    RESPONSE_TYPE = dict


class IdentityContract:
    """GET /api/v1/identity → 200"""
    STATUS = 200
    REQUIRED_KEYS = {
        "full_name", "email", "phone", "linkedin_url",
        "github_url", "website_url", "city", "current_company",
    }
    ALL_STRING_VALUES = True


class SelectorsContract:
    """POST /api/v1/selectors/refresh → 200"""
    STATUS = 200
    REQUIRED_KEYS = {"version", "platforms"}
    PLATFORMS_TYPE = list


class LinkedInIngestContract:
    """POST /api/v1/ingest/linkedin → 200 / 400 / 422 / 413"""
    STATUS_SUCCESS = 200
    SUCCESS_REQUIRED_KEYS = {"status", "stats", "location", "errors"}
    VALID_STATUS_VALUES = {"ok", "partial"}
    STATS_TYPE = dict
    ERRORS_TYPE = list


class GithubIngestContract:
    """POST /api/v1/ingest/github → 200 / 404 / 422"""
    STATUS_SUCCESS = 200
    SUCCESS_REQUIRED_KEYS = {"status", "github_user", "stats", "errors"}
    VALID_STATUS_VALUES = {"ok", "partial"}
    GITHUB_USER_TYPE = dict
    STATS_TYPE = dict
    ERRORS_TYPE = list


class ProfileImportContract:
    """POST /api/v1/ingest/profile → 200 / 422"""
    STATUS_SUCCESS = 200
    SUCCESS_REQUIRED_KEYS = {"status", "stats", "errors"}
    VALID_STATUS_VALUES = {"ok", "partial"}
    STATS_TYPE = dict
    ERRORS_TYPE = list
    STATS_KEYS = {"skills", "experience", "projects", "education", "certifications", "achievements"}


class ProfileTemplateContract:
    """GET /api/v1/ingest/profile/template → 200: dict with 'skills'"""
    STATUS = 200
    RESPONSE_TYPE = dict
    REQUIRED_KEYS = {"skills"}


class PortfolioIngestContract:
    """POST /api/v1/ingest/portfolio → 200 / 400 / 422"""
    STATUS_SUCCESS = 200
    RESPONSE_TYPE = dict


class ScanContract:
    """POST /api/v1/scan → 200 / 409"""
    STATUS_STARTED = 200
    REQUIRED_KEYS = {"status"}
    STATUS_VALUE = "scanning"


class ManualLeadContract:
    """POST /api/v1/leads/manual → 200 / 400 / 422"""
    STATUS_SUCCESS = 200
    SUCCESS_TYPE = dict
