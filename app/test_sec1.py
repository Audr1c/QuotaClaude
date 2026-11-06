# -*- coding: utf-8 -*-
"""SEC-1 (cross-process reading lock) and RES-3 (poller sleep slice)."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import claude_usage as cu
import poller

PAYLOAD = {"five_hour": {"utilization": 10, "resets_at": "2030-01-01T05:00:00+00:00"},
           "seven_day": {"utilization": 20, "resets_at": "2030-01-05T00:00:00+00:00"}}


class ReadingLockTest(unittest.TestCase):
    def test_runs_do_not_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            data = Path(d)
            guard = threading.Lock()
            active = {"now": 0, "max": 0}
            orig = cu._run_locked

            def slow(*a, **k):
                with guard:
                    active["now"] += 1
                    active["max"] = max(active["max"], active["now"])
                time.sleep(0.2)
                try:
                    return orig(*a, **k)
                finally:
                    with guard:
                        active["now"] -= 1

            with mock.patch.object(cu, "_run_locked", slow):
                ts = [threading.Thread(target=cu.run, args=(data, PAYLOAD)) for _ in range(3)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
            self.assertEqual(active["max"], 1)

    def test_busy_when_lock_not_obtained(self):
        with tempfile.TemporaryDirectory() as d:
            data = Path(d)
            with cu.reading_lock(data, 1) as held:
                self.assertTrue(held)
                with mock.patch.object(cu, "READING_LOCK_TIMEOUT_S", 0.3):
                    row, err, state = cu.run(data, PAYLOAD)
            self.assertIsNone(row)
            self.assertTrue(err)
            self.assertEqual(state["error_code"], "busy")


class SleepSliceTest(unittest.TestCase):
    def test_watching_is_short(self):
        self.assertEqual(poller.sleep_slice(100, True), poller.TICK_S)

    def test_not_watching_is_capped(self):
        self.assertEqual(poller.sleep_slice(600, False), poller.MAX_SLEEP_S)

    def test_never_beyond_due(self):
        self.assertEqual(poller.sleep_slice(12, False), 12)
        self.assertEqual(poller.sleep_slice(2, True), 2)
        self.assertEqual(poller.sleep_slice(-5, False), 0.0)


if __name__ == "__main__":
    unittest.main()
