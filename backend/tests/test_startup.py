import socket
import subprocess
import sys
import unittest
from pathlib import Path


class TestStartup(unittest.TestCase):
    """Smoke tests that verify main.py can start as __main__."""

    def test_main_emits_token_and_port(self):
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "main.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={"PYTHONUNBUFFERED": "1"},
        )
        lines = []
        try:
            while len(lines) < 5:
                line = proc.stdout.readline()
                if not line:
                    break
                lines.append(line.strip())
                if any(l.startswith("JHM_TOKEN=") for l in lines) and any(l.startswith("PORT:") for l in lines):
                    break
        finally:
            proc.kill()
            proc.wait()

        token_line = next((l for l in lines if l.startswith("JHM_TOKEN=")), None)
        port_line = next((l for l in lines if l.startswith("PORT:")), None)
        self.assertIsNotNone(token_line, f"No JHM_TOKEN= in stdout:\n" + "\n".join(lines))
        self.assertIsNotNone(port_line, f"No PORT: in stdout:\n" + "\n".join(lines))
        token = token_line.split("=", 1)[1]
        port_str = port_line.split(":", 1)[1]
        self.assertEqual(len(token), 64, f"Expected 64-char hex token, got {len(token)} chars")
        port = int(port_str)
        self.assertGreater(port, 0)
        self.assertLess(port, 65536)

    def test_port_not_released_before_uvicorn_binds(self):
        """Verify the port stays bound (no TOCTOU race). Binding to the
        same port immediately after _bind_port() should fail (address in use)."""
        from main import _bind_port

        sock = _bind_port()
        port = sock.getsockname()[1]
        try:
            thief = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            with self.assertRaises(OSError):
                thief.bind(("127.0.0.1", port))
        finally:
            sock.close()
