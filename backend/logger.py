"""Logging setup with correlation context enrichment.

Configures Python loggers with a CorrelationFilter that injects
contextual metadata (correlation ID, workflow, lead, job) from
the async CorrelationContext, and a ContextFormatter that appends
non-empty context fields as structured key=value pairs.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import settings


class CorrelationFilter(logging.Filter):
    """Inject correlation context fields onto log records.

    Reads the active CorrelationContext and attaches correlation_id
    along with optional workflow, lead, job, node, subsystem, degraded,
    and retrying fields to every log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich the log record with correlation context fields.

        Args:
            record: The log record to enrich.

        Returns:
            Always True to allow the record through the filter.
        """
        try:
            from log_context import get_context
            ctx = get_context()
        except Exception:
            ctx = None
        record.correlation_id = ctx.correlation_id if ctx else "-"
        record._ctx_subsystem = ctx.subsystem if ctx and ctx.subsystem else ""
        record._ctx_workflow = ctx.workflow_type if ctx and ctx.workflow_type else ""
        record._ctx_lead = ctx.lead_id if ctx and ctx.lead_id else ""
        record._ctx_job = ctx.job_id if ctx and ctx.job_id else ""
        record._ctx_node = ctx.node if ctx and ctx.node else ""
        record._ctx_degraded = "DEGRADED" if ctx and ctx.degraded else ""
        record._ctx_retrying = "RETRYING" if ctx and ctx.retrying else ""
        return True


class ContextFormatter(logging.Formatter):
    """Format log records with appended context key=value pairs.

    After the standard format is applied, non-empty context fields
    (lead, job, node, subsystem, workflow, degraded, retrying) are
    appended as a pipe-separated suffix.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Apply standard formatting and append context fields.

        Args:
            record: The log record to format.

        Returns:
            The formatted log string with context suffix.
        """
        s = super().format(record)
        extras = []
        if record._ctx_lead:
            extras.append(f"lead={record._ctx_lead}")
        if record._ctx_job:
            extras.append(f"job={record._ctx_job}")
        if record._ctx_node:
            extras.append(f"node={record._ctx_node}")
        if record._ctx_subsystem:
            extras.append(f"sub={record._ctx_subsystem}")
        if record._ctx_workflow:
            extras.append(f"flow={record._ctx_workflow}")
        if record._ctx_degraded:
            extras.append(record._ctx_degraded)
        if record._ctx_retrying:
            extras.append(record._ctx_retrying)
        if extras:
            s = f"{s} | {' '.join(extras)}"
        return s


def get_logger(name: str) -> logging.Logger:
    """Get or create a configured logger with correlation context support.

    Sets up a stderr stream handler (and optional rotating file handler)
    with CorrelationFilter and standard Formatter. Handlers are added
    only once per logger name.

    Args:
        name: The logger name, typically __name__ from the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level_str = os.environ.get(settings.logging.env_var, settings.logging.default_level).upper()
    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    fmt = logging.Formatter(
        fmt=settings.logging.format_string or "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s",
        datefmt=settings.logging.date_format,
    )
    sh.setFormatter(fmt)
    sh.addFilter(CorrelationFilter())
    logger.addHandler(sh)

    log_file = os.environ.get("JHM_LOG_FILE") or settings.logging.log_file
    if log_file:
        fh = RotatingFileHandler(
            log_file,
            maxBytes=settings.logging.log_file_max_bytes,
            backupCount=settings.logging.log_file_backup_count,
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        fh.addFilter(CorrelationFilter())
        logger.addHandler(fh)

    logger.propagate = False
    return logger
