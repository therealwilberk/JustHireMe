from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from logger import get_logger

_log = get_logger(__name__)

_RELEASE_DOWNLOAD_BASE = "https://github.com/vasu-devs/JustHireMe/releases/latest/download"


def browser_runtime_dir() -> Path:
    from config import settings

    configured = os.environ.get(settings.app.browser.runtime_dir) or os.environ.get(settings.app.browser.playwright_browsers_path)
    if configured:
        return Path(configured)
    if os.name == "nt":
        root = Path(os.environ.get(settings.app.app_data.localappdata) or Path.home() / "AppData" / "Local")
    elif sys_platform() == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get(settings.app.app_data.xdg_data_home) or Path.home() / ".local" / "share")
    return root / "JustHireMe" / "browser-runtime" / "ms-playwright"


def sys_platform() -> str:
    return platform.system().lower()


def browser_runtime_asset_name() -> str:
    system = sys_platform()
    if system == "windows":
        return "JustHireMe-browser-runtime-windows.zip"
    if system == "darwin":
        return "JustHireMe-browser-runtime-macos.zip"
    return "JustHireMe-browser-runtime-linux.zip"


def browser_runtime_url() -> str:
    from config import settings

    return os.environ.get(
        settings.app.browser.runtime_url,
        f"{_RELEASE_DOWNLOAD_BASE}/{browser_runtime_asset_name()}",
    )


def chromium_executable() -> str | None:
    from config import settings

    env_browser = os.environ.get(settings.app.browser.browser)
    if env_browser:
        resolved = shutil.which(env_browser)
        if resolved:
            return resolved
        _log.warning("$BROWSER set to '%s' but binary not found in PATH", env_browser)

    pw_exe = os.environ.get(settings.app.browser.playwright_chromium_executable)
    if pw_exe and os.path.exists(pw_exe):
        return pw_exe

    if os.name == "nt":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
    else:
        for name in [
            "google-chrome", "google-chrome-stable",
            "chromium", "chromium-browser",
            "firefox", "firefox-esr",
            "brave-browser", "brave",
        ]:
            resolved = shutil.which(name)
            if resolved:
                return resolved

    _log.warning("no browser found — set $BROWSER or install Chrome/Firefox/Brave")
    return None


def browser_runtime_ready(path: Path | None = None) -> bool:
    root = path or browser_runtime_dir()
    if not root.exists():
        return False
    return any(candidate.name.lower().startswith("chromium") for candidate in root.iterdir() if candidate.is_dir())


def ensure_browser_runtime() -> Path:
    runtime_dir = browser_runtime_dir()
    if browser_runtime_ready(runtime_dir):
        return runtime_dir

    runtime_dir.parent.mkdir(parents=True, exist_ok=True)
    url = browser_runtime_url()
    with tempfile.TemporaryDirectory(prefix="jhm-browser-runtime-") as tmp:
        archive_path = Path(tmp) / browser_runtime_asset_name()
        try:
            urllib.request.urlretrieve(url, archive_path)
            extract_dir = Path(tmp) / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_dir)
        except Exception as exc:
            raise RuntimeError(
                "Playwright Chromium is not installed yet and the optional browser runtime "
                f"could not be downloaded from {url}. Connect to the internet and retry browser automation."
            ) from exc

        extracted_runtime = extract_dir / "ms-playwright"
        if not extracted_runtime.exists():
            nested = next(extract_dir.glob("**/ms-playwright"), None)
            if nested:
                extracted_runtime = nested
        if not extracted_runtime.exists():
            raise RuntimeError("Downloaded browser runtime archive did not contain ms-playwright.")

        if runtime_dir.exists():
            shutil.rmtree(runtime_dir)
        shutil.copytree(extracted_runtime, runtime_dir)

    if not browser_runtime_ready(runtime_dir):
        raise RuntimeError("Browser runtime installation finished, but Chromium was not found.")
    return runtime_dir


async def launch_chromium(playwright, *, headless: bool = True, **kwargs):
    try:
        return await playwright.chromium.launch(headless=headless, **kwargs)
    except Exception as exc:
        message = str(exc).lower()
        if "executable" in message or "chromium" in message or "browser" in message:
            executable = chromium_executable()
            if executable:
                return await playwright.chromium.launch(
                    headless=headless,
                    executable_path=executable,
                    **kwargs,
                )
            runtime_dir = ensure_browser_runtime()
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(runtime_dir)
            return await playwright.chromium.launch(headless=headless, **kwargs)

        executable = chromium_executable()
        if not executable:
            raise
        return await playwright.chromium.launch(
            headless=headless,
            executable_path=executable,
            **kwargs,
        )
