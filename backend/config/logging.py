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


config = LoggingConfig()
