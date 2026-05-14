"""Tests for _CM WebSocket connection manager.

Tests the async-safety contract: add/remove/broadcast must be safe
under concurrent coroutine execution. Uses mock WebSocket objects
to avoid requiring the full ASGI stack.
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock


class _MockWebSocket:
    """Minimal WebSocket-like object for testing _CM."""

    def __init__(self, name: str):
        self.name = name
        self.send_text = AsyncMock()
        self.send_text.side_effect = None


class _BrokenWebSocket(_MockWebSocket):
    """A WebSocket whose send_text always raises."""

    def __init__(self, name: str, exc: type[Exception] = ConnectionError):
        super().__init__(name)
        self.send_text = AsyncMock(side_effect=exc(f"{name} broken"))


class TestCMAddRemoveBroadcast(unittest.IsolatedAsyncioTestCase):
    """Basic operations — single-coroutine correctness."""

    async def asyncSetUp(self):
        # Import _CM after fakes installed (shouldn't need fakes, but
        # importing from main.py may pull in heavy deps). We test _CM
        # in isolation by reading the source class directly.
        from main import _CM
        self.cm = _CM()

    async def test_add_and_broadcast_delivers_to_all(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        msg = {"type": "heartbeat", "beat": 1}
        await self.cm.broadcast(msg)
        expected = json.dumps(msg)
        ws1.send_text.assert_awaited_once_with(expected)
        ws2.send_text.assert_awaited_once_with(expected)

    async def test_remove_takes_ws_out_of_broadcast(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        await self.cm.remove(ws1)
        msg = {"type": "test"}
        await self.cm.broadcast(msg)
        ws1.send_text.assert_not_awaited()
        ws2.send_text.assert_awaited_once()

    async def test_remove_does_not_affect_other_connections(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        await self.cm.remove(ws1)
        self.assertEqual(self.cm._ws, [ws2])

    async def test_broadcast_empty_registry_does_not_raise(self):
        msg = {"type": "test"}
        await self.cm.broadcast(msg)

    async def test_remove_absent_ws_does_not_raise(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.remove(ws2)
        self.assertEqual(self.cm._ws, [ws1])

    async def test_broadcast_removes_dead_connections(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _BrokenWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        msg = {"type": "test"}
        await self.cm.broadcast(msg)
        # ws2 should be removed after broadcast failure
        self.assertEqual(self.cm._ws, [ws1])

    async def test_broadcast_all_dead_empties_registry(self):
        ws1 = _BrokenWebSocket("ws1")
        ws2 = _BrokenWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        msg = {"type": "test"}
        await self.cm.broadcast(msg)
        self.assertEqual(self.cm._ws, [])

    async def test_remove_uses_identity_not_equality(self):
        class _EqAlwaysTrue(_MockWebSocket):
            def __eq__(self, other):
                return True
        ws1 = _EqAlwaysTrue("ws1")
        ws2 = _EqAlwaysTrue("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        await self.cm.remove(ws1)
        # Should remove only ws1 (identity), not ws2
        self.assertEqual(self.cm._ws, [ws2])


class TestCMConcurrency(unittest.IsolatedAsyncioTestCase):
    """Concurrent operations — overlapping add/remove/broadcast."""

    async def asyncSetUp(self):
        from main import _CM
        self.cm = _CM()

    async def test_concurrent_add_does_not_duplicate(self):
        async def add_ws(ws):
            await self.cm.add(ws)
        wss = [_MockWebSocket(f"ws{i}") for i in range(10)]
        await asyncio.gather(*[add_ws(ws) for ws in wss])
        self.assertEqual(len(self.cm._ws), 10)

    async def test_concurrent_add_and_remove(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        await self.cm.add(ws1)
        async def remover():
            await self.cm.remove(ws1)
        async def adder():
            await self.cm.add(ws2)
        await asyncio.gather(remover(), adder())
        self.assertEqual(self.cm._ws, [ws2])

    async def test_concurrent_broadcast_and_remove(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        async def broadcaster():
            await self.cm.broadcast({"type": "test"})
        async def remover():
            await self.cm.remove(ws1)
        await asyncio.gather(broadcaster(), remover())
        ws1.send_text.assert_awaited()  # may or may not receive (race)

    async def test_concurrent_broadcasts_do_not_miss_messages(self):
        ws = _MockWebSocket("ws")
        await self.cm.add(ws)
        async def bcast(n):
            await self.cm.broadcast({"type": "test", "n": n})
        await asyncio.gather(*[bcast(i) for i in range(5)])
        self.assertEqual(ws.send_text.await_count, 5)

    async def test_concurrent_remove_identity_is_safe(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        ws3 = _MockWebSocket("ws3")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        await self.cm.add(ws3)
        async def remove_all():
            await asyncio.gather(
                self.cm.remove(ws1),
                self.cm.remove(ws2),
                self.cm.remove(ws3),
            )
        await remove_all()
        self.assertEqual(self.cm._ws, [])

    async def test_dead_removal_from_one_broadcast_does_not_affect_another(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _BrokenWebSocket("ws2")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        async def bcast():
            await self.cm.broadcast({"type": "test"})
        await asyncio.gather(bcast(), bcast())
        # ws2 should be removed by first broadcast; second sees [ws1]
        self.assertEqual(self.cm._ws, [ws1])
        ws1.send_text.assert_awaited()

    async def test_add_after_remove_maintains_order(self):
        ws1 = _MockWebSocket("ws1")
        ws2 = _MockWebSocket("ws2")
        ws3 = _MockWebSocket("ws3")
        await self.cm.add(ws1)
        await self.cm.add(ws2)
        await self.cm.remove(ws1)
        await self.cm.add(ws3)
        self.assertEqual(self.cm._ws, [ws2, ws3])
