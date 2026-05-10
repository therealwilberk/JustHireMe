import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests.fakes import _install_storage_fakes

_install_storage_fakes()

from db.client import data_base


class DataBaseTests(unittest.TestCase):
    """data_base() resolves the app data directory via priority chain."""

    def test_jhm_app_data_dir_takes_priority(self):
        """JHM_APP_DATA_DIR env var is checked first."""
        with mock.patch.dict(os.environ, {"JHM_APP_DATA_DIR": "/custom/path"}, clear=False):
            result = data_base()
        self.assertEqual(result, "/custom/path")

    def test_xdg_data_home_used_on_linux_when_jhm_not_set(self):
        """On Linux, XDG_DATA_HOME is used when JHM_APP_DATA_DIR is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/xdg/data"}, clear=False):
                with mock.patch("sys.platform", "linux"):
                    result = data_base()
        self.assertEqual(result, "/xdg/data/JustHireMe")

    def test_localappdata_used_on_windows_when_jhm_not_set(self):
        """On Windows, LOCALAPPDATA is used when JHM_APP_DATA_DIR is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": R"C:\Users\test\AppData\Local"}, clear=False):
                with mock.patch("sys.platform", "win32"):
                    result = data_base()
        self.assertEqual(result, os.path.join(R"C:\Users\test\AppData\Local", "JustHireMe"))

    def test_fallback_to_home_when_no_env_var_set_on_windows(self):
        """Fallback to expanduser('~') on Windows when no relevant env vars."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.platform", "win32"):
                with mock.patch("os.path.expanduser", return_value="/home/user"):
                    result = data_base()
        self.assertEqual(result, "/home/user/JustHireMe")

    def test_fallback_to_xdg_default_on_linux_when_no_env_vars(self):
        """On Linux, fallback to ~/.local/share when XDG_DATA_HOME is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.platform", "linux"):
                with mock.patch("os.path.expanduser", return_value="/home/user/.local/share"):
                    result = data_base()
        self.assertEqual(result, "/home/user/.local/share/JustHireMe")


class EnsureDirTests(unittest.TestCase):
    """_ensure_dir fallback behaviour when os.makedirs fails."""

    def test_fallback_dir_used_when_makedirs_fails(self):
        """When os.makedirs raises, _ensure_dir tries a _store suffix fallback."""
        from db.client import _ensure_dir

        with mock.patch("os.makedirs", side_effect=[PermissionError("denied"), None]):
            result = _ensure_dir("/data/jhm")
        self.assertEqual(result, "/data/jhm_store")


class ChromiumExecutableTests(unittest.TestCase):
    """chromium_executable() resolves browser binary via priority chain."""

    def test_browser_env_var_resolved_via_path(self):
        """$BROWSER env var is checked first and resolved via shutil.which."""
        with mock.patch("shutil.which", return_value="/usr/bin/firefox"):
            with mock.patch.dict(os.environ, {"BROWSER": "firefox"}, clear=False):
                from agents.browser_runtime import chromium_executable
                result = chromium_executable()
        self.assertEqual(result, "/usr/bin/firefox")

    def test_browser_env_var_not_found_logs_warning(self):
        """When $BROWSER is set but shutil.which returns None, log warning."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch.dict(os.environ, {"BROWSER": "nonexistent"}, clear=False):
                with mock.patch("agents.browser_runtime._log.warning") as mock_warn:
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertIsNone(result)
        mock_warn.assert_called()

    def test_playwright_chromium_executable_env(self):
        """PLAYWRIGHT_CHROMIUM_EXECUTABLE is checked if $BROWSER not set."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch("os.path.exists", return_value=True):
                with mock.patch.dict(os.environ, {
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE": "/custom/chrome",
                }, clear=False):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertEqual(result, "/custom/chrome")

    def test_playwright_env_skipped_when_path_does_not_exist(self):
        """PLAYWRIGHT_CHROMIUM_EXECUTABLE is skipped if the file doesn't exist."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch("os.path.exists", return_value=False):
                with mock.patch.dict(os.environ, {
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE": "/missing/chrome",
                }, clear=False):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertIsNone(result)

    def test_linux_candidates_checked_via_shutil_which(self):
        """On Linux, common browser names are checked via shutil.which."""
        def fake_which(name):
            lookup = {
                "google-chrome": "/usr/bin/google-chrome",
                "chromium": None,
                "firefox": None,
            }
            return lookup.get(name)

        with mock.patch("shutil.which", side_effect=fake_which):
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("os.name", "posix"):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertEqual(result, "/usr/bin/google-chrome")

    def test_returns_none_when_no_browser_found(self):
        """When no browser is found through any path, return None."""
        with mock.patch("shutil.which", return_value=None):
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("os.name", "posix"):
                    from agents.browser_runtime import chromium_executable
                    result = chromium_executable()
        self.assertIsNone(result)
