"""Process ownership checks for the public local-service lifecycle helpers."""

import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "dev", Path(__file__).resolve().parents[1] / "scripts/dev.py"
)
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


class ServiceControlTests(unittest.TestCase):
    def test_stale_pid_record_never_stops_a_live_unrelated_process(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=True,
        )
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(
                dev, "STATE", Path(directory) / "services.json"
            ):
                state = {
                    "backend": {
                        "pid": process.pid,
                        "identity": "incorrect-start-time",
                        "port": 8000,
                    }
                }
                dev.stop_app("backend", state)
                self.assertIsNone(process.poll())
                self.assertEqual(state, {})
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_stop_only_terminates_the_recorded_owned_process_group(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=True,
        )
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(
                dev, "STATE", Path(directory) / "services.json"
            ):
                state = {
                    "backend": {
                        "pid": process.pid,
                        "identity": dev.identity(process.pid),
                        "port": 8000,
                    }
                }
                self.assertTrue(dev.owned(state["backend"]))
                dev.stop_app("backend", state)
                process.wait(timeout=5)
                self.assertIsNotNone(process.returncode)
                self.assertEqual(state, {})
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)

    def test_missing_identity_is_never_ownership(self):
        self.assertFalse(dev.owned({"pid": 2, "identity": None}))

    def test_occupied_port_is_refused_before_database_or_process_changes(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            with patch.object(dev, "require"), patch.object(
                dev, "ports", return_value={"backend": port, "frontend": port + 1}
            ), patch.object(dev, "read_state", return_value={}), patch.object(
                dev, "compose"
            ) as compose, patch.object(
                dev, "launch"
            ) as launch:
                with self.assertRaisesRegex(RuntimeError, "unmanaged process"):
                    dev.start()
                compose.assert_not_called()
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
