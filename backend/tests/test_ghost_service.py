from unittest import IsolatedAsyncioTestCase, mock

from services.ghost import GhostService
from services.scanner import ScanManager


class TestGhostServicePhases(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mgr = ScanManager()
        self.ghost = GhostService(self.mgr)

    @mock.patch("db.client.get_setting", return_value="false")
    @mock.patch("db.client.get_settings", return_value={})
    async def test_preflight_skips_when_ghost_off(self, _m1, _m2):
        result = await self.ghost._phase_preflight()
        self.assertIsNone(result)

    @mock.patch("services.ghost._job_targets", return_value=["board1"])
    @mock.patch("db.client.get_setting", return_value="true")
    @mock.patch("db.client.get_settings", return_value={})
    @mock.patch("services.ghost._profile_for_discovery", return_value={})
    @mock.patch("services.ghost._has_x_token", return_value=False)
    @mock.patch("services.ghost._free_sources_enabled", return_value=False)
    async def test_preflight_returns_cfg_profile_boards(self, *mocks):
        result = await self.ghost._phase_preflight()
        self.assertIsNotNone(result)
        cfg, profile, boards = result
        self.assertIsInstance(cfg, dict)
        self.assertIsInstance(boards, list)
        self.assertIn("board1", boards)
