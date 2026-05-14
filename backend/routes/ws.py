import asyncio
import json
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.config_constants import _log, _UP, _API_TOKEN
from core.ws_manager import cm

router = APIRouter(tags=["ws"])


async def _require_ws_token(ws: WebSocket) -> bool:
    """Auth guard for WebSocket routes; token via query param or header."""
    token = ws.query_params.get("token", "")
    if token == _API_TOKEN:
        return True
    auth = ws.headers.get("authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == _API_TOKEN:
        return True
    await ws.close(code=4401, reason="invalid token")
    return False


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    if not await _require_ws_token(ws):
        return
    await ws.accept()
    await cm.add(ws)
    beat = 0
    try:
        while True:
            beat += 1
            await ws.send_text(json.dumps({
                "type": "heartbeat", "status": "alive", "beat": beat,
                "uptime_seconds": round(time.monotonic() - _UP, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=2.0)
                if msg == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                _log.debug("ws ping timeout — expected")
    except WebSocketDisconnect:
        _log.debug("ws client disconnected")
    except Exception as exc:
        _log.warning("ws: %s", exc)
    finally:
        await cm.remove(ws)
