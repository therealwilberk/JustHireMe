import json
import os
import re
from typing import Any

from core.ws_manager import cm
from config import settings
from config.secrets import resolve_secret


def get_job_targets() -> list[str]:
    """Read configured job targets from settings. Empty = none configured."""
    from db.client import get_settings
    cfg = get_settings()
    stored = cfg.get("job_targets", "")
    if not stored:
        return []
    try:
        result = json.loads(stored)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def get_blocked_markers() -> list[str]:
    """Read configured blocked markers from settings."""
    from db.client import get_settings
    cfg = get_settings()
    stored = cfg.get("blocked_markers", "")
    if not stored:
        return []
    try:
        result = json.loads(stored)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def save_job_targets(targets: list[str], blocked: list[str]) -> None:
    from db.client import save_settings
    save_settings({
        "job_targets": json.dumps(targets),
        "blocked_markers": json.dumps(blocked),
    })


def validate_job_targets(entries: list[str]) -> list[str]:
    """Returns list of error messages (empty = valid)."""
    errors: list[str] = []
    if not isinstance(entries, list):
        return ["must be a list of strings"]
    if len(entries) > 100:
        errors.append("exceeds maximum of 100 entries")
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        cleaned = entry.strip()
        if not isinstance(entry, str) or not cleaned:
            errors.append(f"[{i}]: entry must be a non-empty string")
        elif len(cleaned) > 500:
            errors.append(f"[{i}]: entry exceeds 500 character limit")
        elif cleaned.lower() in seen:
            errors.append(f"[{i}]: duplicate entry '{cleaned}'")
        else:
            seen.add(cleaned.lower())
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                host = cleaned.split("/")[2] if "://" in cleaned else ""
                if "." not in host:
                    errors.append(f"[{i}]: URL must contain a valid domain with a dot (e.g. https://remoteok.com/api)")
            elif cleaned.startswith("site:"):
                domain_part = cleaned[5:].strip().split()[0]
                if "." not in domain_part:
                    errors.append(f"[{i}]: site: entry must contain a domain with a dot (e.g. site:linkedin.com/jobs)")
            elif cleaned.startswith("github:") or cleaned.startswith("hn:") or cleaned.startswith("reddit:"):
                pass
            elif cleaned in ("hn-hiring",):
                pass
            else:
                errors.append(f"[{i}]: entry must start with http://, https://, site:, github:, hn:, reddit:, or be a known short name")
    return errors


def validate_blocked_markers(entries: list[str]) -> list[str]:
    """Returns list of error messages (empty = valid).
    Blocked markers are simple keywords — no URL validation needed."""
    errors: list[str] = []
    if not isinstance(entries, list):
        return ["must be a list of strings"]
    if len(entries) > 100:
        errors.append("exceeds maximum of 100 entries")
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        cleaned = entry.strip()
        if not isinstance(entry, str) or not cleaned:
            errors.append(f"[{i}]: entry must be a non-empty string")
        elif len(cleaned) > 200:
            errors.append(f"[{i}]: entry exceeds 200 character limit")
        elif cleaned.lower() in seen:
            errors.append(f"[{i}]: duplicate entry '{cleaned}'")
        else:
            seen.add(cleaned.lower())
    return errors


def _split_configured_targets(raw: str) -> list[str]:
    targets: list[str] = []
    for line in str(raw or "").splitlines():
        target = line.strip().rstrip(",").strip()
        if not target or target.startswith("#"):
            continue
        targets.append(target)
    return targets


def _job_targets(raw: str, market_focus: str = "global") -> list[str]:
    targets = _split_configured_targets(raw)
    if not targets:
        return get_job_targets()

    blocked = get_blocked_markers()
    return [target for target in targets if not any(marker in target.lower() for marker in blocked)]


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
    location = '("remote" OR "hybrid" OR "global" OR "onsite")'
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


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _free_sources_enabled(cfg: dict) -> bool:
    return _truthy(cfg.get("free_sources_enabled", "false"))


async def _broadcast_x_source_errors(errors: list[str]) -> None:
    if not errors:
        return
    for msg in errors[:3]:
        await cm.broadcast({"type": "agent", "event": "x_source_error", "msg": f"X source skipped: {msg}"})
    if len(errors) > 3:
        await cm.broadcast({"type": "agent", "event": "x_source_error", "msg": f"{len(errors) - 3} more X queries were skipped"})
