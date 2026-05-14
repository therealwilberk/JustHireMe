import asyncio
import json
from logger import get_logger

_log = get_logger(__name__)


def _agent_event_action(msg: dict) -> str:
    event = str(msg.get("event") or "agent").strip() or "agent"
    detail = str(msg.get("msg") or "").strip()
    return f"{event}: {detail}" if detail else event


class _CM:
    def __init__(self):
        self._ws: list[WebSocket] = []  # noqa: F821
        self._lock = asyncio.Lock()

    async def add(self, ws):
        async with self._lock:
            self._ws.append(ws)

    async def remove(self, ws):
        async with self._lock:
            self._ws = [w for w in self._ws if w is not ws]

    async def broadcast(self, msg: dict):
        if msg.get("type") == "agent":
            try:
                from db.client import record_event

                await asyncio.to_thread(
                    record_event, msg.get("job_id") or "__system__", _agent_event_action(msg)
                )
            except Exception:
                _log.warning("Failed to record agent event: job_id=%s", msg.get("job_id"))
        async with self._lock:
            snapshot = list(self._ws)
        dead = []
        for w in snapshot:
            try:
                await w.send_text(json.dumps(msg))
            except Exception:
                dead.append(w)
        if dead:
            async with self._lock:
                self._ws = [w for w in self._ws if not any(w is d for d in dead)]


cm = _CM()
