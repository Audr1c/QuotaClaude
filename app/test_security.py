# -*- coding: utf-8 -*-
"""SEC-2 / SEC-3: private data folder, exclusive port on Windows, safer pid check before stopping the server."""
import os
import stat
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import claude_usage as cu  # noqa: E402
import server  # noqa: E402
from launcher import app as launcher_app  # noqa: E402

NOW = cu.now_utc().replace(microsecond=0)
PAYLOAD = {"five_hour": {"utilization": 12.0, "resets_at": cu.iso(NOW + timedelta(hours=3))},
           "seven_day": {"utilization": 40.0, "resets_at": cu.iso(NOW + timedelta(days=2))}}


class DataDirTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX permissions only")
    def test_data_dir_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "data"
            d.mkdir(mode=0o755)
            os.chmod(d, 0o755)
            _, error, _ = cu.run(d, payload=PAYLOAD, now=NOW)
            self.assertIsNone(error)
            self.assertEqual(stat.S_IMODE(d.stat().st_mode), 0o700)


class ServerTests(unittest.TestCase):
    def test_plain_server_still_works(self):
        srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        srv.server_close()

    def test_exclusive_server_binds(self):
        srv = server.ExclusiveHTTPServer(("127.0.0.1", 0), server.Handler)
        srv.server_close()


class _Ui:
    def t(self, key, **kw):
        return f"{key}:{kw.get('msg', '')}"

    def say(self, key, **kw):
        pass


class StopServerTests(unittest.TestCase):
    def test_refuses_foreign_cmdline(self):
        with mock.patch.object(launcher_app, "ping", return_value={"pid": 4242}), \
                mock.patch.object(launcher_app.sys, "platform", "linux"), \
                mock.patch("builtins.open", mock.mock_open(read_data=b"/usr/bin/python3\0other.py\0")), \
                mock.patch.object(launcher_app.os, "kill") as kill, \
                mock.patch("builtins.print") as pr:
            self.assertFalse(launcher_app.stop_server(_Ui()))
        kill.assert_not_called()
        self.assertIn("stop.fail", pr.call_args[0][0])

    def test_refuses_bad_pids(self):
        for bad in (1, -5, "12", True, os.getpid()):
            with mock.patch.object(launcher_app, "ping", return_value={"pid": bad}), \
                    mock.patch.object(launcher_app.os, "kill") as kill, \
                    mock.patch("builtins.print"):
                self.assertFalse(launcher_app.stop_server(_Ui()), bad)
            kill.assert_not_called()

    def test_accepts_server_cmdline(self):
        pings = iter([{"pid": 4242}, None])
        with mock.patch.object(launcher_app, "ping", side_effect=lambda p: next(pings)), \
                mock.patch.object(launcher_app.sys, "platform", "linux"), \
                mock.patch("builtins.open", mock.mock_open(read_data=b"python3\0app/server.py\0")), \
                mock.patch.object(launcher_app.os, "kill") as kill:
            self.assertTrue(launcher_app.stop_server(_Ui()))
        kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
