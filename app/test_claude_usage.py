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

    def test_breakdown_split_by_local_day_per_product(self):
        def p(d7, shares):
            out = payload(5.0, d7)
            if shares:
                out["seven_day_breakdown"] = {"rows": [{"key": k, "display_name": k, "percent": v} for k, v in shares.items()]}
            return out
        local = lambda day, hour: datetime(2026, 10, day, hour, 0).astimezone()
        cu.run(self.dir, p(10.0, {"code": 100, "chat": 0}), local(21, 9))      # first record: 10 pts of Code so far
        cu.run(self.dir, p(20.0, {"code": 100, "chat": 0}), local(21, 18))     # Wednesday: Code only (+10)
        cu.run(self.dir, p(30.0, None), local(22, 9))                          # week % known, products not
        _, _, st = cu.run(self.dir, p(40.0, {"code": 50, "chat": 50}), local(22, 18))   # Thursday: Chats only (+20)
        days = {r["key"]: r["days"] for r in st["breakdown"]["rows"]}
        self.assertEqual(days["chat"], [{"day": "2026-10-22", "pts": 20.0}])
        self.assertEqual(days["code"][-1], {"day": "2026-10-21", "pts": 10.0 if days["code"][0]["day"] is None else 20.0})
        self.assertEqual(sum(g["pts"] for g in days["code"]), 20.0)
        self.assertNotIn("2026-10-22", [g["day"] for g in days["code"]])
        lines = (self.dir / "breakdown.csv").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1 + 6)                       # header + 2 products x 3 records
        cu.run(self.dir, p(40.0, {"code": 50, "chat": 50}), local(22, 19))
        self.assertEqual(len((self.dir / "breakdown.csv").read_text(encoding="utf-8").strip().splitlines()), 7)  # unchanged: not recorded

    def test_csv_open_in_a_spreadsheet(self):
        # breakdown.csv locked (LibreOffice/Excel): the reading still succeeds
        with mock.patch.object(cu, "append_breakdown", side_effect=PermissionError(13, "Permission denied")):
            p = payload(10.0, 20.0)
            p["seven_day_breakdown"] = {"rows": [{"key": "chat", "display_name": "Chats", "percent": 100}]}
            row, err, _ = cu.run(self.dir, p, T0)
        self.assertIsNone(err)
        self.assertIn("breakdown.csv is open", (self.dir / "tracker.log").read_text(encoding="utf-8"))
        # usage.csv locked: a clear error code instead of a crash
        with mock.patch.object(cu, "append_csv", side_effect=PermissionError(13, "Permission denied")):
            _, err, st = cu.run(self.dir, payload(11.0, 20.0), T0 + timedelta(minutes=1))
        self.assertEqual(st["error_code"], "file_locked")

    def test_history_drops_repeated_values(self):
        for i, v in enumerate((10.0, 10.0, 10.0, 12.0, 12.0)):
            cu.run(self.dir, payload(v, 30.0), T0 + timedelta(minutes=i))
        self.assertEqual([h["h5"] for h in self.read_js_state()["history"]], [10.0, 12.0, 12.0])

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

    def test_expired_token_is_refused_without_calling_the_api(self):
        def creds(folder, expires):
            (Path(folder) / ".credentials.json").write_text(json.dumps(
                {"claudeAiOauth": {"accessToken": "tok", "expiresAt": int(expires.timestamp() * 1000)}}), encoding="utf-8")
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": home}):
            os.environ.pop("CLAUDE_USAGE_TOKEN", None)
            creds(home, cu.now_utc() + timedelta(hours=1))
            self.assertEqual(cu.read_token(), "tok")
            creds(home, cu.now_utc() - timedelta(minutes=5))
            with mock.patch("urllib.request.urlopen") as net:
                _, err, st = cu.run(self.dir)
            net.assert_not_called()
            self.assertEqual(st["error_code"], "token_expired")
            self.assertTrue(st["diagnostics"]["last"]["expires_at"])
            self.assertEqual(st["token_expires_at"], st["diagnostics"]["last"]["expires_at"])

    def test_token_from_environment(self):
        with mock.patch.dict(os.environ, {"CLAUDE_USAGE_TOKEN": "  abc  "}):
            self.assertEqual(cu.read_token(), "abc")


class DiagnosticTests(unittest.TestCase):
    def _http_error(self, code, body, headers=None):
        import io, urllib.error, email.message
        h = email.message.Message()
        for k, v in (headers or {}).items():
            h[k] = v
        return urllib.error.HTTPError(cu.API_URL, code, "Too Many Requests", h, io.BytesIO(body.encode()))

    def test_429_is_recorded_with_details_and_streak(self):
        body = '{"error":{"type":"rate_limit_error","message":"Rate limited. Please try again later."}}'
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(cu, "read_token", return_value="x"), \
             mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: (_ for _ in ()).throw(
                 self._http_error(429, body, {"Retry-After": "60", "request-id": "req_1"}))):
            _, err, state = cu.run(Path(d))
            _, err, state = cu.run(Path(d))
            self.assertEqual(state["error_code"], "rate_limited")
            diag = state["diagnostics"]
            self.assertEqual(diag["consecutive"], 2)
            self.assertEqual(diag["last"]["status"], 429)
            self.assertEqual(diag["last"]["retry_after"], "60")
            self.assertEqual(diag["last"]["api_type"], "rate_limit_error")
            self.assertEqual(len(diag["recent"]), 2)
            self.assertIn("429", (Path(d) / "tracker.log").read_text())

    def test_success_resets_streak(self):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            cu.record_diagnostic(dd, cu.now_utc(), cu.TrackerError("http", "boom", {"status": 500}))
            self.assertEqual(cu.record_diagnostic(dd, cu.now_utc(), None)["consecutive"], 0)


class PollerTests(unittest.TestCase):
    def test_ladder(self):
        import poller
        top = len(poller.LADDER_S) - 1
        self.assertEqual(poller.next_delay(top, True, None)[:2], (30, 0))          # a change: 30 s
        delays, step = [], 0
        for _ in range(7):                                                         # then no change: climb, stay at 10 min
            d, step, reason = poller.next_delay(step, False, None)
            delays.append(d)
        self.assertEqual(delays, [60, 180, 300, 420, 600, 600, 600])
        self.assertEqual(reason, "unchanged")

    def test_rate_limited_waits_two_minutes_or_retry_after(self):
        import poller
        self.assertEqual(poller.next_delay(2, False, "rate_limited"), (120, 2, "rate_limited"))
        self.assertEqual(poller.next_delay(2, False, "rate_limited", "300")[0], 300)
        self.assertEqual(poller.next_delay(2, False, "network")[:2], (300, 3))      # other errors: like no change

    def test_single_instance(self):
        import poller
        with tempfile.TemporaryDirectory() as d:
            lock = poller.acquire_lock(Path(d))
            self.assertIsNotNone(lock)
            poller.write_state(Path(d), pid=123)
            self.assertEqual(poller.running(Path(d)), {"pid": 123})
            lock.close()
            self.assertIsNone(poller.running(Path(d)))


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
