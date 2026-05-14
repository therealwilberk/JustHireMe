from pydantic import BaseModel, Field
from typing import Literal


class LoggingConfig(BaseModel):
    # from backend/logger.py:11
    env_var: str = "JHM_LOG_LEVEL"
    default_level: str = "INFO"

    # from backend/logger.py:19-21
    format_string: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format: str = "%H:%M:%S"

    # from backend/logger.py:15
    output_stream: str = "stderr"

    # from backend/logger.py:24
    propagate: bool = False

    log_file: str = Field(default="", description="Path to log file. Empty = no file handler.")
    log_file_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    log_file_backup_count: int = Field(default=3, ge=0)


config = LoggingConfig()
