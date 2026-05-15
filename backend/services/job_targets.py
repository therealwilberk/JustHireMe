"""Job target resolution, settings accessors, and validation.

Provides helpers to read, write, parse, and validate job board URLs,
blocked markers, and related settings.  Also includes profile-enrichment
utilities used by the discovery pipeline.
"""

import json
import os
import re
from typing import Any

from core.ws_manager import cm
from config import settings
from config.secrets import resolve_secret


def get_job_targets() -> list[str]:
    """Read configured job targets from settings. Empty = none configured."""
    from db.client import get_settings  # lazy: lancedb import takes ~7s
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
    from db.client import get_settings  # lazy: lancedb import takes ~7s
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
    """Persist job targets and blocked markers to settings.

    Args:
        targets: List of job board URL strings.
        blocked: List of keyword markers used to filter out unwanted targets.
    """
    from db.client import save_settings  # lazy: lancedb import takes ~7s
    save_settings({
        "job_targets": json.dumps(targets),
        "blocked_markers": json.dumps(blocked),
    })


def validate_job_targets(entries: list[str]) -> list[str]:
    """Returns list of error messages (empty = valid).

    Validates structure, length, and format of job target entries.
    Accepted formats: ``http(s)://...``, ``site:domain/...``,
    ``github:``, ``hn:``, ``reddit:``, and known short names.

    Args:
        entries: Candidate list of job target strings.

    Returns:
        A list of human-readable error messages.  An empty list means
        the input is valid.

    Example:
        >>> validate_job_targets(["https://remoteok.com/api", "site:linkedin.com/jobs"])
        []
        >>> validate_job_targets(["bad-format"])
        ["[0]: entry must start with http://, https://, site:, ..."]
    """
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

    Blocked markers are simple keywords — no URL validation needed.

    Args:
        entries: Candidate list of blocked keyword strings.

    Returns:
        A list of human-readable error messages.  An empty list means
        the input is valid.
    """
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
    """Parse a raw newline-separated target string into a list.

    Strips whitespace and trailing commas.  Lines starting with ``#``
    are treated as comments and skipped.

    Args:
        raw: Raw multi-line string from settings.

    Returns:
        List of non-empty, uncommented target lines.
    """
    targets: list[str] = []
    for line in str(raw or "").splitlines():
        target = line.strip().rstrip(",").strip()
        if not target or target.startswith("#"):
            continue
        targets.append(target)
    return targets


def _job_targets(raw: str) -> list[str]:
    """Resolve job targets from raw settings, falling back to stored JSON.

    Filters targets against the blocked-markers list (case-insensitive
    substring match).

    Args:
        raw: Raw ``job_boards`` setting string.

    Returns:
        List of resolved and filtered job target URLs.
    """
    targets = _split_configured_targets(raw)
    if not targets:
        return get_job_targets()

    blocked = get_blocked_markers()
    return [target for target in targets if not any(marker in target.lower() for marker in blocked)]


def _desired_position(cfg: dict) -> str:
    """Extract the desired position string from a settings dict.

    Checks multiple known keys in priority order.

    Args:
        cfg: Application settings dictionary.

    Returns:
        The first non-empty position string found, or ``""``.
    """
    for key in ("desired_position", "target_position", "target_role", "onboarding_target_role"):
        value = str(cfg.get(key) or "").strip()
        if value:
            return value
    return ""


def _profile_for_discovery(profile: dict | None, cfg: dict) -> dict:
    """Enrich a user profile with the desired position from config.

    Prepends the desired position to the profile summary when it is
    not already present, and sets ``profile["desired_position"]``.

    Args:
        profile: Raw user profile dict (may be ``None``).
        cfg: Application settings dictionary.

    Returns:
        Enriched profile dictionary (always a new dict).
    """
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
    """Extract search terms from a profile for discovery queries.

    Sources: desired position / summary, role from each experience
    entry, and skill names.

    Args:
        profile: User profile dictionary (may contain ``desired_position``,
            ``s``, ``exp``, ``skills``).
        limit: Maximum number of unique terms to return (default 4).

    Returns:
        A list of deduplicated, stripped terms, falling back to
        ``["jobs"]`` when the profile is empty.
    """
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
    """Build free-source (GitHub/HN/Reddit) target strings from a profile.

    Args:
        profile: User profile dictionary.

    Returns:
        A newline-separated string of target queries for free sources,
        one per line.
    """
    terms = _terms_for_discovery(profile, 3)
    role = " ".join(terms[:2])
    template = settings.scraping.limits.free_source_query_template
    return template.replace("{role}", role)


def _profile_x_queries(profile: dict) -> str:
    """Build X/Twitter search queries from a profile.

    Args:
        profile: User profile dictionary.

    Returns:
        A newline-separated string of X search queries, one per line.
    """
    terms = _terms_for_discovery(profile, 4)
    role = " OR ".join(f'"{term}"' for term in terms[:3])
    location = '("remote" OR "hybrid" OR "global" OR "onsite")'
    tpl = settings.scraping.limits.x_query_template
    alt = settings.scraping.limits.x_query_alt_template
    return "\n".join([
        tpl.replace("{role}", role).replace("{location}", location),
        alt.replace("{role}", role),
    ])


def _has_x_token(cfg: dict) -> bool:
    """Check whether an X/Twitter API bearer token is available.

    Checks both the resolved secret (from settings or env vars) and the
    raw ``TWITTER_BEARER_TOKEN`` environment variable.

    Args:
        cfg: Application settings dictionary.

    Returns:
        True if a token is configured and accessible.
    """
    bt = settings.app.bearer_tokens
    return bool(
        resolve_secret(bt.x_bearer_token, settings.app.settings_key_names.x_bearer_token)
        or os.environ.get(bt.twitter_bearer_token)
    )


def _int_cfg(cfg: dict, key: str, default: int, min_value: int, max_value: int) -> int:
    """Read an integer setting with bounds clamping.

    Args:
        cfg: Application settings dictionary.
        key: Setting key to read.
        default: Fallback value when the key is missing or unparseable.
        min_value: Lower clamp bound.
        max_value: Upper clamp bound.

    Returns:
        An integer within ``[min_value, max_value]``.
    """
    try:
        value = int(str(cfg.get(key, "") or "").strip())
    except (ValueError, TypeError):
        value = default
    return max(min_value, min(value, max_value))


def _truthy(value: Any) -> bool:
    """Check whether a value is truthy in the settings convention.

    Accepted truthy strings: ``"1"``, ``"true"``, ``"yes"``, ``"on"``
    (case-insensitive).

    Args:
        value: Any value (string, bool, int, etc.).

    Returns:
        True if the value represents an enabled/truthy setting.
    """
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _free_sources_enabled(cfg: dict) -> bool:
    """Check whether free-source scanning is enabled in settings.

    Args:
        cfg: Application settings dictionary.

    Returns:
        True if ``free_sources_enabled`` is truthy.
    """
    return _truthy(cfg.get("free_sources_enabled", "false"))


async def _broadcast_x_source_errors(errors: list[str]) -> None:
    """Broadcast X source scanning errors to the frontend via WebSocket.

    Sends at most 3 individual error messages and a summary line for
    any remaining errors.

    Args:
        errors: List of error message strings from the X scout module.
    """
    if not errors:
        return
    for msg in errors[:3]:
        await cm.broadcast({"type": "agent", "event": "x_source_error", "msg": f"X source skipped: {msg}"})
    if len(errors) > 3:
        await cm.broadcast({"type": "agent", "event": "x_source_error", "msg": f"{len(errors) - 3} more X queries were skipped"})
