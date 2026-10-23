#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adaptive poller: takes readings in a loop, faster while the quota is moving.

    python poller.py          -> runs until stopped (this is what the background job starts at logon)

Timing (the ladder):
  - a reading that shows a change (5-hour or weekly %) -> next one 30 s later;
  - each reading without change climbs one step: 1 min, 3 min, 5 min, 7 min, then 10 min (and stays there);
  - HTTP 429 (rate limited) -> next one 2 minutes later (or the Retry-After the API asks, if longer),
    without moving on the ladder;
  - expired token (401, or expiresAt already past) -> the poller watches ~/.claude/.credentials.json and
    reads again as soon as Claude Code renews it, instead of waiting for the next step.

Only one poller runs at a time (lock on data/poller.lock). Its state is written to data/poller.json
(next reading time, current step), which the widget and the launcher read.
"""
from __future__ import annotations

import importlib
import json
import os
import signal
import sys
import time
from pathlib import Path

import claude_usage as cu

LADDER_S = (30, 60, 180, 300, 420, 600)   # delay after a change, then after each reading without change
RATE_LIMITED_S = 120                       # delay after HTTP 429
TICK_S = 5                                 # sleep in short slices: survives sleep/hibernate and clock changes

AUTH_CODES = ("auth", "token_expired")     # fixed by Claude Code renewing the credentials file

LOCK_NAME = "poller.lock"
STATE_NAME = "poller.json"


# --------------------------------------------------------------------------- timing

def next_delay(step: int, changed: bool, error_code: str | None, retry_after=None) -> tuple[float, int, str]:
    """(seconds until the next reading, new step on the ladder, reason) after one reading."""
    if error_code == "rate_limited":
        wait = max(RATE_LIMITED_S, cu.num(retry_after) or 0)
        return wait, step, "rate_limited"
    if changed:
        return LADDER_S[0], 0, "changed"
    step = min(step + 1, len(LADDER_S) - 1)
    return LADDER_S[step], step, "error" if error_code else "unchanged"


def signature(state: dict | None) -> tuple | None:
    """What counts as 'a change': the 5-hour and weekly percentages."""
    if not state:
        return None
    return ((state.get("five_hour") or {}).get("pct"), (state.get("seven_day") or {}).get("pct"))


def credentials_stamp():
    """Changes whenever Claude Code rewrites its credentials file (None when there is no file)."""
    try:
        st = cu.credentials_path().stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return None


def read_state(data_dir: Path) -> dict | None:
    try:
        return json.loads((data_dir / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------- single instance

def _try_lock(fh) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def acquire_lock(data_dir: Path):
    """Open and lock data/poller.lock; returns the open file (keep it), or None if another poller holds it."""
    data_dir.mkdir(parents=True, exist_ok=True)
    fh = open(data_dir / LOCK_NAME, "a+")
    if _try_lock(fh):
        return fh
    fh.close()
    return None


def running(data_dir: Path = cu.DATA_DIR) -> dict | None:
    """The state of the poller that is running right now (data/poller.json), or None if none runs."""
    fh = acquire_lock(data_dir)
    if fh is not None:          # we could take the lock: nobody holds it
        fh.close()
        return None
    try:
        return json.loads((data_dir / STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def stop(data_dir: Path = cu.DATA_DIR) -> bool:
    """Stop the running poller, if any. True when none is left running."""
    info = running(data_dir)
    if info is None:
        return True
    pid = info.get("pid")
    if not pid:
        return False
    try:
        os.kill(int(pid), signal.SIGTERM)        # the pid comes from the poller that holds the lock
    except OSError:
        pass
    for _ in range(20):
        if running(data_dir) is None:
            return True
        time.sleep(0.15)
    return False


# --------------------------------------------------------------------------- loop

def write_state(data_dir: Path, **fields) -> None:
    try:
        cu._atomic_write(data_dir / STATE_NAME, json.dumps(fields, indent=1))
    except OSError:
        pass


def loop(data_dir: Path = cu.DATA_DIR) -> int:
    global cu
    lock = acquire_lock(data_dir)
    if lock is None:
        print("A poller is already running.")
        return 0
    if hasattr(signal, "SIGTERM") and os.name != "nt":
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))   # systemctl stop / kill: still log "stopped"
    started = cu.iso(cu.now_utc())
    cu.log(data_dir, f"POLLER started (pid {os.getpid()}), ladder {'/'.join(str(s) for s in LADDER_S)} s")
    step = len(LADDER_S) - 1
    try:
        while True:
            before = signature(read_state(data_dir))      # also sees readings made by the Refresh button
            try:
                cu = importlib.reload(cu)                 # picks up script updates without restarting
                _, error, state = cu.run(data_dir)
                code = state.get("error_code")
                last = (state.get("diagnostics") or {}).get("last") or {}
                after = signature(state) if error is None else before
                delay, step, reason = next_delay(step, before is not None and after != before, code, last.get("retry_after"))
            except Exception as e:                        # never let one bad reading kill the loop
                cu.log(data_dir, f"POLLER unexpected error: {e!r}")
                code = "crash"
                delay, step, reason = next_delay(step, False, code)
            if reason == "rate_limited":
                cu.log(data_dir, f"POLLER rate limited: next reading in {int(delay)} s")
            watch = credentials_stamp() if code in AUTH_CODES else None
            due = time.time() + delay
            write_state(data_dir, pid=os.getpid(), started_at=started, last_at=cu.iso(cu.now_utc()),
                        next_at=cu.iso(cu.datetime.fromtimestamp(due, cu.timezone.utc)),
                        delay_s=delay, step=step, reason=reason, ladder_s=list(LADDER_S))
            while time.time() < due:
                time.sleep(min(TICK_S, max(0.0, due - time.time())))
                if watch is not None and credentials_stamp() != watch:
                    cu.log(data_dir, "POLLER credentials file renewed: reading now")
                    time.sleep(1)                         # let Claude Code finish writing it
                    break
    except KeyboardInterrupt:
        return 0
    finally:
        cu.log(data_dir, "POLLER stopped")
        lock.close()


if __name__ == "__main__":
    sys.exit(loop())
