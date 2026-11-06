# -*- coding: utf-8 -*-
"""VSC-1: the status bar logic of the VS Code extension (vscode/lib/status.js), run with node."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class StatusBarTests(unittest.TestCase):
    SCRIPT = r"""
      const vm = require("vm"), fs = require("fs"), root = process.argv[1];
      const sb = { localStorage: { getItem() { return null; }, setItem() {} }, navigator: { language: "fr" },
        location: { search: "" }, document: { documentElement: {}, querySelectorAll() { return []; } }, URLSearchParams };
      sb.window = sb;
      vm.runInNewContext(fs.readFileSync(root + "/web/js/i18n.js", "utf8"), sb);
      const cu = sb.CU, st = require(root + "/vscode/lib/status.js"), H = 3600e3, now = Date.parse("2026-11-05T12:00:00Z");
      const state = { fetched_at: "2026-11-05T11:58:00Z", samples: 9,
        five_hour: { pct: 42, resets_at: new Date(now + 2 * H).toISOString() },
        seven_day: { pct: 18, resets_at: new Date(now + 3 * 24 * H).toISOString() } };
      const out = {};
      out.bars = [0, 1, 33, 34, 66, 67, 100, 140].map(v => st.bars(v));
      const s = st.summary(state, now);
      out.text = st.text(s, cu);
      out.level = s.level;
      out.warn = st.summary(Object.assign({}, state, { five_hour: { pct: 85, resets_at: state.five_hour.resets_at } }), now).level;
      out.error = st.summary(Object.assign({}, state, { seven_day: { pct: 97, resets_at: state.seven_day.resets_at } }), now).level;
      out.stale = st.summary(state, now + 2 * H).level;
      out.tip = st.tooltip(s, cu, now);
      out.none = st.text(st.summary(null, now), cu);
      console.log(JSON.stringify(out));
    """

    def test_status_bar_text_colours_and_tooltip(self):
        r = subprocess.run(["node", "-e", self.SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["bars"], ["▱▱▱", "▰▱▱", "▰▱▱", "▰▰▱", "▰▰▱", "▰▰▰", "▰▰▰", "▰▰▰"])
        self.assertEqual(out["text"], "▰▰▱ 42 % · ▰▱▱ 18 %")
        self.assertEqual((out["level"], out["warn"], out["error"], out["stale"]), ("ok", "warning", "error", "stale"))
        self.assertIn("Fenêtre 5 heures", out["tip"])
        self.assertIn("reset dans 2 h 00", out["tip"])
        self.assertIn("rythme 60 %", out["tip"])           # 3 h of the 5 have gone
        self.assertEqual(out["none"], "Claude —")

    def test_manifest_points_at_existing_files(self):
        pkg = json.loads((ROOT / "vscode" / "package.json").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "vscode" / pkg["main"]).is_file())
        self.assertTrue((ROOT / "vscode" / pkg["contributes"]["viewsContainers"]["activitybar"][0]["icon"]).is_file())
        commands = {c["command"] for c in pkg["contributes"]["commands"]}
        src = (ROOT / "vscode" / "extension.js").read_text(encoding="utf-8")
        for c in commands:
            self.assertIn(f'"{c}"', src)


if __name__ == "__main__":
    unittest.main()
