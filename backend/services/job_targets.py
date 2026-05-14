import os
import re

from core.ws_manager import cm
from config import settings
from config.secrets import resolve_secret


DEFAULT_JOB_TARGETS = (
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
)

INDIA_JOB_TARGETS = (
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
)

_BLOCKED_JOB_TARGET_MARKERS = (
    "freelance", "upwork", "freelancer.com", "fiverr", "contra.com",
    "peopleperhour", "guru.com", "truelancer", "codementor", "toptal",
)


def _split_configured_targets(raw: str) -> list[str]:
    targets: list[str] = []
    for line in str(raw or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.split(","):
            target = part.strip()
            if target and not target.startswith("#"):
                targets.append(target)
    return targets


def _dedupe_targets(targets: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for target in targets:
        key = target.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(target.strip())
    return out


def _job_market_focus(value) -> str:
    focus = str(value or "global").strip().lower()
    return "india" if focus in {"india", "in", "indian", "indian_startups"} else "global"


def _is_hn_target(target: str) -> bool:
    lower = target.lower()
    return lower.startswith("hn:") or "hn-hiring" in lower or "hackernews" in lower or "news.ycombinator.com" in lower


def _job_targets(raw: str, market_focus: str = "global") -> list[str]:
    focus = _job_market_focus(market_focus)
    targets = _split_configured_targets(raw)
    if not targets:
        return list(INDIA_JOB_TARGETS if focus == "india" else DEFAULT_JOB_TARGETS)

    filtered: list[str] = []
    for target in targets:
        lower = target.lower()
        if any(marker in lower for marker in _BLOCKED_JOB_TARGET_MARKERS):
            continue
        filtered.append(target)

    if focus == "global" and filtered and all(_is_hn_target(target) for target in filtered):
        filtered.extend(target for target in DEFAULT_JOB_TARGETS if not _is_hn_target(target))

    if focus == "india":
        india_markers = (
            "india", "indian", "bangalore", "bengaluru", "mumbai", "delhi",
            "gurgaon", "gurugram", "hyderabad", "pune", "chennai", "noida",
            "cutshort", "instahyre", "naukri", "foundit", "internshala",
            "glassdoor.co.in",
        )
        filtered = [target for target in filtered if any(marker in target.lower() for marker in india_markers)]

    fallback = INDIA_JOB_TARGETS if focus == "india" else DEFAULT_JOB_TARGETS
    return _dedupe_targets(filtered) or list(fallback)


def _desired_position(cfg: dict) -> str:
    for key in ("desired_position", "target_position", "target_role", "onboarding_target_role"):
        value = str(cfg.get(key) or "").strip()
        if value:
            return value
    return ""


def _profile_for_discovery(profile: dict | None, cfg: dict) -> dict:
    profile = dict(profile or {})
    desired = _desired_position(cfg)
    if desired:
        summary = str(profile.get("s") or "").strip()
        if desired.lower() not in summary.lower():
            profile["s"] = f"{desired}. {summary}".strip()
        else:
            profile["s"] = summary or desired
        profile["desired_position"] = desired
    return profile


def _terms_for_discovery(profile: dict, limit: int = 4) -> list[str]:
    terms: list[str] = []
    summary = str(profile.get("desired_position") or profile.get("s") or "").strip()
    if summary:
        terms.append(" ".join(summary.split()[:5]))
    for exp in profile.get("exp", []) or []:
        if isinstance(exp, dict) and exp.get("role"):
            terms.append(str(exp["role"]))
    for skill in profile.get("skills", []) or []:
        if isinstance(skill, dict) and skill.get("n"):
            terms.append(str(skill["n"]))
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        term = re.sub(r"\s+", " ", str(term)).strip(" ,.;:-")
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            out.append(term)
    return out[:limit] or ["jobs"]


def _profile_free_source_targets(profile: dict) -> str:
    terms = _terms_for_discovery(profile, 3)
    role_query = " ".join(terms[:2])
    return "\n".join([
        f"github:{role_query} hiring help wanted",
        f"hn:{role_query} remote hiring",
        f"reddit:forhire:{role_query} hiring job remote",
    ])


def _profile_x_queries(profile: dict, market_focus: str = "global") -> str:
    terms = _terms_for_discovery(profile, 4)
    role = " OR ".join(f'"{term}"' for term in terms[:3])
    location = '("India" OR "Indian" OR "Bengaluru" OR "Mumbai" OR "Pune" OR "Hyderabad")' if _job_market_focus(market_focus) == "india" else '("remote" OR "hybrid" OR "global" OR "onsite")'
    return "\n".join([
        f'("hiring" OR "job opening" OR "open role") ({role}) {location} lang:en -is:retweet',
        f'("we are hiring" OR "is hiring" OR "apply") ({role}) lang:en -is:retweet',
    ])


def _has_x_token(cfg: dict) -> bool:
    bt = settings.app.bearer_tokens
    return bool(
        resolve_secret(bt.x_bearer_token, settings.app.settings_key_names.x_bearer_token)
        or os.environ.get(bt.twitter_bearer_token)
    )


def _int_cfg(cfg: dict, key: str, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(str(cfg.get(key, "") or "").strip())
    except (ValueError, TypeError):
        value = default
    return max(min_value, min(value, max_value))


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _free_sources_enabled(cfg: dict) -> bool:
    return _truthy(cfg.get("free_sources_enabled", "false"))


async def _broadcast_x_source_errors(errors: list[str]):
    if not errors:
        return
    for msg in errors[:3]:
        await cm.broadcast({"type": "agent", "event": "x_source_error", "msg": f"X source skipped: {msg}"})
    if len(errors) > 3:
        await cm.broadcast({"type": "agent", "event": "x_source_error", "msg": f"{len(errors) - 3} more X queries were skipped"})
