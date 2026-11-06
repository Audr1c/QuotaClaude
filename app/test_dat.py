"""DAT-1: the first reading of a new 5-hour window counts from 0 (when the window began after the previous reading)."""
import unittest

import claude_usage as cu

W7 = "2026-11-10T00:00:00Z"


def row(ts, p5, r5, p7=10):
    return {"timestamp": ts, "five_hour_pct": str(p5), "five_hour_resets_at": r5,
            "seven_day_pct": str(p7), "seven_day_resets_at": W7}


class NewWindowTest(unittest.TestCase):
    def test_start_after_gap_is_counted(self):
        # previous reading 10:00 (window ends 12:00); new window 15:00-20:00, first reading 16:00 at 7 %
        rows = [row("2026-11-06T10:00:00Z", 30, "2026-11-06T12:00:00Z"),
                row("2026-11-06T16:00:00Z", 7, "2026-11-06T20:00:00Z", 11)]
        self.assertEqual(cu.hourly_5h(rows), [["2026-11-06T16:00:00Z", 7.0]])
        self.assertEqual(list(cu._same_window_deltas(rows)), [("2026-11-06T16:00:00Z", 7.0, 1.0)])

    def test_start_before_previous_reading_not_counted(self):
        # new window began 11:00, but the previous reading is from 11:30: usage before it is unknown
        rows = [row("2026-11-06T11:30:00Z", 30, "2026-11-06T11:00:00Z"),
                row("2026-11-06T12:00:00Z", 7, "2026-11-06T16:00:00Z")]
        self.assertEqual(cu.hourly_5h(rows), [])
        self.assertEqual(list(cu._same_window_deltas(rows)), [])

    def test_same_window_unchanged(self):
        rows = [row("2026-11-06T10:00:00Z", 5, "2026-11-06T12:00:00Z"),
                row("2026-11-06T11:00:00Z", 9, "2026-11-06T12:00:00Z", 10)]
        self.assertEqual(cu.hourly_5h(rows), [["2026-11-06T11:00:00Z", 4.0]])


if __name__ == "__main__":
    unittest.main()
