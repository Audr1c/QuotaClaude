# -*- coding: utf-8 -*-
"""Tests of RES-1 (parse cache, identical outputs) and RES-2 (unchanged files are not rewritten)."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import claude_usage as cu

T0 = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)


def pl(h5, d7):
    return {"five_hour": {"utilization": h5, "resets_at": "2026-10-22T12:00:00+00:00"},
            "seven_day": {"utilization": d7, "resets_at": "2026-10-27T18:00:00.123456+00:00"}}


class ParseCacheTests(unittest.TestCase):
    def test_cache_hit_and_same_values(self):
        cu._parse_str.cache_clear()
        s = "2026-10-22T12:00:00.5Z"
        first = cu.parse_dt(s)
        for _ in range(1000):
            self.assertEqual(cu.parse_dt(s), first)
        info = cu._parse_str.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertGreaterEqual(info.hits, 1000)

    def test_semantics_unchanged(self):
        self.assertIsNone(cu.parse_dt(None))
        self.assertIsNone(cu.parse_dt(""))
        self.assertIsNone(cu.parse_dt("garbage"))
        self.assertEqual(cu.parse_dt(0), datetime(1970, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(cu.parse_dt("2026-10-22T09:00:00"), T0)
        self.assertEqual(cu.parse_dt("2026-10-22T11:00:00+02:00"), T0)

    def test_run_output_is_deterministic(self):
        outs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as d:
                dd = Path(d)
                for i in range(5):
                    cu.run(dd, payload=pl(10 + i, 20 + i), now=T0 + timedelta(minutes=5 * i))
                outs.append((dd / "latest.json").read_text(encoding="utf-8"))
            cu._parse_str.cache_clear()
        self.assertEqual(outs[0], outs[1])
        json.loads(outs[0])


class AtomicWriteTests(unittest.TestCase):
    def test_identical_content_not_rewritten(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            cu._atomic_write(p, "hello\n")
            ino = p.stat().st_ino
            with mock.patch("claude_usage.os.replace") as rep:
                cu._atomic_write(p, "hello\n")
                rep.assert_not_called()
            self.assertEqual(p.stat().st_ino, ino)
            self.assertEqual(os.listdir(d), ["x.json"])      # no temp file left behind

    def test_changed_content_is_written(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            cu._atomic_write(p, "a")
            cu._atomic_write(p, "b")
            self.assertEqual(p.read_text(encoding="utf-8"), "b")

    def test_run_skips_identical_last_response(self):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            cu.run(dd, payload=pl(10, 20), now=T0)
            with mock.patch("claude_usage.os.replace", wraps=os.replace) as rep:
                cu.run(dd, payload=pl(10, 20), now=T0 + timedelta(minutes=5))
                written = [Path(c.args[1]).name for c in rep.call_args_list]
            self.assertNotIn("last_response.json", written)
            self.assertIn("latest.json", written)      # generated_at changed


if __name__ == "__main__":
    unittest.main()
