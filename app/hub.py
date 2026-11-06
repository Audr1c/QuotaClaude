# -*- coding: utf-8 -*-
"""Hub (HUB-1, option A): an always-on machine (NAS, small server) that keeps the history and serves the widget and the
API to every device, while the PC where Claude Code is signed in keeps doing the readings and PUSHES each one to it.
The Claude token never leaves the PC; the hub only ever sees quota percentages and reset times.

    PC  : poller -> claude_usage.run -> data/usage.csv  --push-->  hub: POST /api/readings -> its data/usage.csv
    hub : server.py --bind 0.0.0.0 --token-file data/api_token   (every request then needs the API token)

The API token of the tracker is NOT the Claude token: it is a random secret made here, stored with 0600 rights.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import urllib.request
from pathlib import Path

import claude_usage as cu

PUSH_TIMEOUT_S = 5
ROW_FIELDS = ("timestamp", "five_hour_pct", "five_hour_resets_at", "seven_day_pct", "seven_day_resets_at",
              "seven_day_opus_pct", "seven_day_sonnet_pct")


# --------------------------------------------------------------------------- tokens

def ensure_token(path: Path) -> str:
    """Read the API token at `path`, creating a random one (rights 0600) the first time."""
    try:
        tok = path.read_text(encoding="utf-8").strip()
        if len(tok) >= 20:
            return tok
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_urlsafe(32)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(tok + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return tok


def same_token(given: str | None, expected: str | None) -> bool:
    return bool(given and expected) and hmac.compare_digest(given.encode(), expected.encode())


# --------------------------------------------------------------------------- PC side: push each reading

def push_config(data_dir: Path) -> dict | None:
    """{"url", "token"} when this PC pushes its readings to a hub (run.py hub --url ...), else None."""
    try:
        cfg = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
        url = (cfg.get("hub") or {}).get("url")
        tok = (data_dir / "hub_token").read_text(encoding="utf-8").strip()
    except (OSError, ValueError, AttributeError):
        return None
    return {"url": url.rstrip("/"), "token": tok} if url and tok else None


def push(data_dir: Path, row: dict) -> str | None:
    """Send one reading to the hub. Returns None when done, or a short error (logged by the caller, never raised)."""
    hub = push_config(data_dir)
    if not hub:
        return None
    body = json.dumps({"row": {k: row.get(k, "") for k in ROW_FIELDS}}).encode("utf-8")
    req = urllib.request.Request(hub["url"] + "/api/readings", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + hub["token"]})
    try:
        with urllib.request.urlopen(req, timeout=PUSH_TIMEOUT_S) as r:
            return None if r.status == 200 else f"HTTP {r.status}"
    except Exception as e:                             # the reading itself is saved locally anyway
        return type(e).__name__ + (f" {e.code}" if hasattr(e, "code") else "")


# --------------------------------------------------------------------------- hub side: receive

def _pct(v):
    if v in ("", None):
        return ""
    f = float(v)
    if not 0 <= f <= 1000:
        raise ValueError("percentage out of range")
    return f"{f:g}"


def clean_row(raw) -> dict:
    """A reading sent by a PC, checked field by field (anything else is refused)."""
    if not isinstance(raw, dict) or set(raw) - set(ROW_FIELDS):
        raise ValueError("row: the fields of usage.csv only")
    ts = cu.parse_dt(raw.get("timestamp"))
    if ts is None:
        raise ValueError("row.timestamp: an ISO date-time")
    out = {"timestamp": cu.iso(ts)}
    for k in ("five_hour_pct", "seven_day_pct", "seven_day_opus_pct", "seven_day_sonnet_pct"):
        out[k] = _pct(raw.get(k))
    for k in ("five_hour_resets_at", "seven_day_resets_at"):
        v = raw.get(k) or ""
        if v and cu.parse_dt(v) is None:
            raise ValueError(f"row.{k}: an ISO date-time")
        out[k] = cu.iso(cu.parse_dt(v)) if v else ""
    if out["five_hour_pct"] == "" and out["seven_day_pct"] == "":
        raise ValueError("row: no percentage")
    return out


def receive(data_dir: Path, payload) -> dict:
    """Store a pushed reading (once: same timestamp = already there) and rebuild latest.json. Returns {added, samples}."""
    if not isinstance(payload, dict):
        raise ValueError("a JSON object {row} is expected")
    row = clean_row(payload.get("row"))
    rows = cu.load_history(data_dir / "usage.csv")
    added = not any(r["timestamp"] == row["timestamp"] for r in rows)
    if added:
        cu.append_csv(data_dir / "usage.csv", row)
        rows = cu.load_history(data_dir / "usage.csv")
        cu.write_outputs(data_dir, rows, cu.now_utc(), None, cu.previous_breakdown(data_dir))
    return {"added": added, "samples": len(rows)}
