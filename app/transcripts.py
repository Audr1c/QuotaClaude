# -*- coding: utf-8 -*-
"""
Local token counters read from Claude Code's transcripts (~/.claude/projects/**/*.jsonl).

Why: the quota endpoint only gives percentages. The transcripts give the real token volumes, so we can show the
cache hit rate and measure how many tokens one percent of the weekly quota is worth.

Privacy: a transcript holds whole conversations. Only `message.id`, `message.model`, `timestamp` and the numbers of
`message.usage` are ever read out of a line; nothing else is kept, logged or written. Nothing here is served except
the aggregated counters (data/tokens.csv and the "tokens" part of latest.json).

How: each file is read from the byte offset where the last scan stopped (the first scan reads everything, later
ones only what was appended). Claude Code writes the same assistant message several times while it streams, with
the final numbers in the last copy: consecutive lines with the same `message.id` replace each other.
Counts go into hourly (UTC) buckets per model, kept in data/transcripts_state.json and exported to data/tokens.csv.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ["input", "output", "cache_read", "cache_write", "messages"]
STATE_NAME, CSV_NAME = "transcripts_state.json", "tokens.csv"


def projects_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECTS_DIR") or Path.home() / ".claude" / "projects")


def _hour(ts) -> str | None:
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")


def _n(v) -> int:
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else 0


def parse_line(raw: bytes):
    """(message_id, hour, model, [input, output, cache_read, cache_write]) or None. Reads nothing but those fields."""
    if b'"usage"' not in raw or b'"assistant"' not in raw:       # cheap filter before the JSON parse
        return None
    try:
        d = json.loads(raw)
        m = d["message"]
        u = m["usage"]
        hour = _hour(d["timestamp"])
        if d.get("type") != "assistant" or not hour or not isinstance(u, dict):
            return None
        mid = m.get("id")
        model = m.get("model")
        return (mid if isinstance(mid, str) else None, hour, model if isinstance(model, str) else "?",
                [_n(u.get("input_tokens")), _n(u.get("output_tokens")),
                 _n(u.get("cache_read_input_tokens")), _n(u.get("cache_creation_input_tokens"))])
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def _add(buckets: dict, hour: str, model: str, vals: list, sign: int = 1) -> None:
    b = buckets.setdefault(hour + "|" + model, [0, 0, 0, 0, 0])
    for i, v in enumerate(vals):
        b[i] += sign * v
    b[4] += sign


def scan(data_dir: Path, root: Path | None = None) -> dict:
    """Read what was appended to the transcripts since the last scan and return the state (also saved)."""
    root = root or projects_dir()
    sp = data_dir / STATE_NAME
    try:
        st = json.loads(sp.read_text(encoding="utf-8"))
        if not isinstance(st.get("files"), dict) or not isinstance(st.get("buckets"), dict):
            raise ValueError
    except (OSError, ValueError):
        st = {"files": {}, "buckets": {}}
    files, buckets = st["files"], st["buckets"]
    changed = False
    for path in (root.rglob("*.jsonl") if root.is_dir() else []):
        key = str(path.relative_to(root))
        try:
            size = path.stat().st_size
        except OSError:
            continue
        f = files.get(key) or {"offset": 0, "last": None}
        if size < f["offset"]:                      # file replaced: start it over (its old counts stay, rare)
            f = {"offset": 0, "last": None}
        if size == f["offset"]:
            files[key] = f
            continue
        try:
            with path.open("rb") as fh:
                fh.seek(f["offset"])
                chunk = fh.read(size - f["offset"])
        except OSError:
            continue
        end = chunk.rfind(b"\n") + 1                # never consume a half-written last line
        last = f["last"]                            # [message_id, hour, model, vals] of the previous line
        for raw in chunk[:end].split(b"\n"):
            r = parse_line(raw)
            if not r:
                continue
            mid, hour, model, vals = r
            if mid and last and last[0] == mid:     # same message streamed again: the new copy replaces the old one
                _add(buckets, last[1], last[2], last[3], -1)
            _add(buckets, hour, model, vals)
            last = [mid, hour, model, vals]
        files[key] = {"offset": f["offset"] + end, "last": last}
        changed = True
    if changed or not sp.exists():
        _write(data_dir, st)
    return st


def _write(data_dir: Path, st: dict) -> None:
    def atomic(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="")
        os.replace(tmp, path)
    try:
        atomic(data_dir / STATE_NAME, json.dumps(st, separators=(",", ":")))
        rows = ["hour,model," + ",".join(FIELDS)]
        for k in sorted(st["buckets"]):
            hour, model = k.split("|", 1)
            rows.append(",".join([hour, model.replace(",", " ")] + [str(x) for x in st["buckets"][k]]))
        atomic(data_dir / CSV_NAME, "\n".join(rows) + "\n")
    except OSError:
        pass                                        # locked by a sync tool: next scan retries


def cache_hit(inp: float, cache_read: float, cache_write: float):
    """Share of the prompt tokens served from the cache, in %."""
    total = inp + cache_read + cache_write
    return round(100.0 * cache_read / total, 1) if total > 0 else None


def summary(st: dict, now: datetime, d7_by_day: dict | None = None, days: int = 120) -> dict:
    """What the widget shows: per UTC day totals (overall and per model, with the weekly % of that day), the last 7 days,
    and the per-model share. Counters per model are [input, output, cache_read, cache_write, messages]."""
    d7_by_day = d7_by_day or {}
    per_day: dict = {}
    cut7 = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:00:00Z")
    week = [0, 0, 0, 0, 0]
    week_models: dict = {}
    for k, v in st["buckets"].items():
        hour, model = k.split("|", 1)
        day = per_day.setdefault(hour[:10], {})
        m = day.setdefault(model, [0, 0, 0, 0, 0])
        for i, x in enumerate(v):
            m[i] += x
        if hour >= cut7:
            wm = week_models.setdefault(model, [0, 0, 0, 0, 0])
            for i, x in enumerate(v):
                week[i] += x
                wm[i] += x
    out_days = []
    for day in sorted(per_day)[-days:]:
        tot = [sum(m[i] for m in per_day[day].values()) for i in range(5)]
        d7 = d7_by_day.get(day)
        fresh = tot[0] + tot[1] + tot[3]            # tokens that cost real work (cache reads are nearly free)
        out_days.append({
            "day": day, "input": tot[0], "output": tot[1], "cache_read": tot[2], "cache_write": tot[3], "messages": tot[4],
            "cache_hit": cache_hit(tot[0], tot[2], tot[3]), "d7": d7,
            "tokens_per_pct": round(fresh / d7) if d7 and d7 > 0 else None,
            "models": {m: v for m, v in per_day[day].items() if any(v)},
        })
    wd7 = sum(d7_by_day.get(x["day"]) or 0 for x in out_days if x["day"] >= cut7[:10])
    wfresh = week[0] + week[1] + week[3]
    return {
        "days": out_days,
        "week": {"input": week[0], "output": week[1], "cache_read": week[2], "cache_write": week[3], "messages": week[4],
                 "cache_hit": cache_hit(week[0], week[2], week[3]),
                 "tokens_per_pct": round(wfresh / wd7) if wd7 > 0 else None},
        "models": [{"name": m, "tokens": v[0] + v[1] + v[3]} for m, v in
                   sorted(week_models.items(), key=lambda x: -(x[1][0] + x[1][1] + x[1][3])) if v[0] + v[1] + v[3] > 0][:5],
    }
