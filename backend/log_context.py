"""Correlation context propagation for structured logging.

Provides a thread-safe mechanism for propagating correlation IDs and
contextual metadata across async boundaries using contextvars. Used
by the logging system to enrich log records with workflow state.
"""

import contextvars
import uuid
from dataclasses import dataclass, replace
from typing import Optional


@dataclass
class CorrelationContext:
    """Contextual metadata carried across async boundaries for log enrichment.

    Attributes:
        correlation_id: Unique identifier tying together related log entries.
        workflow_type: Type of workflow being executed (e.g. scan, scoring).
        lead_id: Identifier of the lead being processed.
        job_id: Identifier of the job posting being handled.
        node: Name of the processing node or stage.
        subsystem: Name of the subsystem generating the log.
        degraded: Whether the system is operating in degraded mode.
        retrying: Whether the current operation is a retry.
    """
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
    """Create a new CorrelationContext with an auto-generated correlation ID.

    Args:
        **overrides: Field values to override on the new context.

    Returns:
        A new CorrelationContext instance.
    """
    if "correlation_id" not in overrides:
        overrides["correlation_id"] = str(uuid.uuid4())
    return CorrelationContext(**overrides)


def get_context() -> Optional[CorrelationContext]:
    """Retrieve the current correlation context.

    Returns:
        The active CorrelationContext, or None if none is set.
    """
    return _context_var.get()


def set_context(ctx: CorrelationContext) -> contextvars.Token:
    """Set the current correlation context.

    Args:
        ctx: The CorrelationContext to activate.

    Returns:
        A token for later use with reset_context().
    """
    return _context_var.set(ctx)


def reset_context(token: contextvars.Token) -> None:
    """Restore a previous correlation context using a token.

    Args:
        token: The token returned by a prior set_context() call.
    """
    _context_var.reset(token)


def enrich(**fields) -> contextvars.Token:
    """Merge new fields into the current correlation context.

    Args:
        **fields: Field names and values to update on the context.

    Returns:
        A token for later use with reset_context().

    Raises:
        RuntimeError: If no correlation context is currently active.
    """
    ctx = get_context()
    if ctx is None:
        raise RuntimeError("No correlation context to enrich")
    new_ctx = replace(ctx, **fields)
    return set_context(new_ctx)
