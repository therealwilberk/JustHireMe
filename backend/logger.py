import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import settings


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
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
    def format(self, record: logging.LogRecord) -> str:
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

    if settings.logging.log_file:
        fh = RotatingFileHandler(
            settings.logging.log_file,
            maxBytes=settings.logging.log_file_max_bytes,
            backupCount=settings.logging.log_file_backup_count,
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        fh.addFilter(CorrelationFilter())
        logger.addHandler(fh)

    logger.propagate = False
    return logger
