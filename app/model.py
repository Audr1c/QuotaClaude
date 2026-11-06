# -*- coding: utf-8 -*-
"""The pace model computed on the server (API-1, option B): what GET /api/v1/model returns, so that a client
(VS Code, Android, a phone) only has to draw.

It is a line-by-line port of the core of web/js/model.js (CU.compute), which the widget keeps so that it also works
as a plain file. test_audit.py runs both on the same data and checks they give the same numbers: change them together.
Times are in milliseconds since the epoch, like in JavaScript; "local" means the local time of this machine.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

H = 3600e3
FIVE_H = 5 * H
SEVEN_D = 7 * 24 * H
DEFAULT_START_H = 8


def clamp(v, a=0.0, b=100.0):
    return min(b, max(a, v))


def ms(iso_text) -> float | None:
    if not iso_text:
        return None
    try:
        return datetime.fromisoformat(str(iso_text).replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return None


def local(t: float) -> datetime:
    return datetime.fromtimestamp(t / 1000)          # naive local time, like a JavaScript Date


def midnight(t: float) -> datetime:
    d = local(t)
    return datetime(d.year, d.month, d.day)


def stamp(d: datetime) -> float:
    return d.timestamp() * 1000                       # a naive datetime is read as local time


def win(w, length, now):
    reset = ms(w.get("resets_at")) if w else None
    active = reset is not None and reset > now
    return {
        "active": active,
        "reset": reset if active else None,
        "used": (w.get("pct") or 0) if active else 0,
        "left": reset - now if active else length,
        "pace": clamp((now - (reset - length)) / length * 100) if active else None,
    }


def used_at(history, ts, current):
    pts = [(ms(r.get("t")), r.get("d7")) for r in history or []]
    pts = [p for p in pts if p[0] is not None and p[1] is not None]
    if not pts:
        return current
    p = pts[0]
    for q in pts:
        if q[0] <= ts:
            p = q
    return 0 if p[1] > current else p[1]


def day_starts(history):
    out, last = {}, None
    for r in history or []:
        t = ms(r.get("t"))
        if t is None:
            continue
        key = local(t).date()
        rose = last is not None and (
            (r.get("h5") is not None and last.get("h5") is not None and r["h5"] > last["h5"])
            or (r.get("d7") is not None and last.get("d7") is not None and r["d7"] > last["d7"]))
        if rose and key not in out:
            out[key] = t - stamp(midnight(t))
        last = r
    return out


def work_pace(history, hours, week_start, week_end, now):
    starts = day_starts(history)
    day = midnight(week_start)
    total = elapsed = 0.0
    start_today = None
    today = midnight(now)
    while stamp(day) < week_end:
        key = day.date()
        auto = key in starts
        off = 0 if hours >= 24 else (starts[key] if auto else DEFAULT_START_H * H)
        a = stamp(day) + off
        b = a + hours * H
        lo, hi = max(a, week_start), min(b, week_end)
        if hi > lo:
            total += hi - lo
            elapsed += max(0, min(hi, now) - lo)
        if day == today:
            start_today = {"ms": a, "auto": auto and hours < 24}
        day = datetime(day.year, day.month, day.day) + timedelta(days=1)
    return {"pace": clamp(elapsed / total * 100) if total > 0 else None, "elapsedH": elapsed / H,
            "totalH": total / H, "startToday": start_today}


def compute(D: dict, now: float, hours_per_day: float = 24) -> dict | None:
    """Same result as CU.compute(D, now, { hoursPerDay }) for the gauge values, limits and paces."""
    if not D or not D.get("seven_day"):
        return None
    ratio = D.get("ratio_estimate") or D.get("ratio_default")
    seven = win(D["seven_day"], SEVEN_D, now)
    seven["remaining"] = 100 - seven["used"]
    hours = clamp(hours_per_day or 24, 1, 24)
    seven["sessionsLeft"] = seven["remaining"] / ratio
    wp = work_pace(D.get("history"), hours, seven["reset"] - SEVEN_D, seven["reset"], now) if seven["active"] else None
    if wp:
        seven["pace"] = wp["pace"]
    seven["work"] = wp

    day_start = stamp(midnight(now))
    start_used = used_at(D.get("history"), day_start, seven["used"])
    days_left = max((seven["reset"] - day_start) / (24 * H), 0.25) if seven["active"] else 1
    seven["startUsed"], seven["daysLeft"] = start_used, days_left
    seven["dailyBudget"] = (100 - start_used) / days_left
    seven["limit"] = clamp(start_used + seven["dailyBudget"]) if seven["active"] else None
    seven["todayUsed"] = max(0, seven["used"] - start_used)
    seven["todayLeft"] = 0 if seven["limit"] is None else max(0, seven["limit"] - seven["used"])
    seven["ratePerDay"] = seven["dailyBudget"]
    seven["ratePerHour"] = seven["dailyBudget"] / hours

    five = win(D.get("five_hour"), FIVE_H, now)
    five["limit"] = five["used"] + seven["todayLeft"] * 100 / ratio if five["active"] and seven["limit"] is not None else None
    five["weekPace"] = (five["used"] + (seven["pace"] - seven["used"]) * 100 / ratio
                        if five["active"] and seven["pace"] is not None else None)
    five["maxRate"] = (100 - five["used"]) / (five["left"] / H)
    five["paceRate"] = seven["ratePerHour"] * 100 / ratio

    fetched = ms(D.get("fetched_at"))
    return {"schema": 1, "five": five, "seven": seven, "ratio": ratio, "hours": hours,
            "ratioEstimated": bool(D.get("ratio_estimate")), "samples": D.get("samples"),
            "fetched": fetched, "age": now - fetched if fetched else None, "error": D.get("error"),
            "errorCode": D.get("error_code"), "status5": status(five["used"], five["pace"]),
            "status7": status(seven["used"], seven["pace"])}


def status(used, pace):
    """Ahead of / behind the pace, like CU.status."""
    if pace is None:
        return None
    d = used - pace
    if d > 5:
        return {"kind": "ahead", "n": math.floor(d + 0.5)}          # Math.round, not round-half-to-even
    if d < -5:
        return {"kind": "margin", "n": math.floor(-d + 0.5)}
    return {"kind": "even", "n": 0}
