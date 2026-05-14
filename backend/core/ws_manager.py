"""WebSocket connection manager for real-time event broadcasting.

Manages active WebSocket connections and broadcasts agent events
to all connected clients. Provides thread-safe registry operations
and automatic cleanup of stale connections.
"""

import asyncio
import json

from fastapi import WebSocket
from logger import get_logger

_log = get_logger(__name__)


def _agent_event_action(msg: dict) -> str:
    """Format an agent event message into a compact action string.

    Args:
        msg: The agent event dictionary containing 'event' and 'msg' keys.

    Returns:
        A formatted string like "event: detail" or just the event name.
    """
    event = str(msg.get("event") or "agent").strip() or "agent"
    detail = str(msg.get("msg") or "").strip()
    return f"{event}: {detail}" if detail else event


class _CM:
    """Connection manager registry with thread-safe broadcast.

    Maintains a list of active WebSocket connections protected by
    an asyncio lock to prevent race conditions on concurrent access.
    """

    def __init__(self) -> None:
        """Initialize an empty connection registry with an asyncio lock."""
        self._ws: list[WebSocket] = []  # noqa: F821
        self._lock = asyncio.Lock()

    async def add(self, ws: WebSocket) -> None:
        """Register a new WebSocket connection.

        Args:
            ws: The WebSocket connection to add to the registry.
        """
        async with self._lock:
            self._ws.append(ws)

    async def remove(self, ws: WebSocket) -> None:
        """Unregister a WebSocket connection.

        Args:
            ws: The WebSocket connection to remove from the registry.
        """
        async with self._lock:
            self._ws = [w for w in self._ws if w is not ws]

    async def broadcast(self, msg: dict) -> None:
        """Send a JSON message to all connected clients.

        Persists agent events to the database before broadcasting.
        Dead connections are automatically detected and removed.

        Args:
            msg: The message dictionary to serialize and broadcast.
        """
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
