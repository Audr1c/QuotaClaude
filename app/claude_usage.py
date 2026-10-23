#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Usage Tracker: takes one reading of your Claude quota (5-hour and 7-day windows).

    python claude_usage.py        -> one reading (this is what the scheduled task runs)

Each reading writes, inside data/:
  - usage.csv           one line appended (full history)
  - breakdown.csv       per-product weekly shares, one line per product, when they change
  - latest.json         latest state + recent history + estimated 5h->week ratio
  - latest.js           same content, loadable by web/index.html even when opened as a file
  - last_response.json  raw API response (for debugging)
  - tracker.log         log (useful because the scheduled task has no console)

Source: the endpoint Claude Code itself uses for /status (not officially documented,
it may change). The OAuth token is read from ~/.claude/.credentials.json
(%USERPROFILE%\\.claude\\.credentials.json on Windows). Standard library only.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
API_URL = "https://api.anthropic.com/api/oauth/usage"

CSV_FIELDS = [
    "timestamp",
    "five_hour_pct",
    "five_hour_resets_at",
    "seven_day_pct",
    "seven_day_resets_at",
    "seven_day_opus_pct",
    "seven_day_sonnet_pct",
]

# Starting assumption: one full 5-hour window ~ 10 % of the weekly quota.
# Replaced automatically by an estimate once the history allows it.
DEFAULT_RATIO = 10.0
MIN_5H_POINTS_FOR_RATIO = 20.0   # cumulated 5h % observed before trusting the estimate
HISTORY_DAYS = 8                 # history embedded in latest.js for charts
SAME_WINDOW_TOLERANCE_S = 300    # two resets_at less than 5 minutes apart = same window
MAX_LOG_BYTES = 200_000


class TrackerError(Exception):
    """Expected failure (missing token, network, bad format): logged, no traceback.

    `code` is a stable identifier the UIs translate (the message itself is English).
    """

    def __init__(self, code: str, message: str, detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}      # raw facts for the diagnostic panel (status, headers, body...)


# --------------------------------------------------------------------------- dates

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value) -> datetime | None:
    """ISO 8601 (with or without fraction / Z) or epoch seconds -> UTC datetime."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    s = str(value).strip().replace("Z", "+00:00")
    s = re.sub(r"(\.\d+)(?=[+-]\d\d:\d\d$|$)", "", s)  # Python < 3.11 rejects some fractions
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def iso(d: datetime | None) -> str:
    return d.astimezone(timezone.utc).isoformat(timespec="seconds") if d else ""


def num(v) -> float | None:
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- API

def read_token() -> str:
    env = os.environ.get("CLAUDE_USAGE_TOKEN")
    if env:
        return env.strip()
    base = Path(os.environ["CLAUDE_CONFIG_DIR"]) if os.environ.get("CLAUDE_CONFIG_DIR") else Path.home() / ".claude"
    path = base / ".credentials.json"
    if not path.exists():
        raise TrackerError(
            "no_credentials",
            f"Claude Code credentials not found ({path}). "
            "Open Claude Code and sign in (/login) with your Claude subscription.",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise TrackerError("bad_credentials", f"Cannot read {path}: {e}")
    token = (data.get("claudeAiOauth") or {}).get("accessToken")
    if not token:
        raise TrackerError(
            "bad_credentials",
            "No accessToken in .credentials.json: a subscription login is required, not an API key.",
        )
    return token


def fetch_usage(token: str) -> dict:
    req = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
            "User-Agent": "claude-usage-tracker/0.2",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:600]
        detail = {"url": API_URL, "status": e.code, "reason": str(e.reason or ""),
                  "retry_after": e.headers.get("Retry-After") if e.headers else None,
                  "request_id": (e.headers.get("request-id") or e.headers.get("x-request-id")) if e.headers else None,
                  "body": body}
        try:
            err = json.loads(body).get("error") or {}
            detail["api_type"], detail["api_message"] = err.get("type"), err.get("message")
        except (ValueError, AttributeError):
            pass
        if e.code in (401, 403):
            raise TrackerError(
                "auth",
                f"Access refused ({e.code}): the token has probably expired. "
                f"Open Claude Code once, it refreshes it by itself. Detail: {body[:300]}", detail,
            )
        if e.code == 429:
            raise TrackerError("rate_limited", f"HTTP 429 - rate limited: {detail.get('api_message') or body[:200]}", detail)
        raise TrackerError("http", f"HTTP error {e.code}: {body[:300]}", detail)
    except urllib.error.URLError as e:
        raise TrackerError("network", f"Network unavailable: {e.reason}", {"url": API_URL, "reason": str(e.reason)})
    except TimeoutError as e:
        raise TrackerError("network", f"Network timeout: {e}", {"url": API_URL, "reason": "timeout"})
    except ValueError as e:
        raise TrackerError("bad_json", f"Response is not JSON: {e}", {"url": API_URL})


def window(payload: dict, key: str) -> tuple[float | None, datetime | None]:
    w = payload.get(key) or {}
    if not isinstance(w, dict):
        return None, None
    return num(w.get("utilization")), parse_dt(w.get("resets_at"))


def build_row(payload: dict, ts: datetime) -> dict:
    f5, r5 = window(payload, "five_hour")
    f7, r7 = window(payload, "seven_day")
    if f5 is None and f7 is None:
        raise TrackerError("unexpected_response", f"Unexpected response, keys received: {sorted(payload)[:12]}")
    opus, _ = window(payload, "seven_day_opus")
    sonnet, _ = window(payload, "seven_day_sonnet")

    def f(v):
        return "" if v is None else f"{v:g}"

    return {
        "timestamp": iso(ts),
        "five_hour_pct": f(f5),
        "five_hour_resets_at": iso(r5),
        "seven_day_pct": f(f7),
        "seven_day_resets_at": iso(r7),
        "seven_day_opus_pct": f(opus),
        "seven_day_sonnet_pct": f(sonnet),
    }


# --------------------------------------------------------------------------- storage

def append_csv(path: Path, row: dict) -> None:
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if parse_dt(r.get("timestamp"))]
    rows.sort(key=lambda r: parse_dt(r["timestamp"]))
    return rows


def _same(a: datetime | None, b: datetime | None) -> bool:
    return a is not None and b is not None and abs((a - b).total_seconds()) <= SAME_WINDOW_TOLERANCE_S


def estimate_ratio(rows: list[dict]) -> tuple[float | None, float]:
    """
    How many % of the week one full 5-hour window costs.
    Between consecutive readings inside the SAME windows (no reset in between) we add up
    the 5h increase and the 7d increase: ratio = 100 * sum(d7) / sum(d5).
    Returns (ratio, or None when there is not enough data; total 5h points observed).
    """
    s5 = s7 = 0.0
    for a, b in zip(rows, rows[1:]):
        a5, b5 = num(a.get("five_hour_pct")), num(b.get("five_hour_pct"))
        a7, b7 = num(a.get("seven_day_pct")), num(b.get("seven_day_pct"))
        if None in (a5, b5, a7, b7):
            continue
        if not (_same(parse_dt(a.get("five_hour_resets_at")), parse_dt(b.get("five_hour_resets_at")))
                and _same(parse_dt(a.get("seven_day_resets_at")), parse_dt(b.get("seven_day_resets_at")))):
            continue
        d5, d7 = b5 - a5, b7 - a7
        if d5 > 0 and d7 >= 0:
            s5 += d5
            s7 += d7
    if s5 < MIN_5H_POINTS_FOR_RATIO or s7 <= 0:
        return None, s5
    return 100.0 * s7 / s5, s5


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def extract_breakdown(payload: dict) -> dict | None:
    """Weekly usage split by product (Claude Code, Chats, Cowork...), as % of what was used."""
    b = payload.get("seven_day_breakdown")
    if not isinstance(b, dict) or not isinstance(b.get("rows"), list):
        return None
    rows = [
        {"key": r.get("key"), "name": r.get("display_name") or r.get("key"), "pct": num(r.get("percent"))}
        for r in b["rows"] if isinstance(r, dict)
    ]
    return {"as_of": b.get("as_of"), "rows": rows}


BREAKDOWN_FIELDS = ["timestamp", "seven_day_pct", "seven_day_resets_at", "key", "name", "pct"]


def load_breakdown_history(path: Path) -> list[dict]:
    """breakdown.csv grouped by reading: [{t, d7, reset, shares: {key: pct}}], oldest first."""
    if not path.exists():
        return []
    snaps: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            t = parse_dt(r.get("timestamp"))
            if not t or num(r.get("pct")) is None:
                continue
            s = snaps.setdefault(r["timestamp"], {"t": t, "d7": num(r.get("seven_day_pct")),
                                                  "reset": parse_dt(r.get("seven_day_resets_at")), "shares": {}})
            s["shares"][r["key"]] = num(r["pct"])
    return sorted(snaps.values(), key=lambda s: s["t"])


def append_breakdown(path: Path, row: dict, breakdown: dict) -> None:
    """Record the per-product shares of this reading, unless nothing changed since the last record of this window."""
    d7, reset = num(row.get("seven_day_pct")), parse_dt(row.get("seven_day_resets_at"))
    shares = {r["key"]: r["pct"] for r in breakdown["rows"] if r.get("key") and r.get("pct") is not None}
    if d7 is None or not shares:
        return
    hist = load_breakdown_history(path)
    if hist and hist[-1]["d7"] == d7 and hist[-1]["shares"] == shares and _same(hist[-1]["reset"], reset):
        return
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=BREAKDOWN_FIELDS)
        if new:
            w.writeheader()
        for r in breakdown["rows"]:
            if r.get("key") in shares:
                w.writerow({"timestamp": row["timestamp"], "seven_day_pct": row["seven_day_pct"],
                            "seven_day_resets_at": row["seven_day_resets_at"], "key": r["key"],
                            "name": r.get("name") or r["key"], "pct": f"{r['pct']:g}"})


def _local_midnights(start: datetime, end: datetime) -> list[datetime]:
    """Local midnights strictly between start and end (as UTC datetimes)."""
    out, day = [], start.astimezone().date()
    while True:
        day += timedelta(days=1)
        m = datetime(day.year, day.month, day.day).astimezone().astimezone(timezone.utc)
        if m >= end:
            return out
        if m > start:
            out.append(m)


def daily_breakdown(snaps: list[dict], rows: list[dict], now: datetime) -> dict:
    """
    Split each product's weekly usage by local day: {key: [{"day": "YYYY-MM-DD" or None, "pts", "est"}]}.

    pts = points of the weekly quota used by that product that day. A product's cumulative quota at a
    recorded reading is share x week used / 100; at a midnight between two records it is interpolated on
    the week's % (from usage.csv), so each day gets the usage that happened in it. Before the first record
    of the week the product mix is assumed constant ("est": estimated). Days before the first reading of
    the week cannot be told apart: they form one segment with "day": None ("earlier").
    """
    if not snaps or not snaps[-1]["reset"]:
        return {}
    reset = snaps[-1]["reset"]
    start = reset - timedelta(days=7)
    snaps = [s for s in snaps if _same(s["reset"], reset) and s["d7"] is not None and s["t"] >= start]
    if not snaps:
        return {}
    usage = [(parse_dt(r["timestamp"]), num(r.get("seven_day_pct"))) for r in rows
             if _same(parse_dt(r.get("seven_day_resets_at")), reset) and num(r.get("seven_day_pct")) is not None]
    usage = [(t, v) for t, v in usage if t >= start]
    end = min(now, snaps[-1]["t"])
    first_usage = usage[0][0] if usage else snaps[0]["t"]
    bounds = sorted({start, end, *_local_midnights(start, end), *([first_usage] if start < first_usage < end else [])})
    origin = {"t": start, "d7": 0.0, "shares": {}}             # nothing is used when the week starts

    def d7_at(b: datetime) -> float | None:
        v = None
        for t, x in usage:
            if t > b:
                break
            v = x
        return v

    def quota(snap: dict, key: str) -> float:
        return (snap["shares"].get(key) or 0.0) * snap["d7"] / 100.0

    out: dict[str, list] = {}
    for key in snaps[-1]["shares"]:
        points = []                                             # (time, cumulative quota or None, estimated)
        for b in bounds:
            before = origin
            for s in snaps:
                if s["t"] <= b:
                    before = s
            after = next((s for s in snaps if s["t"] > b), None)
            if b == start:
                q, est = 0.0, False
            elif after is None:
                q, est = quota(before, key), False
            else:
                d = d7_at(b)
                if d is None:
                    q, est = None, True
                else:
                    span = after["d7"] - before["d7"]
                    frac = min(1.0, max(0.0, (d - before["d7"]) / span)) if span > 0 else 0.0
                    qb = quota(before, key)
                    q, est = qb + frac * (quota(after, key) - qb), before is origin
            points.append((b, q, est))
        points = [p for p in points if p[1] is not None]        # an unknown midnight merges the days around it
        segs = []
        for (a, qa, ea), (b, qb, eb) in zip(points, points[1:]):
            one_day = a.astimezone().date() == (b - timedelta(seconds=1)).astimezone().date()
            day = a.astimezone().date().isoformat() if one_day else None
            pts = max(0.0, qb - qa)
            if segs and day is not None and segs[-1]["day"] == day:
                segs[-1]["pts"] += pts
                segs[-1]["est"] = segs[-1]["est"] or ea or eb
            else:
                segs.append({"day": day, "pts": pts, "est": ea or eb})
        out[key] = [dict(g, pts=round(g["pts"], 2)) for g in segs if g["pts"] >= 0.01]
    return out


def previous_breakdown(data_dir: Path) -> dict | None:
    try:
        return json.loads((data_dir / "latest.json").read_text(encoding="utf-8")).get("breakdown")
    except (OSError, ValueError, AttributeError):
        return None


MAX_ERRORS_KEPT = 30


def record_diagnostic(data_dir: Path, now: datetime, err: "TrackerError | None") -> dict:
    """Keep a short history of failures in errors.json; return what the widget shows.

    consecutive = failures in a row since the last successful reading (0 when it worked).
    """
    p = data_dir / "errors.json"
    try:
        hist = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(hist, dict):
            raise ValueError
    except (OSError, ValueError):
        hist = {}
    events = hist.get("events") if isinstance(hist.get("events"), list) else []
    consecutive = int(hist.get("consecutive") or 0)
    if err is None:
        consecutive = 0
    else:
        consecutive += 1
        events.append({"t": iso(now), "code": err.code, "message": str(err), **err.detail})
        events = events[-MAX_ERRORS_KEPT:]
    try:
        _atomic_write(p, json.dumps({"consecutive": consecutive, "events": events}, ensure_ascii=False, indent=1))
    except OSError:
        pass
    return {"consecutive": consecutive, "last": events[-1] if (err and events) else None,
            "recent": events[-8:][::-1], "kept": len(events)}


def write_outputs(data_dir: Path, rows: list[dict], now: datetime, error: str | None,
                  breakdown: dict | None = None, error_code: str | None = None,
                  diagnostics: dict | None = None) -> dict:
    last = rows[-1] if rows else None
    ratio, ratio_points = estimate_ratio(rows)
    cutoff = now - timedelta(days=HISTORY_DAYS)
    history = []
    recent = [r for r in rows if parse_dt(r["timestamp"]) >= cutoff]
    for i, r in enumerate(recent):          # repeated values add nothing (the poller can read every 30 s): keep changes + last
        h = {"t": r["timestamp"], "h5": num(r.get("five_hour_pct")), "d7": num(r.get("seven_day_pct"))}
        if history and i < len(recent) - 1 and (history[-1]["h5"], history[-1]["d7"]) == (h["h5"], h["d7"]):
            continue
        history.append(h)
    state = {
        "generated_at": iso(now),
        "fetched_at": last["timestamp"] if last else None,
        "five_hour": {"pct": num(last.get("five_hour_pct")), "resets_at": last.get("five_hour_resets_at") or None} if last else None,
        "seven_day": {"pct": num(last.get("seven_day_pct")), "resets_at": last.get("seven_day_resets_at") or None} if last else None,
        "seven_day_opus_pct": num(last.get("seven_day_opus_pct")) if last else None,
        "seven_day_sonnet_pct": num(last.get("seven_day_sonnet_pct")) if last else None,
        "ratio_estimate": round(ratio, 2) if ratio else None,
        "ratio_points": round(ratio_points, 1),
        "ratio_default": DEFAULT_RATIO,
        "samples": len(rows),
        "history": history,
        "breakdown": breakdown,
        "error": error,
        "error_code": error_code,
        "diagnostics": diagnostics,
    }
    text = json.dumps(state, ensure_ascii=False, indent=1)
    _atomic_write(data_dir / "latest.json", text)
    _atomic_write(data_dir / "latest.js", "window.CLAUDE_USAGE = " + text + ";\n")
    return state


def log(data_dir: Path, msg: str) -> None:
    p = data_dir / "tracker.log"
    try:
        if p.exists() and p.stat().st_size > MAX_LOG_BYTES:
            p.write_text(p.read_text(encoding="utf-8")[-MAX_LOG_BYTES // 2:], encoding="utf-8")
        with p.open("a", encoding="utf-8") as fh:
            fh.write(f"{iso(now_utc())}  {msg}\n")
    except OSError:
        pass


# --------------------------------------------------------------------------- entry point

def run(data_dir: Path = DATA_DIR, payload: dict | None = None, now: datetime | None = None):
    """One complete reading. `payload` lets tests inject an API response.

    Returns (row or None, error message or None, state dict).
    """
    now = now or now_utc()
    data_dir.mkdir(parents=True, exist_ok=True)
    row, error, error_code, breakdown, failure = None, None, None, None, None
    try:
        if payload is None:
            payload = fetch_usage(read_token())
        _atomic_write(data_dir / "last_response.json", json.dumps(payload, ensure_ascii=False, indent=2))
        row = build_row(payload, now)
        append_csv(data_dir / "usage.csv", row)
        breakdown = extract_breakdown(payload)
        if breakdown:
            append_breakdown(data_dir / "breakdown.csv", row, breakdown)
    except TrackerError as e:
        error, error_code, failure = str(e), e.code, e
    diagnostics = record_diagnostic(data_dir, now, failure)
    if breakdown is None:
        breakdown = previous_breakdown(data_dir)
    rows = load_history(data_dir / "usage.csv")
    if breakdown and isinstance(breakdown.get("rows"), list):
        days = daily_breakdown(load_breakdown_history(data_dir / "breakdown.csv"), rows, now)
        for r in breakdown["rows"]:
            r["days"] = days.get(r.get("key"), [])
    state = write_outputs(data_dir, rows, now, error, breakdown, error_code, diagnostics)
    if error:
        d = failure.detail
        extra = "".join(f" {k}={d[k]}" for k in ("status", "retry_after", "request_id") if d.get(k))
        log(data_dir, f"ERROR [{error_code}]{extra} (failure #{diagnostics['consecutive']} in a row) " + error)
    else:
        log(data_dir, f"OK 5h={row['five_hour_pct']}% 7d={row['seven_day_pct']}%")
    return row, error, state


def _fmt_reset(s: str) -> str:
    d = parse_dt(s)
    if not d:
        return "no active window"
    left = d - now_utc()
    h, m = divmod(max(0, int(left.total_seconds() // 60)), 60)
    days, h = divmod(h, 24)
    when = d.astimezone().strftime("%a %d/%m %H:%M")
    return f"resets {when} (in {f'{days} d ' if days else ''}{h} h {m:02d})"


def main() -> int:
    row, error, state = run()
    if error:
        print("ERROR:", error)
        return 1
    print(f"5 hours : {row['five_hour_pct'] or '-'} %  | {_fmt_reset(row['five_hour_resets_at'])}")
    print(f"7 days  : {row['seven_day_pct'] or '-'} %  | {_fmt_reset(row['seven_day_resets_at'])}")
    r = state["ratio_estimate"]
    print(f"Readings stored: {state['samples']}  | 5h->7d ratio: "
          + (f"{r} % (estimated)" if r else f"{DEFAULT_RATIO} % (assumption, not enough data yet)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
