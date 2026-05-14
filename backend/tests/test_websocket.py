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


class _ControlledWebSocket:
    """WebSocket with event-controlled send for deterministic timing.

    Allows tests to create explicit blocking windows:
    - block_next_send() makes send_text suspend until unblock_send()
    - fail_next_send() makes the next send raise
    - wait_until_blocked() waits until send_text is suspended
    """

    def __init__(self, name: str):
        self.name = name
        self.sent: list[str] = []
        self._should_block = False
        self._blocked = asyncio.Event()
        self._unblock = asyncio.Event()
        self._should_fail = False
        self._fail_exc: type[Exception] = ConnectionError

    def block_next_send(self):
        self._should_block = True
        self._blocked.clear()
        self._unblock.clear()

    def unblock_send(self):
        self._unblock.set()

    async def wait_until_blocked(self):
        await self._blocked.wait()

    def fail_next_send(self, exc: type[Exception] = ConnectionError):
        self._should_fail = True
        self._fail_exc = exc

    async def send_text(self, text: str):
        self.sent.append(text)
        if self._should_fail:
            self._should_fail = False
            raise self._fail_exc(f"{self.name} forced failure")
        if self._should_block:
            self._should_block = False
            self._blocked.set()
            await self._unblock.wait()


class _DisconnectingWebSocket:
    """WebSocket that disconnects after N successful sends."""

    def __init__(self, name: str, succeed_count: int = 1):
        self.name = name
        self._succeed_count = succeed_count
        self.send_count = 0

    async def send_text(self, text: str):
        self.send_count += 1
        if self.send_count > self._succeed_count:
            raise ConnectionError(f"{self.name} disconnected after {self.send_count} sends")
        return None


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


class TestCMControlledConcurrency(unittest.IsolatedAsyncioTestCase):
    """Deterministic concurrency via event-controlled WebSocket fakes.

    Uses _ControlledWebSocket to create explicit blocking windows in
    broadcast's send loop, allowing precise overlap of concurrent
    add/remove/broadcast operations without timing-based flakiness.
    """

    async def asyncSetUp(self):
        from main import _CM
        self.cm = _CM()

    async def test_concurrent_add_during_blocked_broadcast(self):
        """Adding a WebSocket during broadcast send phase must not
        corrupt the registry and the new socket is retained after."""
        ws1 = _MockWebSocket("ws1")
        controlled = _ControlledWebSocket("controlled")
        ws_late = _MockWebSocket("ws_late")
        await self.cm.add(ws1)
        await self.cm.add(controlled)

        controlled.block_next_send()

        async def bcast():
            await self.cm.broadcast({"type": "test"})

        async def add_late():
            await controlled.wait_until_blocked()
            await self.cm.add(ws_late)
            controlled.unblock_send()

        await asyncio.gather(bcast(), add_late())

        self.assertIn(ws_late, self.cm._ws, "late-added ws must be in registry")
        self.assertIn(ws1, self.cm._ws, "normal ws must remain")
        self.assertIn(controlled, self.cm._ws, "controlled ws must remain (no failure)")
        ws1.send_text.assert_awaited_once()
        self.assertEqual(controlled.sent, [json.dumps({"type": "test"})],
                         "controlled must have received broadcast")

    async def test_concurrent_remove_of_middle_during_blocked_broadcast(self):
        """Removing a socket from the registry during broadcast's send
        phase must not prevent broadcast from reaching later sockets
        (snapshot is independent), and the removed socket must be gone."""
        ws1 = _MockWebSocket("ws1")
        controlled = _ControlledWebSocket("controlled")
        ws3 = _MockWebSocket("ws3")
        await self.cm.add(ws1)
        await self.cm.add(controlled)
        await self.cm.add(ws3)

        controlled.block_next_send()

        async def bcast():
            await self.cm.broadcast({"type": "test"})

        async def remove_middle():
            await controlled.wait_until_blocked()
            await self.cm.remove(controlled)
            controlled.unblock_send()

        await asyncio.gather(bcast(), remove_middle())

        self.assertEqual(self.cm._ws, [ws1, ws3],
                         "controlled must be removed from registry")
        ws1.send_text.assert_awaited_once()
        ws3.send_text.assert_awaited_once()

    async def test_broadcast_snapshot_is_independent_of_concurrent_mutations(self):
        """Mutations to _ws during broadcast must not change which
        sockets the broadcast iterates over (it uses a snapshot copy)."""
        ws1 = _MockWebSocket("ws1")
        controlled = _ControlledWebSocket("controlled")
        ws_late = _MockWebSocket("ws_late")
        await self.cm.add(ws1)
        await self.cm.add(controlled)

        controlled.block_next_send()

        async def bcast():
            await self.cm.broadcast({"type": "test"})

        async def mutate_during_send():
            await controlled.wait_until_blocked()
            # Add and remove during broadcast send phase
            await self.cm.add(ws_late)
            await self.cm.remove(ws1)
            controlled.unblock_send()

        await asyncio.gather(bcast(), mutate_during_send())

        # ws_late was added after snapshot — not in snapshot, no message expected
        self.assertIn(ws_late, self.cm._ws, "late ws must be in final registry")
        # ws1 was in snapshot — received message despite being removed from _ws
        self.assertIn(json.dumps({"type": "test"}), ws1.send_text.call_args_list[0].args,
                      "ws1 must have received broadcast (was in snapshot)")
        # ws1 was removed from registry though
        self.assertNotIn(ws1, self.cm._ws, "ws1 was removed from registry")

    async def test_disconnecting_ws_removed_before_subsequent_broadcast(self):
        """A socket that disconnects mid-broadcast must be removed
        before the next broadcast starts."""
        ws1 = _MockWebSocket("ws1")
        disconnecting = _DisconnectingWebSocket("disconnecting", succeed_count=1)
        ws3 = _MockWebSocket("ws3")
        await self.cm.add(ws1)
        await self.cm.add(disconnecting)
        await self.cm.add(ws3)

        await self.cm.broadcast({"type": "first"})
        # disconnecting succeeds on first send, fails on second

        self.assertIn(disconnecting, self.cm._ws,
                      "disconnecting ws survives first broadcast (succeeds once)")

        await self.cm.broadcast({"type": "second"})
        # disconnecting fails on second send, should be removed

        self.assertNotIn(disconnecting, self.cm._ws,
                         "disconnecting ws must be removed after second broadcast")
        self.assertEqual(self.cm._ws, [ws1, ws3],
                         "only working sockets remain")

    async def test_disconnecting_ws_does_not_block_valid_sockets(self):
        """Valid sockets still receive messages when a peer disconnects
        during the same broadcast."""
        ws1 = _MockWebSocket("ws1")
        disconnecting = _DisconnectingWebSocket("disconnecting", succeed_count=0)
        ws3 = _MockWebSocket("ws3")
        await self.cm.add(ws1)
        await self.cm.add(disconnecting)
        await self.cm.add(ws3)

        await self.cm.broadcast({"type": "test"})

        ws1.send_text.assert_awaited_once()
        ws3.send_text.assert_awaited_once()
        self.assertEqual(self.cm._ws, [ws1, ws3],
                         "disconnecting ws removed, valid ones remain")

    async def test_concurrent_remove_of_dead_socket_is_safe(self):
        """If a concurrent remove removes a socket that broadcast also
        detected as dead, the double removal must not raise or corrupt
        the registry."""
        ws1 = _MockWebSocket("ws1")
        broken = _BrokenWebSocket("broken")
        controlled = _ControlledWebSocket("controlled")
        await self.cm.add(ws1)
        await self.cm.add(broken)
        await self.cm.add(controlled)

        controlled.block_next_send()

        async def bcast():
            await self.cm.broadcast({"type": "test"})

        async def remove_dead():
            await controlled.wait_until_blocked()
            # At this point broadcast's send to broken has already
            # failed; broken is in dead list.  Concurrently remove it.
            await self.cm.remove(broken)
            controlled.unblock_send()

        await asyncio.gather(bcast(), remove_dead())

        self.assertNotIn(broken, self.cm._ws,
                         "broken must be removed (by us or by broadcast)")
        self.assertEqual(self.cm._ws, [ws1, controlled],
                         "only working sockets remain")

    async def test_valid_clients_still_receive_during_dead_cleanup(self):
        """When multiple sockets fail in a broadcast, valid sockets
        must still receive their messages before cleanup occurs."""
        ws1 = _MockWebSocket("ws1")
        broken1 = _BrokenWebSocket("broken1")
        ws2 = _MockWebSocket("ws2")
        broken2 = _BrokenWebSocket("broken2")
        ws3 = _MockWebSocket("ws3")
        await self.cm.add(ws1)
        await self.cm.add(broken1)
        await self.cm.add(ws2)
        await self.cm.add(broken2)
        await self.cm.add(ws3)

        await self.cm.broadcast({"type": "test"})

        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()
        ws3.send_text.assert_awaited_once()
        self.assertEqual(self.cm._ws, [ws1, ws2, ws3],
                         "only broken sockets removed")

    async def test_high_contention_concurrent_ops(self):
        """Stress test: many concurrent adds, removes, and broadcasts."""
        ws_normal = _MockWebSocket("normal")
        ws_broken = _BrokenWebSocket("broken")
        await self.cm.add(ws_normal)
        await self.cm.add(ws_broken)

        async def add_broadcaster():
            local = _MockWebSocket(f"local_{id(object())}")
            await self.cm.add(local)
            await self.cm.broadcast({"type": "stress"})
            await self.cm.remove(local)
            return local

        async def remover():
            await self.cm.remove(ws_broken)

        async def plain_broadcaster():
            await self.cm.broadcast({"type": "stress"})

        tasks = [plain_broadcaster() for _ in range(5)]
        tasks += [add_broadcaster() for _ in range(5)]
        tasks += [remover() for _ in range(2)]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                self.fail(f"Unexpected exception: {r}")

        # Normal must survive; broken was removed (by remover or by broadcast dead cleanup)
        self.assertIn(ws_normal, self.cm._ws, "normal ws must survive")
        self.assertNotIn(ws_broken, self.cm._ws, "broken ws must be removed")

    async def test_three_way_race_add_remove_broadcast(self):
        """Add, remove, and broadcast all concurrent — registry must
        remain internally consistent: no duplicates, no missing entries."""
        base = _MockWebSocket("base")
        await self.cm.add(base)

        async def adder():
            for i in range(5):
                ws = _MockWebSocket(f"adder_{i}")
                await self.cm.add(ws)
                await asyncio.sleep(0)

        async def remover():
            for i in range(5):
                await self.cm.remove(base)
                await self.cm.add(base)
                await asyncio.sleep(0)

        async def broadcaster():
            for i in range(5):
                await self.cm.broadcast({"type": "stress", "n": i})
                await asyncio.sleep(0)

        await asyncio.gather(adder(), remover(), broadcaster())

        # base must be in the registry (remover always re-adds it)
        self.assertIn(base, self.cm._ws, "base must be in registry")
        # No duplicates: every ws appears exactly once
        self.assertEqual(len(self.cm._ws), len(set(id(w) for w in self.cm._ws)),
                         "no duplicate websockets in registry")
        # All adder-created sockets still present
        adder_sockets = [w for w in self.cm._ws if isinstance(w, _MockWebSocket)]
        self.assertEqual(len(adder_sockets), 6,
                         "base + 5 adder sockets = 6 total MockWebSockets")
