"""Real-browser test of the widget (TST-1): Chromium driven by Playwright through node.

Skipped when node or playwright is missing. It builds synthetic data in a temp folder (never the real app/data),
runs one node script and asserts on the JSON it prints. The page is opened with ?lang=en (no accents outside i18n.js).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import claude_usage as cu

HERE = Path(__file__).resolve().parent


def node_env():
    """Environment for node with the global node_modules on NODE_PATH, or None when node/playwright is unavailable."""
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        return None
    try:
        root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=30).stdout.strip()
        env = dict(os.environ, NODE_PATH=root)
        ok = subprocess.run([node, "-e", "require('playwright')"], env=env, capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None
    return env if ok else None


def synthetic_rows(now: datetime, days: int = 13) -> list[dict]:
    """A reading every 30 minutes for `days` days, usage in every slot (so every hour has some)."""
    h5 = timedelta(hours=5)
    t = (now - timedelta(days=days)).replace(minute=0, second=0, microsecond=0)
    rows, k, win, d7 = [], 0, None, 0.0
    reset7 = now + timedelta(days=3)
    while t <= now:
        w = int(t.timestamp() // h5.total_seconds())
        if w != win:
            win, k = w, 0
        k += 1
        d7 = min(60.0, d7 + 0.05)
        rows.append(cu.build_row({
            "five_hour": {"utilization": min(95.0, 0.5 * k), "resets_at": cu.iso(datetime.fromtimestamp((w + 1) * h5.total_seconds(), timezone.utc))},
            "seven_day": {"utilization": round(d7), "resets_at": cu.iso(reset7)},
        }, t))
        t += timedelta(minutes=30)
    return rows


NODE_SCRIPT = r"""
const { chromium } = require('playwright');
const [url, tz] = process.argv.slice(2);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function open(browser, timezoneId) {
  const ctx = await browser.newContext({ timezoneId, viewport: { width: 1100, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(url);
  await page.waitForSelector('#app *', { timeout: 10000 });
  await sleep(300);
  return { ctx, page, errors };
}

async function levels(page) {
  if (!(await page.$('#level'))) return null;
  const out = {};
  for (let lv = 1; lv <= 9; lv++) {
    await page.evaluate(v => { const e = document.querySelector('#level'); e.value = String(v); e.dispatchEvent(new Event('input', { bubbles: true })); }, lv);
    await sleep(150);
    out[lv] = await page.evaluate(() => ({
      level: document.body.dataset.level,
      strip: !!document.querySelector('.strip'),
      compact: !!document.querySelector('.compact'),
      gauges: document.querySelectorAll('svg.gauge').length,
      hourly: !!document.querySelector('[data-key=hourly]'),
      ratio: !!document.querySelector('[data-key=ratio]'),
      tokens: !!document.querySelector('[data-key=tokens]'),
      breakdown: !!document.querySelector('.breakdown'),
      hoursVisible: (() => { const e = document.querySelector('#hours-box'); return !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; })(),
    }));
  }
  return out;
}

async function notes(page) {
  if (!(await page.$('#notes'))) return null;
  const hiddenCount = () => page.evaluate(() => { const n = [...document.querySelectorAll('[data-note]')]; return { total: n.length, hidden: n.filter(e => e.hasAttribute('hidden')).length }; });
  const before = await hiddenCount();
  await page.click('#notes'); await sleep(150);
  const after = await hiddenCount();
  await page.click('#notes'); await sleep(150);
  const again = await hiddenCount();
  return { before, after, again };
}

const label = (page) => page.evaluate(() => { const r = document.querySelector('[data-key=hourly] .rlabel'); return r && r.firstChild ? r.firstChild.textContent.trim() : null; });

async function drags(page) {
  if (await page.$('#level')) {
    await page.evaluate(() => { const e = document.querySelector('#level'); e.value = '9'; e.dispatchEvent(new Event('input', { bubbles: true })); });
    await sleep(200);
  }
  await page.evaluate(() => { const d = document.querySelector('[data-key=hourly]'); d.open = true; d.scrollIntoView({ block: 'center' }); });
  await sleep(300);
  const out = { start: await label(page) };
  const plot = await (await page.$('[data-key=hourly] svg.plot')).boundingBox();
  const cy = plot.y + plot.height / 2;
  // drag to the right = back in time (the range starts at the present, it cannot go further right)
  await page.mouse.move(plot.x + plot.width * 0.4, cy); await page.mouse.down();
  await page.mouse.move(plot.x + plot.width * 0.7, cy, { steps: 8 }); await page.mouse.up();
  await sleep(200);
  out.afterPlot = await label(page);
  out.beforeMini = out.afterPlot;
  const win = await (await page.$('[data-key=hourly] svg.mini .win')).boundingBox();
  const mini = await (await page.$('[data-key=hourly] svg.mini')).boundingBox();
  const wy = mini.y + mini.height / 2, wx = win.x + win.width / 2;
  await page.mouse.move(wx, wy); await page.mouse.down();
  await page.mouse.move(wx - Math.min(80, win.x - mini.x - 2), wy, { steps: 8 }); await page.mouse.up();
  await sleep(200);
  out.afterMini = await label(page);
  return out;
}

async function dst(page) {
  await page.evaluate(() => { const d = document.querySelector('[data-key=hourly]'); d.open = true; });
  return page.evaluate(() => {
    const m = CU.lastModel, I = CU.charts.internals;
    const ranges = {
      '3d': [new Date(2026, 9, 24, 0, 0).getTime(), new Date(2026, 9, 27, 0, 0).getTime()],
      '37h': [new Date(2026, 9, 24, 12, 0).getTime(), new Date(2026, 9, 26, 0, 0).getTime()],
      '7d': [new Date(2026, 9, 22, 0, 0).getTime(), new Date(2026, 9, 29, 0, 0).getTime()],
    };
    const out = { offsets: [new Date(2026, 9, 24, 12).getTimezoneOffset(), new Date(2026, 9, 26, 12).getTimezoneOffset()], ranges: {} };
    for (const [name, [a, b]] of Object.entries(ranges)) {
      const { bh, bars } = I.hourlyBuckets(m, a, b);
      let contiguous = true;
      const unique = new Set(bars.map(x => x.t)).size === bars.length;
      for (let i = 1; i < bars.length; i++) if (bars[i].t !== bars[i - 1].e) contiguous = false;
      const lo = bars[0].t, hi = bars[bars.length - 1].e;
      const input = m.hourly5.filter(([iso]) => { const t = Date.parse(iso); return t >= lo && t < hi; }).reduce((s, [, v]) => s + v, 0);
      const kept = bars.reduce((s, x) => s + x.v, 0);
      out.ranges[name] = { bh, n: bars.length, contiguous, unique, firstCovers: lo <= a, lastCovers: hi >= b, input, kept, spanHours: (hi - lo) / 3600e3 };
    }
    out.chartRendered = !!document.querySelector('[data-key=hourly] svg.plot rect');
    return out;
  });
}

(async () => {
  const browser = await chromium.launch();
  const res = {};
  try {
    let c = await open(browser, 'UTC');
    res.levels = await levels(c.page);
    res.notes = await notes(c.page);
    res.drag = await drags(c.page);
    res.errors = c.errors;
    await c.ctx.close();
    c = await open(browser, tz);
    res.dst = await dst(c.page);
    res.dstErrors = c.errors;
    await c.ctx.close();
  } finally { await browser.close(); }
  console.log('RESULT' + JSON.stringify(res));
})().catch(e => { console.error(e); process.exit(1); });
"""

ENV = node_env()


@unittest.skipUnless(ENV, "node or playwright not available")
class BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        shutil.copytree(HERE / "web", tmp / "web")
        (tmp / "data").mkdir()
        now = cu.now_utc().replace(microsecond=0)
        breakdown = {"as_of": cu.iso(now), "rows": [{"key": "code", "name": "Claude Code", "pct": 70.0},
                                                      {"key": "chat", "name": "Chats", "pct": 30.0}]}
        with mock.patch.object(cu, "token_expiry", return_value=None):
            cls.state = cu.write_outputs(tmp / "data", synthetic_rows(now), now, None, breakdown)
        script = tmp / "run.js"
        script.write_text(NODE_SCRIPT, encoding="utf-8")
        url = (tmp / "web" / "index.html").as_uri() + "?lang=en"
        p = subprocess.run(["node", str(script), url, "Europe/Paris"], env=ENV, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise RuntimeError("node failed: " + p.stderr[-2000:])
        line = [x for x in p.stdout.splitlines() if x.startswith("RESULT")][-1]
        cls.r = json.loads(line[len("RESULT"):])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_data_is_synthetic(self):
        self.assertIsNone(self.state["tokens"])
        self.assertTrue(self.state["hourly_5h"])

    def test_no_errors(self):
        self.assertEqual(self.r["errors"], [])
        self.assertEqual(self.r["dstErrors"], [])

    def test_levels(self):
        lv = self.r["levels"]
        if lv is None:
            self.fail("the widget has no #level slider")
        for n in range(1, 10):
            # level 9 with Explanations on (the default) is shown as level 10
            self.assertIn(lv[str(n)]["level"], (str(n), "10") if n == 9 else (str(n),))
        self.assertTrue(lv["1"]["strip"])
        self.assertTrue(lv["4"]["compact"])
        self.assertEqual(lv["5"]["gauges"], 2)
        self.assertTrue(lv["6"]["hourly"])
        self.assertTrue(lv["7"]["ratio"])
        if self.state.get("tokens"):
            self.assertTrue(lv["7"]["tokens"])
        self.assertTrue(lv["9"]["breakdown"])
        self.assertTrue(lv["9"]["hoursVisible"])

    def test_notes_toggle(self):
        n = self.r["notes"]
        if n is None:
            self.fail("the widget has no #notes button")
        self.assertGreater(n["before"]["total"], 0)
        self.assertNotEqual(n["before"]["hidden"], n["after"]["hidden"])
        self.assertEqual(n["before"]["hidden"], n["again"]["hidden"])

    def test_drag_overview(self):
        d = self.r["drag"]
        self.assertTrue(d["start"])
        self.assertNotEqual(d["afterMini"], d["beforeMini"])

    def test_drag_plot(self):
        d = self.r["drag"]
        self.assertNotEqual(d["afterPlot"], d["start"])

    def test_dst_hourly_buckets(self):
        d = self.r["dst"]
        self.assertEqual(d["offsets"], [-120, -60])          # Paris: summer time before 2026-10-25, winter time after
        self.assertTrue(d["chartRendered"])
        for name, b in d["ranges"].items():
            with self.subTest(range=name):
                self.assertTrue(b["contiguous"])
                self.assertTrue(b["unique"])
                self.assertTrue(b["firstCovers"])
                self.assertTrue(b["lastCovers"])
                self.assertAlmostEqual(b["kept"], b["input"], places=6)
                self.assertGreater(b["kept"], 0)
        self.assertEqual(d["ranges"]["37h"]["bh"], 1)


if __name__ == "__main__":
    unittest.main()
