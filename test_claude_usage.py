# -*- coding: utf-8 -*-
"""
Tests of the tracker and of the local server.   python test_claude_usage.py   (or: python run.py tests)

- Offline tests: a simulated API response; checks the CSV / latest.js files and the ratio estimate.
- Server tests: the widget server answers, serves files, and refuses other hosts / origins.
- Live test (test_live_fetch): really queries the API if Claude Code credentials are present
  on this machine, and prints your values. Skipped otherwise.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import claude_usage as cu

T0 = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
R5 = "2026-10-22T12:00:00+00:00"
R7 = "2026-10-27T18:00:00.123456+00:00"


def payload(h5, d7, r5=R5, r7=R7):
    return {
        "five_hour": {"utilization": h5, "resets_at": r5},
        "seven_day": {"utilization": d7, "resets_at": r7},
        "seven_day_opus": None,
        "extra_usage": {"is_enabled": False},
    }


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def read_js_state(self):
        js = (self.dir / "latest.js").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("window.CLAUDE_USAGE = "))
        return json.loads(js[len("window.CLAUDE_USAGE = "):].rstrip().rstrip(";"))

    def test_reading_writes_csv_and_js(self):
        cu.run(self.dir, payload(12.0, 34.0), T0)
        row, err, _ = cu.run(self.dir, payload(15.0, 34.5), T0 + timedelta(minutes=10))
        self.assertIsNone(err)
        lines = (self.dir / "usage.csv").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(lines[0].split(","), cu.CSV_FIELDS)
        self.assertEqual(len(lines), 3)
        st = self.read_js_state()
        self.assertEqual(st["five_hour"]["pct"], 15.0)
        self.assertEqual(st["seven_day"]["pct"], 34.5)
        self.assertEqual(st["seven_day"]["resets_at"], "2026-10-27T18:00:00+00:00")
        self.assertEqual(len(st["history"]), 2)
        self.assertIsNone(st["error"])

    def test_ratio_estimated_inside_one_window(self):
        # 5h: 0 -> 40 %; 7d: 20 -> 24 %  => one full window costs 10 % of the week
        for i in range(5):
            cu.run(self.dir, payload(10.0 * i, 20.0 + i), T0 + timedelta(minutes=10 * i))
        self.assertAlmostEqual(self.read_js_state()["ratio_estimate"], 10.0)

    def test_ratio_ignores_resets(self):
        cu.run(self.dir, payload(80.0, 20.0), T0)
        # new 5-hour window: the drop 80 -> 5 must not count
        cu.run(self.dir, payload(5.0, 30.0, r5="2026-10-22T17:00:00+00:00"), T0 + timedelta(hours=5))
        st = self.read_js_state()
        self.assertIsNone(st["ratio_estimate"])
        self.assertEqual(st["ratio_default"], cu.DEFAULT_RATIO)

    def test_error_keeps_last_state_and_gives_a_code(self):
        cu.run(self.dir, payload(42.0, 50.0), T0)
        row, err, _ = cu.run(self.dir, {"other": 1}, T0 + timedelta(minutes=10))
        self.assertIsNone(row)
        self.assertIn("Unexpected response", err)
        st = self.read_js_state()
        self.assertEqual(st["five_hour"]["pct"], 42.0)
        self.assertEqual(st["error_code"], "unexpected_response")
        self.assertIn("Unexpected response", st["error"])

    def test_breakdown_per_product(self):
        p = payload(10.0, 20.0)
        p["seven_day_breakdown"] = {"as_of": R5, "rows": [
            {"key": "claude_code", "display_name": "Claude Code", "percent": 28},
            {"key": "chat", "display_name": "Chats", "percent": 72}]}
        cu.run(self.dir, p, T0)
        cu.run(self.dir, {"other": 1}, T0 + timedelta(minutes=10))   # failure: the breakdown is kept
        st = self.read_js_state()
        self.assertEqual([r["pct"] for r in st["breakdown"]["rows"]], [28.0, 72.0])
        self.assertEqual(st["breakdown"]["rows"][0]["name"], "Claude Code")

    def test_window_without_reset(self):
        row, err, _ = cu.run(self.dir, {"five_hour": {"utilization": 0, "resets_at": None},
                                         "seven_day": {"utilization": 3, "resets_at": R7}}, T0)
        self.assertIsNone(err)
        self.assertEqual(row["five_hour_resets_at"], "")

    def test_missing_credentials_has_a_stable_code(self):
        with tempfile.TemporaryDirectory() as empty, \
                mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": empty}):
            os.environ.pop("CLAUDE_USAGE_TOKEN", None)
            with self.assertRaises(cu.TrackerError) as cm:
                cu.read_token()
        self.assertEqual(cm.exception.code, "no_credentials")

    def test_token_from_environment(self):
        with mock.patch.dict(os.environ, {"CLAUDE_USAGE_TOKEN": "  abc  "}):
            self.assertEqual(cu.read_token(), "abc")


class ServerTests(unittest.TestCase):
    """The widget server answers, serves files, and refuses other hosts and origins."""

    @classmethod
    def setUpClass(cls):
        import threading
        import urllib.request
        import server
        cls.server = server
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def get(self, path):
        import urllib.error
        try:
            with self.opener.open(self.base + path, timeout=5) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            return e.code, "", b""

    def test_ping_and_files(self):
        code, _, body = self.get("/api/ping")
        self.assertEqual(code, 200)
        info = json.loads(body)
        self.assertEqual(info["app"], self.server.APP_ID)
        self.assertEqual(info["pid"], os.getpid())
        code, ctype, _ = self.get("/web/js/app.js")
        self.assertEqual(code, 200)
        self.assertIn("javascript", ctype)
        self.assertEqual(self.get("/web/index.html")[0], 200)

    def test_ping_helper_identifies_our_server(self):
        self.assertEqual(self.server.ping(self.port)["pid"], os.getpid())

    def test_root_redirect_keeps_the_language(self):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/?lang=fr")
        r = c.getresponse()
        self.assertEqual(r.status, 302)
        self.assertEqual(r.getheader("Location"), "/web/index.html?lang=fr")
        c.close()

    def test_no_escape_from_the_web_folder(self):
        self.assertEqual(self.get("/web/../claude_usage.py")[0], 404)
        self.assertEqual(self.get("/claude_usage.py")[0], 404)

    def test_refuses_a_hijacked_domain_name(self):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/data/latest.json", headers={"Host": "evil.example"})
        self.assertEqual(c.getresponse().status, 403)
        c.close()

    def test_refresh_refuses_other_origin(self):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(self.base + "/api/refresh", method="POST", headers={"Origin": "http://example.com"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.opener.open(req, timeout=5)
        self.assertEqual(cm.exception.code, 403)


class LiveTest(unittest.TestCase):
    def test_live_fetch(self):
        try:
            token = cu.read_token()
        except cu.TrackerError as e:
            self.skipTest(str(e))
        data = cu.fetch_usage(token)
        row = cu.build_row(data, cu.now_utc())
        print("\n--- Real values ---")
        print(" 5 hours:", row["five_hour_pct"], "%  resets", row["five_hour_resets_at"] or "-")
        print(" 7 days :", row["seven_day_pct"], "%  resets", row["seven_day_resets_at"] or "-")
        print(" response keys:", sorted(data))
        self.assertTrue(row["seven_day_pct"] != "" or row["five_hour_pct"] != "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
