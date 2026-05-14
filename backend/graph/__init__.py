from __future__ import annotations

import threading
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from logger import get_logger

_log = get_logger(__name__)

_DEFAULT_EVALUATE_TIMEOUT = 600
_DEFAULT_GENERATE_TIMEOUT = 600


class PipelineState(TypedDict):
    job_id: str
    lead: dict[str, Any]
    profile: dict[str, Any]
    cfg: dict[str, Any]
    score: int
    reason: str
    match_points: list[str]
    gaps: list[str]
    asset_path: str
    cover_letter_path: str
    error: str | None
    error_stage: str | None


def _with_timeout(seconds: float | None, func, *args, **kwargs):
    if seconds is None or seconds <= 0:
        return func(*args, **kwargs)
    result: list = []
    exc: list[BaseException] = []
    done = threading.Event()

    def wrapper():
        try:
            result.append(func(*args, **kwargs))
        except BaseException as e:
            exc.append(e)
        finally:
            done.set()

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()

    if not done.wait(timeout=seconds):
        raise TimeoutError(f"Operation timed out after {seconds}s")
    if exc:
        raise exc[0]
    return result[0]


def _job_eval_document(lead: dict) -> str:
    desc = (lead.get("description") or "").strip()
    return (
        f"Job Title: {lead.get('title','')}\n"
        f"Company: {lead.get('company','')}\n"
        f"URL: {lead.get('url','')}\n"
        + (f"Description: {desc}" if desc else "")
    )


def evaluate_node(state: PipelineState) -> dict:
    try:
        from agents.evaluator import score

        timeout = float(state.get("cfg", {}).get("evaluate_timeout") or _DEFAULT_EVALUATE_TIMEOUT)
        result = _with_timeout(timeout, score, _job_eval_document(state["lead"]), state["profile"])
        return {
            "score": int(result.get("score") or 0),
            "reason": str(result.get("reason") or ""),
            "match_points": list(result.get("match_points") or []),
            "gaps": list(result.get("gaps") or []),
            "error": None,
            "error_stage": None,
        }
    except Exception as exc:
        _log.error("evaluate failed for %s: %s", state.get("job_id", "?"), exc)
        return {
            "score": 0,
            "reason": "eval failed",
            "match_points": [],
            "gaps": [],
            "error": str(exc),
            "error_stage": "evaluate",
        }


def generate_node(state: PipelineState) -> dict:
    threshold = int(state.get("cfg", {}).get("auto_generate_threshold") or 60)
    if int(state.get("score") or 0) < threshold:
        return {"asset_path": "", "cover_letter_path": ""}
    try:
        from agents.generator import run_package

        template = str(state.get("cfg", {}).get("resume_template") or "")
        timeout = float(state.get("cfg", {}).get("generate_timeout") or _DEFAULT_GENERATE_TIMEOUT)
        package = _with_timeout(timeout, run_package, {**state["lead"], **state}, template=template)
        return {
            "asset_path": package.get("resume", ""),
            "cover_letter_path": package.get("cover_letter", ""),
            "error": None,
            "error_stage": None,
        }
    except Exception as exc:
        _log.error("generate failed for %s: %s", state.get("job_id", "?"), exc)
        return {
            "asset_path": "",
            "cover_letter_path": "",
            "error": str(exc),
            "error_stage": "generate",
        }


def persist_node(state: PipelineState) -> dict:
    from db.client import save_asset_package, update_lead_score

    jid = state.get("job_id") or "?"
    try:
        update_lead_score(
            jid,
            int(state.get("score") or 0),
            state.get("reason") or "",
            state.get("match_points") or [],
            state.get("gaps") or [],
        )
        if state.get("asset_path") or state.get("cover_letter_path"):
            save_asset_package(
                jid,
                state.get("asset_path") or "",
                state.get("cover_letter_path") or "",
            )
    except Exception as exc:
        _log.error("persist failed for %s: %s", jid, exc)
        return {"error": str(exc), "error_stage": "persist"}
    return {}


def build_eval_graph():
    g = StateGraph(PipelineState)
    g.add_node("evaluate", evaluate_node)
    g.add_node("generate", generate_node)
    g.add_node("persist", persist_node)

    g.set_entry_point("evaluate")
    g.add_edge("evaluate", "generate")
    g.add_edge("generate", "persist")
    g.add_edge("persist", END)

    return g.compile()


eval_graph = build_eval_graph()
