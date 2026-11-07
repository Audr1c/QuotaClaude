# -*- coding: utf-8 -*-
"""
Local token counters read from Claude Code's transcripts (~/.claude/projects/**/*.jsonl).

Why: the quota endpoint only gives percentages. The transcripts give the real token volumes, so we can show the
cache hit rate, the share of thinking, what sub-agents cost, and how many tokens one percent of the weekly quota is worth.

Privacy: a transcript holds whole conversations. Only `message.id`, `message.model`, `timestamp`, the `isSidechain`
flag and the numbers of `message.usage` are ever read out of a line. What is written is counters, message ids (random
strings from the API) and, per transcript file, a hash of its path: never the text, never a project or folder name.
Nothing here is served except the aggregated counters (the "tokens" part of latest.json).

How: each file is read from the byte offset where the last scan stopped (the first scan reads everything, later
ones only what was appended). Claude Code writes the same assistant message several times while it streams (and a
resumed session or a sub-agent file can repeat it): every message id is counted ONCE, the copy with the most output
tokens (the most complete one) wins, whatever the file or the position. Because of that, re-reading a file from the
start (it was replaced or truncated) never counts anything twice.
Counts go into hourly (UTC) buckets per model and per agent kind ("main" session or "sub" = sub-agent), kept in
data/transcripts_state.json and exported to data/tokens.csv.
A bucket is [input, output, cache_read, cache_write, messages, thinking, cache_write_1h]; `thinking` is part of
`output` and `cache_write_1h` is the part of `cache_write` kept for 1 hour (the rest is the 5-minute cache, cheaper to write).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ["input", "output", "cache_read", "cache_write", "messages", "thinking", "cache_write_1h"]
STATE_NAME, CSV_NAME = "transcripts_state.json", "tokens.csv"
VERSION = 4                         # bumped when the state layout changes: the old state is dropped and rebuilt
HEAD = 64                           # bytes of a file's start kept as a fingerprint, to notice a replaced file
_BAD_MODEL = re.compile(r"[^A-Za-z0-9._:/-]")


def projects_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECTS_DIR") or Path.home() / ".claude" / "projects")


def _hour(ts) -> str | None:
    try:
        # Python < 3.11 only accepts 3 or 6 fraction digits: drop the fraction, only the hour is kept anyway
        d = datetime.fromisoformat(re.sub(r"\.\d+(?=[+-]\d\d:\d\d$|$)", "", ts.replace("Z", "+00:00")))
    except (ValueError, AttributeError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")


def _n(v) -> int:
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else 0


def _model(v) -> str:
    """The model name goes into a file and a JSON key: keep it to plain characters (a '|' or a newline would break both)."""
    return _BAD_MODEL.sub("?", v)[:64] if isinstance(v, str) and v else "?"


def parse_line(raw: bytes):
    """(message_id, hour, model, agent, [input, output, cache_read, cache_write, thinking, cache_write_1h]) or None.
    Reads nothing but those fields."""
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
        details = u.get("output_tokens_details")
        cc = u.get("cache_creation")
        vals = [_n(u.get("input_tokens")), _n(u.get("output_tokens")),
                _n(u.get("cache_read_input_tokens")), _n(u.get("cache_creation_input_tokens")),
                _n(details.get("thinking_tokens")) if isinstance(details, dict) else 0,
                _n(cc.get("ephemeral_1h_input_tokens")) if isinstance(cc, dict) else 0]
        if not any(vals[:4]):                       # "<synthetic>" placeholders and the like: no tokens, not a message
            return None
        return (mid[:80] if isinstance(mid, str) and mid else None, hour, _model(m.get("model")),
                "sub" if d.get("isSidechain") is True else "main", vals)
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def _add(buckets: dict, key: str, vals: list, sign: int = 1) -> None:
    b = buckets.setdefault(key, [0] * 7)
    for i in range(4):
        b[i] += sign * vals[i]
    b[4] += sign
    b[5] += sign * vals[4]
    b[6] += sign * vals[5]


def _split(key: str):
    hour, model, agent = key.split("|", 2)
    return hour, model, agent


def _fresh() -> dict:
    return {"v": VERSION, "files": {}, "seen": {}, "buckets": {}}


def _valid(st) -> bool:
    """A damaged or hand-edited state is thrown away (and rebuilt from the transcripts) instead of breaking every scan."""
    try:
        if st["v"] != VERSION:
            return False
        if not all(isinstance(f, dict) and isinstance(f.get("o"), int) and isinstance(f.get("h", ""), str)
                   for f in st["files"].values()):
            return False
        if not all(isinstance(b, list) and len(b) == 7 and all(isinstance(x, int) for x in b) and k.count("|") == 2
                   for k, b in st["buckets"].items()):
            return False
        return all(isinstance(s, list) and len(s) == 2 and isinstance(s[0], str) and s[0].count("|") == 2
                   and isinstance(s[1], list) and len(s[1]) == 6 and all(isinstance(x, int) for x in s[1])
                   for s in st["seen"].values())
    except (KeyError, TypeError, AttributeError):
        return False


def _key(root: Path, path: Path) -> str:
    """Per-file key in the state: a hash, so that no project or folder name is ever written."""
    return hashlib.sha1(str(path.relative_to(root)).encode("utf-8", "replace")).hexdigest()[:16]


def _count(st: dict, mid, hour: str, model: str, agent: str, vals: list) -> None:
    buckets, seen = st["buckets"], st["seen"]
    key = f"{hour}|{model}|{agent}"
    old = seen.get(mid) if mid else None
    if old:
        if vals[1] < old[1][1]:                     # an earlier, less complete copy of a message already counted
            return
        _add(buckets, old[0], old[1], -1)
    _add(buckets, key, vals)
    if mid:
        seen[mid] = [key, vals]


def scan(data_dir: Path, root: Path | None = None) -> dict:
    """Read what was appended to the transcripts since the last scan and return the state (also saved)."""
    root = root or projects_dir()
    sp = data_dir / STATE_NAME
    try:
        st = json.loads(sp.read_text(encoding="utf-8"))
        if not _valid(st):
            raise ValueError
    except (OSError, ValueError):
        st = _fresh()
    files = st["files"]
    changed = False
    for path in (root.rglob("*.jsonl") if root.is_dir() else []):
        try:
            size = path.stat().st_size
            key = _key(root, path)
        except (OSError, ValueError):
            continue
        f = files.get(key) or {"o": 0, "h": ""}
        if size == f["o"] and f["o"] > 0 and key in files:
            continue
        try:
            with path.open("rb") as fh:
                head = fh.read(HEAD)
                hs = hashlib.sha1(head).hexdigest()[:16]
                if size < f["o"] or (f["h"] and hs != f["h"]):       # replaced or truncated: read it again from the start
                    f = {"o": 0, "h": ""}
                fh.seek(f["o"])
                chunk = fh.read(max(size - f["o"], 0))
        except OSError:
            continue
        end = chunk.rfind(b"\n") + 1                # never consume a half-written last line
        for raw in chunk[:end].split(b"\n"):
            r = parse_line(raw)
            if r:
                _count(st, *r)
        files[key] = {"o": f["o"] + end, "h": hs if f["o"] + end >= HEAD else ""}
        changed = True
    if changed or not sp.exists():
        _write(data_dir, st)
    return st


def _atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")   # own name: the poller and the server never share a temp file
    tmp.write_bytes(text.encode("utf-8"))                   # exact bytes (write_text(newline=) needs Python 3.10)
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:                     # Windows: a sync tool or antivirus has the file open right now
            if attempt == 19:
                raise
            time.sleep(0.1)


def _write(data_dir: Path, st: dict) -> None:
    try:
        _atomic(data_dir / STATE_NAME, json.dumps(st, separators=(",", ":")))
        rows = ["hour,model,agent," + ",".join(FIELDS)]
        for k in sorted(st["buckets"]):
            hour, model, agent = _split(k)
            rows.append(",".join([hour, model, agent] + [str(x) for x in st["buckets"][k]]))
        _atomic(data_dir / CSV_NAME, "\n".join(rows) + "\n")
    except OSError:
        pass                                        # still locked: the next scan retries


def cache_hit(inp: float, cache_read: float, cache_write: float):
    """Share of the prompt tokens served from the cache, in %."""
    total = inp + cache_read + cache_write
    return round(100.0 * cache_read / total, 1) if total > 0 else None


def _sum(a: list, b: list) -> None:
    for i, x in enumerate(b):
        a[i] += x


def summary(st: dict, now: datetime, d7_by_day: dict | None = None, days: int = 120) -> dict:
    """What the widget shows. Per UTC day: totals, per model and per agent kind ("main" / "sub"), with the weekly %
    of that day. Counters are [input, output, cache_read, cache_write, messages, thinking, cache_write_1h]."""
    d7_by_day = d7_by_day or {}
    per_day: dict = {}
    cut7 = (now - timedelta(hours=24 * 7)).strftime("%Y-%m-%dT%H:00:00Z")
    week = [0] * 7
    week_agents: dict = {}
    for k, v in st["buckets"].items():
        hour, model, agent = _split(k)
        day = per_day.setdefault(hour[:10], {"models": {}, "agents": {}})
        _sum(day["models"].setdefault(model, [0] * 7), v)
        _sum(day["agents"].setdefault(agent, [0] * 7), v)
        if hour >= cut7:
            _sum(week, v)
            _sum(week_agents.setdefault(agent, [0] * 7), v)
    out_days = []
    for day in sorted(per_day)[-days:]:
        tot = [0] * 7
        for v in per_day[day]["models"].values():
            _sum(tot, v)
        d7 = d7_by_day.get(day)
        fresh = tot[0] + tot[1] + tot[3]            # tokens that cost real work (cache reads are nearly free)
        out_days.append({
            "day": day, "input": tot[0], "output": tot[1], "cache_read": tot[2], "cache_write": tot[3], "messages": tot[4],
            "thinking": tot[5], "cache_write_1h": tot[6], "cache_hit": cache_hit(tot[0], tot[2], tot[3]), "d7": d7,
            "tokens_per_pct": round(fresh / d7) if d7 and d7 > 0 else None,
            "models": {m: v for m, v in per_day[day]["models"].items() if any(v)},
            "agents": {a: v for a, v in per_day[day]["agents"].items() if any(v)},
        })
    wd7 = sum(d7_by_day.get(x["day"]) or 0 for x in out_days if x["day"] >= cut7[:10])
    wfresh = week[0] + week[1] + week[3]
    sub = week_agents.get("sub", [0] * 7)
    return {
        "days": out_days,
        "week": {"input": week[0], "output": week[1], "cache_read": week[2], "cache_write": week[3], "messages": week[4],
                 "thinking": week[5], "cache_write_1h": week[6], "cache_hit": cache_hit(week[0], week[2], week[3]),
                 "tokens_per_pct": round(wfresh / wd7) if wd7 > 0 else None,
                 "sub_share": round(100.0 * (sub[0] + sub[1] + sub[3]) / wfresh, 1) if wfresh else None},
    }
