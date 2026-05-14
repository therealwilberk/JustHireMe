from unittest import IsolatedAsyncioTestCase

from services.scanner import ScanManager


class TestScanManagerLifecycle(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mgr = ScanManager()

    async def test_start_scan_returns_status_dict(self):
        result = await self.mgr.start_scan()
        self.assertEqual(result, {"status": "scanning"})

    async def test_double_start_scan_raises_409(self):
        await self.mgr.start_scan()
        with self.assertRaises(Exception) as ctx:
            await self.mgr.start_scan()
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_stop_scan_when_idle(self):
        result = await self.mgr.stop_scan()
        self.assertEqual(result, {"status": "idle"})

    def test_is_scanning_false_initially(self):
        self.assertFalse(self.mgr.is_scanning())

    async def test_stop_reevaluate_when_idle(self):
        result = await self.mgr.stop_reevaluate()
        self.assertEqual(result, {"status": "idle"})

    async def test_ghost_lock_blocks_scan(self):
        await self.mgr._ghost_lock.acquire()
        with self.assertRaises(Exception) as ctx:
            await self.mgr.start_scan()
        self.assertEqual(ctx.exception.status_code, 409)
        self.mgr._ghost_lock.release()

    async def test_reevaluate_blocked_by_ghost_lock(self):
        await self.mgr._ghost_lock.acquire()
        with self.assertRaises(Exception) as ctx:
            await self.mgr.start_reevaluate()
        self.assertEqual(ctx.exception.status_code, 409)
        self.mgr._ghost_lock.release()
