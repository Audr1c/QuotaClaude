# -*- coding: utf-8 -*-
"""API-1 / API-2: the data contract (schema/latest.v1.json), the /api/v1 routes, the shared settings, and the
server-side model (model.py) giving the same numbers as the widget's web/js/model.js."""
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import claude_usage as cu  # noqa: E402
import settings  # noqa: E402

SAMPLE = ROOT / "schema" / "latest.v1.json"


def synthetic_rows(now: datetime, days: int = 9) -> list[dict]:
    """Readings every 30 min over `days` days, active from 09:00 to 19:00 UTC, with one weekly reset."""
    rows, d7, h5, r5 = [], 0.0, 0.0, None
    reset7 = now - timedelta(days=days) + timedelta(days=2, hours=5)
    t = now - timedelta(days=days)
    while t <= now:
        if t >= reset7:
            reset7, d7 = reset7 + timedelta(days=7), 0.0
        if r5 is not None and t >= r5:
            r5, h5 = None, 0.0
        if 9 <= t.hour < 19:
            r5 = r5 or t + timedelta(hours=5)
            h5, d7 = min(100.0, h5 + 3), min(100.0, d7 + 0.4)
        rows.append({"timestamp": cu.iso(t), "five_hour_pct": f"{round(h5):g}", "five_hour_resets_at": cu.iso(r5) if r5 else "",
                     "seven_day_pct": f"{round(d7):g}", "seven_day_resets_at": cu.iso(reset7),
                     "seven_day_opus_pct": "", "seven_day_sonnet_pct": ""})
        t += timedelta(minutes=30)
    return rows


class ContractTests(unittest.TestCase):
    def test_latest_json_has_the_shape_of_the_sample(self):
        sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
        now = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(cu, "token_expiry", lambda: None):
            state = cu.write_outputs(Path(d), synthetic_rows(now, 3), now, None)
        self.assertEqual(state["schema"], 1)
        self.assertEqual(sample["schema"], cu.SCHEMA)
        self.assertEqual(sorted(state), sorted(sample), "latest.json keys changed: update schema/latest.v1.json and SCHEMA")
        for key in ("five_hour", "seven_day"):
            self.assertEqual(sorted(state[key]), sorted(sample[key]))
        self.assertEqual(sorted(state["history"][0]), sorted(sample["history"][0]))


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ModelParityTests(unittest.TestCase):
    """model.py is a port of web/js/model.js: same numbers, also across a daylight-saving change."""

    KEYS = {"five": ("used", "pace", "limit", "weekPace", "maxRate", "paceRate", "left"),
            "seven": ("used", "pace", "limit", "dailyBudget", "todayLeft", "todayUsed", "sessionsLeft", "startUsed",
                      "daysLeft", "ratePerHour", "remaining")}
    JS = """
      global.window = global; global.localStorage = { getItem() { return null; }, setItem() {} };
      global.document = { documentElement: {}, querySelectorAll() { return []; }, addEventListener() {} };
      global.navigator = { language: "en" };
      require(process.argv[1] + "/web/js/model.js");      // node -e <script> <root> <input.json>
      const { D, cases } = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
      console.log(JSON.stringify(cases.map(([now, h]) => CU.compute(D, now, { hoursPerDay: h }))));
    """
    PY = """
import json, sys
sys.path.insert(0, sys.argv[1])
import model
inp = json.load(sys.stdin)
print(json.dumps([model.compute(inp["D"], now, h) for now, h in inp["cases"]]))
"""

    def run_both(self, D, cases, tz):
        env = dict(os.environ, TZ=tz)
        payload = json.dumps({"D": D, "cases": cases})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write(payload)
        try:
            js = subprocess.run(["node", "-e", self.JS, str(ROOT), fh.name],
                                capture_output=True, text=True, timeout=60, env=env)
            py = subprocess.run([sys.executable, "-c", self.PY, str(ROOT)], input=payload, capture_output=True, text=True,
                                timeout=60, env=env)
        finally:
            os.unlink(fh.name)
        self.assertEqual(js.returncode, 0, js.stderr)
        self.assertEqual(py.returncode, 0, py.stderr)
        return json.loads(js.stdout), json.loads(py.stdout)

    def test_same_numbers_as_the_widget(self):
        # Paris switches to winter time on 2026-10-25: the history crosses it
        now = datetime(2026, 10, 27, 14, 20, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(cu, "token_expiry", lambda: None):
            D = cu.write_outputs(Path(d), synthetic_rows(now), now, None)
        base = now.timestamp() * 1000
        cases = [[base + k * 3600e3, h] for k in (0, 3, 7) for h in (24, 8, 5)]
        for tz in ("Europe/Paris", "America/New_York", "UTC"):
            js, py = self.run_both(D, cases, tz)
            for (now_ms, h), a, b in zip(cases, js, py):
                for part, keys in self.KEYS.items():
                    for k in keys:
                        x, y = a[part][k], b[part][k]
                        if x is None or y is None:
                            self.assertEqual(x, y, f"{tz} {part}.{k} h={h}")
                        else:
                            self.assertAlmostEqual(x, y, places=6, msg=f"{tz} {part}.{k} h={h}")


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server = server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.tmp.name)
        cls.patch = mock.patch.object(cu, "DATA_DIR", cls.data)
        cls.patch.start()
        now = cu.now_utc()
        rows = synthetic_rows(now, 3)
        for r in rows:
            cu.append_csv(cls.data / "usage.csv", r)
        with mock.patch.object(cu, "token_expiry", lambda: None):
            state = cu.write_outputs(cls.data, rows, now, None)
        state["tokens"] = json.loads(SAMPLE.read_text(encoding="utf-8"))["tokens"]
        (cls.data / "latest.json").write_text(json.dumps(state), encoding="utf-8")
        (cls.data / "config.json").write_text(json.dumps({"lang": "fr", "setup_done": True}), encoding="utf-8")
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.patch.stop()
        cls.tmp.cleanup()

    def setUp(self):
        self.server._config_posts.clear()

    def request(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        try:
            return r.status, json.loads(data)
        except ValueError:
            return r.status, None

    def post_config(self, obj, origin=True):
        h = {"Content-Type": "application/json"}
        if origin:
            h["Origin"] = f"http://127.0.0.1:{self.port}"
        return self.request("POST", "/api/v1/config", json.dumps(obj), h)

    def test_read_routes(self):
        st, latest = self.request("GET", "/api/v1/latest")
        self.assertEqual((st, latest["schema"]), (200, 1))
        st, hist = self.request("GET", "/api/v1/history")
        self.assertEqual(st, 200)
        all_n = len(hist["readings"])
        since = hist["readings"][-10]["t"]
        from urllib.parse import quote
        st, recent = self.request("GET", "/api/v1/history?since=" + quote(since))
        self.assertEqual(self.request("GET", "/api/v1/history?since=" + since)[1], recent)   # a raw "+" is accepted too
        self.assertEqual(len(recent["readings"]), 10)
        self.assertLess(10, all_n)
        self.assertEqual(sorted(recent["readings"][0]), ["d7", "h5", "r5", "r7", "t"])
        self.assertEqual(self.request("GET", "/api/v1/history?since=yesterday")[0], 400)
        st, tok = self.request("GET", "/api/v1/tokens?since=2026-11-06")
        self.assertEqual((st, tok["days"]), (200, []))
        self.assertEqual(len(self.request("GET", "/api/v1/tokens")[1]["days"]), 1)
        self.assertEqual(self.request("GET", "/api/v1/tokens?since=x'or")[0], 400)
        st, m = self.request("GET", "/api/v1/model?hours=8")
        self.assertEqual((st, m["hours"], m["schema"]), (200, 8, 1))
        self.assertIn("weekPace", m["five"])
        self.assertEqual(self.request("GET", "/api/v1/model?hours=99")[0], 400)
        self.assertEqual(self.request("GET", "/api/v1/nothing")[0], 404)

    def test_read_routes_keep_the_cross_site_and_host_checks(self):
        self.assertEqual(self.request("GET", "/api/v1/latest", headers={"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.request("GET", "/api/v1/latest", headers={"Host": "evil.example"})[0], 403)

    def test_settings_are_validated_and_shared(self):
        st, cfg = self.request("GET", "/api/v1/config")
        self.assertEqual((st, cfg["widget"]["level"], cfg["widget"]["work_hours"]), (200, "auto", False))
        self.assertEqual(self.post_config({"level": 4}, origin=False)[0], 403)
        st, cfg = self.post_config({"level": 4, "work_hours": True, "hours": 6})
        self.assertEqual((st, cfg["widget"]["level"], cfg["widget"]["hours"]), (200, 4, 6))
        stored = json.loads((self.data / "config.json").read_text(encoding="utf-8"))
        self.assertEqual((stored["lang"], stored["setup_done"]), ("fr", True))      # the launcher's keys are kept
        self.assertEqual(self.request("GET", "/api/v1/model")[1]["hours"], 6)      # the model follows the settings
        for bad in ({"level": 12}, {"level": "7"}, {"hours": True}, {"css": "body{}"}, {"theme": {"preset": "x"}},
                    {"theme": {"light": {"five": "red"}}}, {"theme": {"light": {"five": "#12345g"}}}, [], {}):
            self.assertEqual(self.post_config(bad)[0], 400, bad)
        st, cfg = self.post_config({"theme": {"preset": "mono", "light": {"five": "#AABBCC"}}})
        self.assertEqual(cfg["widget"]["theme"]["light"]["five"], "#aabbcc")
        self.post_config({"level": "auto", "work_hours": False, "hours": 8, "theme": {"preset": "claude"}})

    def test_a_hand_edited_bad_value_falls_back_to_the_default(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "config.json").write_text(json.dumps({"widget": {"level": 40, "notes": False}}), encoding="utf-8")
            prefs = settings.load(Path(d))
        self.assertEqual((prefs["level"], prefs["notes"]), ("auto", False))

    def test_too_many_changes_are_refused(self):
        codes = [self.post_config({"notes": True})[0] for _ in range(self.server.CONFIG_POSTS[0] + 2)]
        self.assertEqual(codes[0], 200)
        self.assertEqual(codes[-1], 429)


if __name__ == "__main__":
    unittest.main()
