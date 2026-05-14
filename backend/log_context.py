import contextvars
import uuid
from dataclasses import dataclass, replace
from typing import Optional


@dataclass
class CorrelationContext:
    correlation_id: str
    workflow_type: Optional[str] = None
    lead_id: Optional[str] = None
    job_id: Optional[str] = None
    node: Optional[str] = None
    subsystem: Optional[str] = None
    degraded: bool = False
    retrying: bool = False


_context_var: contextvars.ContextVar[Optional[CorrelationContext]] = (
    contextvars.ContextVar("correlation_context", default=None)
)


def new_context(**overrides) -> CorrelationContext:
    return CorrelationContext(correlation_id=str(uuid.uuid4()), **overrides)


def get_context() -> Optional[CorrelationContext]:
    return _context_var.get()


def set_context(ctx: CorrelationContext) -> contextvars.Token:
    return _context_var.set(ctx)


def reset_context(token: contextvars.Token) -> None:
    _context_var.reset(token)


def enrich(**fields) -> contextvars.Token:
    ctx = get_context()
    if ctx is None:
        raise RuntimeError("No correlation context to enrich")
    new_ctx = replace(ctx, **fields)
    return set_context(new_ctx)
