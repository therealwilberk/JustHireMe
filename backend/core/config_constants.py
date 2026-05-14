"""Module-level constants and shared singletons for the application.

These values are initialized at import time and are not part of the
config system (see config/ for Pydantic settings). Includes scheduler
instance, auth token, bearer scheme, and CORS origin regex.
"""

import secrets
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.security import HTTPBearer
from logger import get_logger


_log = get_logger(__name__)
_UP = time.monotonic()  # Application start timestamp for uptime tracking
_sched = AsyncIOScheduler()  # Global background task scheduler
_API_TOKEN: str = secrets.token_hex(32)  # Auto-generated API bearer token
_LOCAL_ORIGIN_RE = r"^(tauri://localhost|https?://(localhost|127\.0\.0\.1|tauri\.localhost|\[::1\])(?::\d+)?)$"  # CORS origin whitelist regex for local dev
_bearer = HTTPBearer(auto_error=False)  # FastAPI HTTP Bearer scheme, non-fatal on missing token
