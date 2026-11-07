# -*- coding: utf-8 -*-
"""HUB-1: a PC pushes its readings to a hub; with an API token, every request to the hub needs it."""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import claude_usage as cu  # noqa: E402
import hub  # noqa: E402

NOW = cu.now_utc().replace(microsecond=0)
PAYLOAD = {"five_hour": {"utilization": 12.0, "resets_at": cu.iso(NOW + timedelta(hours=3))},
           "seven_day": {"utilization": 40.0, "resets_at": cu.iso(NOW + timedelta(days=2))}}


def row(ts, h5="10", d7="30"):
    return {"timestamp": cu.iso(ts), "five_hour_pct": h5, "five_hour_resets_at": cu.iso(NOW + timedelta(hours=2)),
            "seven_day_pct": d7, "seven_day_resets_at": cu.iso(NOW + timedelta(days=2)),
            "seven_day_opus_pct": "", "seven_day_sonnet_pct": ""}


class ReceiveTests(unittest.TestCase):
    def test_rows_are_checked_field_by_field(self):
        for bad in (None, [], {"timestamp": "x"}, dict(row(NOW), extra="1"), dict(row(NOW), five_hour_pct="abc"),
                    dict(row(NOW), seven_day_pct="5000"), dict(row(NOW), five_hour_resets_at="soon"),
                    dict(row(NOW), five_hour_pct="", seven_day_pct="")):
            with self.assertRaises(ValueError, msg=bad):
                hub.clean_row(bad)
        self.assertEqual(hub.clean_row(dict(row(NOW), five_hour_pct="12.50"))["five_hour_pct"], "12.5")

    def test_a_reading_is_stored_once(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(cu, "token_expiry", lambda: None):
            d = Path(d)
            self.assertEqual(hub.receive(d, {"row": row(NOW)}), {"added": True, "samples": 1})
            self.assertEqual(hub.receive(d, {"row": row(NOW)}), {"added": False, "samples": 1})
            self.assertTrue(hub.receive(d, {"row": row(NOW + timedelta(minutes=1))})["added"])
            self.assertEqual(json.loads((d / "latest.json").read_text())["samples"], 2)

    def test_token_file_is_private_and_stable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "api_token"
            a = hub.ensure_token(p)
            self.assertEqual(a, hub.ensure_token(p))
            self.assertGreaterEqual(len(a), 40)
            if os.name != "nt":
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)
        self.assertFalse(hub.same_token(None, a))
        self.assertFalse(hub.same_token(a[:-1], a))


class HubServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server = server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.hub_dir = Path(cls.tmp.name) / "hub"
        cls.pc_dir = Path(cls.tmp.name) / "pc"
        cls.hub_dir.mkdir()
        cls.pc_dir.mkdir()
        cls.patches = [mock.patch.object(cu, "DATA_DIR", cls.hub_dir), mock.patch.object(cu, "token_expiry", lambda: None)]
        for p in cls.patches:
            p.start()
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.srv.api_token = hub.ensure_token(cls.hub_dir / "api_token")
        cls.srv.allowed_hosts = ("nas.example.ts.net",)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def setUp(self):
        self.server._reading_posts.clear()

    def request(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, r, data

    def auth(self, extra=None):
        return dict({"Authorization": "Bearer " + self.srv.api_token}, **(extra or {}))

    def test_every_request_needs_the_token(self):
        self.assertEqual(self.request("GET", "/web/index.html")[0], 401)
        self.assertEqual(self.request("GET", "/api/v1/config", headers={"Authorization": "Bearer nope"})[0], 401)
        self.assertEqual(self.request("GET", "/api/v1/config", headers=self.auth())[0], 200)
        self.assertEqual(self.request("GET", "/api/ping")[0], 200)              # the launcher, from this machine
        self.assertEqual(self.request("POST", "/api/v1/config", "{}", {"Origin": f"http://127.0.0.1:{self.port}"})[0], 401)

    def test_a_browser_gets_a_cookie_from_the_token_in_the_address(self):
        st, r, _ = self.request("GET", "/?token=" + self.srv.api_token)
        self.assertEqual(st, 302)
        self.assertEqual(r.getheader("Location"), "/web/index.html")
        cookie = r.getheader("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertEqual(self.request("GET", "/web/index.html", headers={"Cookie": cookie.split(";")[0]})[0], 200)
        self.assertEqual(self.request("GET", "/?token=wrong")[0], 401)

    def test_extra_host_names_are_accepted(self):
        self.assertEqual(self.request("GET", "/api/v1/config", headers=self.auth({"Host": f"nas.example.ts.net:{self.port}"}))[0], 200)
        self.assertEqual(self.request("GET", "/api/v1/config", headers=self.auth({"Host": "evil.example"}))[0], 403)

    def test_pushed_readings_land_on_the_hub(self):
        body = json.dumps({"row": row(NOW - timedelta(minutes=5))})
        self.assertEqual(self.request("POST", "/api/readings", body, {"Content-Type": "application/json"})[0], 401)
        st, _, data = self.request("POST", "/api/readings", body, self.auth({"Content-Type": "application/json"}))
        self.assertEqual((st, json.loads(data)["added"]), (200, True))
        self.assertFalse(json.loads(self.request("POST", "/api/readings", body, self.auth())[2])["added"])
        self.assertEqual(self.request("POST", "/api/readings", '{"row": {"timestamp": 1}}', self.auth())[0], 400)

    def test_the_pc_pushes_after_each_reading(self):
        (self.pc_dir / "config.json").write_text(json.dumps({"hub": {"url": f"http://127.0.0.1:{self.port}"}}))
        (self.pc_dir / "hub_token").write_text(self.srv.api_token + "\n")
        row_, error, _ = cu.run(self.pc_dir, payload=PAYLOAD, now=NOW)
        self.assertIsNone(error)
        stored = [r["timestamp"] for r in cu.load_history(self.hub_dir / "usage.csv")]
        self.assertIn(row_["timestamp"], stored)
        # a hub that is down never breaks the reading on the PC
        (self.pc_dir / "config.json").write_text(json.dumps({"hub": {"url": "http://127.0.0.1:9"}}))
        _, error, _ = cu.run(self.pc_dir, payload=PAYLOAD, now=NOW + timedelta(minutes=1))
        self.assertIsNone(error)
        self.assertIn("hub push failed", (self.pc_dir / "tracker.log").read_text())


class BindTests(unittest.TestCase):
    def test_no_network_address_without_a_token(self):
        r = subprocess.run([sys.executable, str(ROOT / "server.py"), "--bind", "0.0.0.0", "--port", "0"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2)
        self.assertIn("without --token-file", r.stdout)


if __name__ == "__main__":
    unittest.main()
