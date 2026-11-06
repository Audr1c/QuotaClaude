# -*- coding: utf-8 -*-
"""
Tests added with the 1.1.1 fixes (findings of the 1.1.0 audit): message de-duplication in the transcript reader,
nothing private in its state file, server hardening, no account name in what the widget serves, long chart ranges.

    python -m unittest test_audit        (from the app/ folder)
"""
import http.client
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import claude_usage as cu
import transcripts as T

NL = chr(10)


def line(mid, hour, out, cr=0, cw=0, model="m1", side=False, inp=2):
    return json.dumps({"type": "assistant", "timestamp": f"2026-11-05T{hour}:10:00.000Z", "isSidechain": side,
                       "message": {"id": mid, "model": model, "content": "SECRET",
                                   "usage": {"input_tokens": inp, "output_tokens": out,
                                             "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw}}}) + NL


def messages(st):
    return sum(v[4] for v in st["buckets"].values())


def output(st):
    return sum(v[1] for v in st["buckets"].values())


class TranscriptDedupTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        self.root, self.data = Path(self.a.name), Path(self.b.name)

    def tearDown(self):
        self.a.cleanup()
        self.b.cleanup()

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_same_id_not_on_the_previous_line_and_in_two_files_is_counted_once(self):
        self.put("p1/s.jsonl", line("A", "10", 5) + line("B", "10", 7, side=True) + line("A", "10", 50))
        self.put("p2/s.jsonl", line("A", "10", 50) + line("C", "11", 3))          # a resumed session repeats A
        st = T.scan(self.data, self.root)
        self.assertEqual(messages(st), 3)
        self.assertEqual(output(st), 50 + 7 + 3)

    def test_a_less_complete_copy_never_replaces_the_complete_one(self):
        self.put("p1/s.jsonl", line("A", "10", 50))
        T.scan(self.data, self.root)
        self.put("p2/s.jsonl", line("A", "10", 5))
        self.assertEqual(output(T.scan(self.data, self.root)), 50)

    def test_replaced_file_is_read_again_without_counting_twice(self):
        p = self.put("p1/s.jsonl", line("A", "10", 5, cr=1000) + line("B", "10", 6))
        T.scan(self.data, self.root)
        p.write_text(line("X", "09", 1) + line("A", "10", 5, cr=1000) + line("B", "10", 6) + line("D", "11", 9), encoding="utf-8")
        st = T.scan(self.data, self.root)                                          # bigger and different: re-read from 0
        self.assertEqual(messages(st), 4)
        self.assertEqual(output(st), 1 + 5 + 6 + 9)

    def test_state_holds_no_project_or_folder_name_and_no_text(self):
        self.put("SECRETPROJECT-Users-audri/session.jsonl", line("A", "10", 5))
        T.scan(self.data, self.root)
        text = (self.data / T.STATE_NAME).read_text() + (self.data / T.CSV_NAME).read_text()
        for word in ("SECRETPROJECT", "audri", "session", "jsonl", "SECRET"):
            self.assertNotIn(word, text)

    def test_model_name_cannot_break_the_files(self):
        self.put("p/s.jsonl", line("A", "10", 5, model="a|b" + NL + "c,d") + line("B", "10", 5, model="x" * 500))
        st = T.scan(self.data, self.root)
        self.assertTrue(all(k.count("|") == 2 for k in st["buckets"]))
        self.assertTrue(all(len(k.split("|")[1]) <= 64 for k in st["buckets"]))
        self.assertEqual(len((self.data / T.CSV_NAME).read_text().splitlines()), 1 + len(st["buckets"]))

    def test_a_damaged_state_is_rebuilt_not_fatal(self):
        self.put("p/s.jsonl", line("A", "10", 5))
        for bad in ({"v": T.VERSION, "files": {}, "seen": {}, "buckets": {"2026-11-05T10:00:00Z|m1|main": [1]}},
                    {"v": T.VERSION, "files": {"x": 3}, "seen": {}, "buckets": {}},
                    {"v": T.VERSION, "files": {}, "seen": {"id": ["k"]}, "buckets": {}},
                    [1, 2, 3]):
            (self.data / T.STATE_NAME).write_text(json.dumps(bad))
            self.assertEqual(messages(T.scan(self.data, self.root)), 1)
        (self.data / T.STATE_NAME).write_text("{not json")
        self.assertEqual(messages(T.scan(self.data, self.root)), 1)

    def test_placeholder_messages_without_tokens_are_ignored(self):
        self.put("p/s.jsonl", line("A", "10", 0, inp=0, model="<synthetic>") + line("B", "10", 4))
        self.assertEqual(messages(T.scan(self.data, self.root)), 1)


class ServerHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server = server
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def request(self, method, path, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, headers=headers or {})
        r = c.getresponse()
        r.read()
        out = r.status, r
        c.close()
        return out

    def test_odd_paths_never_reach_the_file_system(self):
        bs = chr(92)
        for rel in ("//evil.example/share/x", bs + bs + "evil" + bs + "x", "..", "../x", "a//b", "C:/Windows/win.ini",
                    "js/../js/app.js", ".hidden", "", "js/", "x%00", "/js/app.js"):
            self.assertIsNone(self.server.web_file(rel), rel)
        self.assertIsNotNone(self.server.web_file("js/app.js"))
        self.assertEqual(self.request("GET", "/web///evil.example/share/x")[0], 404)

    def test_a_page_of_another_site_cannot_read_our_files(self):
        for path in ("/data/latest.js", "/data/latest.json", "/web/index.html", "/web/js/app.js"):
            self.assertEqual(self.request("GET", path, {"Sec-Fetch-Site": "cross-site"})[0], 403, path)
            self.assertEqual(self.request("GET", path, {"Sec-Fetch-Site": "same-site"})[0], 403, path)
        self.assertEqual(self.request("GET", "/web/index.html", {"Sec-Fetch-Site": "same-origin"})[0], 200)
        self.assertEqual(self.request("GET", "/web/index.html", {"Sec-Fetch-Site": "none"})[0], 200)
        self.assertEqual(self.request("GET", "/api/ping", {"Sec-Fetch-Site": "cross-site"})[0], 200)   # only says who we are

    def test_only_the_three_data_files_are_served(self):
        for name in ("tokens.csv", "transcripts_state.json", "usage.csv", "breakdown.csv", "tracker.log", "errors.json",
                     "last_response.json", "poller.lock", "config.json"):
            self.assertEqual(self.request("GET", "/data/" + name)[0], 404, name)

    def test_security_headers(self):
        status, r = self.request("GET", "/web/index.html")
        self.assertEqual(status, 200)
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(r.getheader("Cross-Origin-Resource-Policy"), "same-origin")
        self.assertIn("script-src 'self'", r.getheader("Content-Security-Policy"))
        self.assertIn("frame-ancestors 'none'", r.getheader("Content-Security-Policy"))
        self.assertNotIn("Python", r.getheader("Server"))
        status, r = self.request("GET", "/web/js/app.js")
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")

    def test_easy_address_and_installable_app(self):
        ok = self.request("GET", "/web/index.html", {"Host": f"claude.localhost:{self.port}"})[0]
        self.assertEqual(ok, 200)
        for host in (f"evil.localhost:{self.port}", f"claude.localhost.evil.example:{self.port}", "claude.localhost"):
            self.assertEqual(self.request("GET", "/web/index.html", {"Host": host})[0], 403, host)
        status, r = self.request("GET", "/web/manifest.webmanifest")
        self.assertEqual((status, r.getheader("Content-Type")), (200, "application/manifest+json"))
        self.assertEqual(self.request("GET", "/web/sw.js")[1].getheader("Content-Type"), "text/javascript; charset=utf-8")

    def test_the_page_has_no_inline_script(self):
        html = (self.server.WEB / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", html)
        self.assertNotRegex(html, r"\son[a-z]+=")

    def test_refresh_needs_the_widget_origin(self):
        host = f"127.0.0.1:{self.port}"
        with mock.patch.object(self.server.cu, "run", side_effect=AssertionError("must not read")):
            self.assertEqual(self.request("POST", "/api/refresh")[0], 403)                         # no Origin
            self.assertEqual(self.request("POST", "/api/refresh", {"Origin": "http://evil.example"})[0], 403)
            self.assertEqual(self.request("POST", "/api/refresh", {"Origin": f"http://{host}", "Sec-Fetch-Site": "cross-site"})[0], 403)

    def test_refresh_is_rate_limited(self):
        host = f"127.0.0.1:{self.port}"
        self.server._last_refresh[0] = 0.0
        calls = []

        def fake_run():
            calls.append(1)
            return None, None, {"ok": True}
        with mock.patch.object(self.server.cu, "run", side_effect=fake_run), \
                mock.patch.object(self.server.importlib, "reload", side_effect=lambda m: m):
            for _ in range(3):
                c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                c.request("POST", "/api/refresh", headers={"Origin": f"http://{host}"})
                r = c.getresponse()
                body = json.loads(r.read())
                c.close()
                self.assertEqual(r.status, 200)
        self.assertEqual(len(calls), 1)                      # the two other clicks got the saved state, no API call
        self.assertTrue(body.get("cached"))


class NoAccountNameTests(unittest.TestCase):
    def test_messages_and_served_state_hide_the_home_folder(self):
        home = str(Path.home())
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(Path.home() / "no-such-folder-xyz")}):
            os.environ.pop("CLAUDE_USAGE_TOKEN", None)
            with self.assertRaises(cu.TrackerError) as cm:
                cu.read_token()
            self.assertNotIn(home, str(cm.exception))
            self.assertIn("~", str(cm.exception))
            cu.write_outputs(Path(d), [], cu.now_utc(), "failed at " + home + chr(92) + "x", None, None, {"p": home})
            for name in ("latest.json", "latest.js"):
                self.assertNotIn(home, (Path(d) / name).read_text(encoding="utf-8"))
                self.assertNotIn(json.dumps(home)[1:-1], (Path(d) / name).read_text(encoding="utf-8"))


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ChartRangeTests(unittest.TestCase):
    SCRIPT = """
      global.window = global; global.localStorage = { getItem() { return null; }, setItem() {} };
      global.document = { documentElement: {}, querySelectorAll() { return []; }, addEventListener() {} };
      global.navigator = { language: "en" };
      for (const f of ["i18n", "model", "charts"]) require(process.argv[2] + "/web/js/" + f + ".js");
      const { hourlyBuckets, bucketHours } = CU.charts.internals, H = 3600e3, D = 24 * H;
      const hi = Math.ceil(Date.now() / H) * H, out = {};
      for (const days of [1, 14, 90, 400, 420, 800, 3000]) {
        const hourly5 = [];
        for (let t = hi - days * D; t < hi; t += 7 * H) hourly5.push([new Date(t).toISOString(), 2]);
        const r = hourlyBuckets({ hourly5 }, hi - days * D, hi);
        const total = r.bars.reduce((s, b) => s + b.v, 0);
        out[days] = { n: r.bars.length, reachesNow: r.bars[r.bars.length - 1].e >= hi, total, expected: hourly5.length * 2 };
      }
      console.log(JSON.stringify(out));
    """

    def test_every_range_reaches_the_present_and_keeps_all_the_usage(self):
        app = str(Path(__file__).resolve().parent)
        r = subprocess.run(["node", "-", app], input=self.SCRIPT, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        for days, x in res.items():
            self.assertTrue(x["reachesNow"], days)
            self.assertLessEqual(x["n"], 450, days)
            self.assertEqual(x["total"], x["expected"], days)          # not one hour of usage dropped by a long range


if __name__ == "__main__":
    unittest.main()
