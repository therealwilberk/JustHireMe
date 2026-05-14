import secrets
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.security import HTTPBearer
from logger import get_logger


_log = get_logger(__name__)
_UP = time.monotonic()
_sched = AsyncIOScheduler()
_API_TOKEN: str = secrets.token_hex(32)
_LOCAL_ORIGIN_RE = r"^(tauri://localhost|https?://(localhost|127\.0\.0\.1|tauri\.localhost|\[::1\])(?::\d+)?)$"
_bearer = HTTPBearer(auto_error=False)
