# -*- coding: utf-8 -*-
"""Widget settings shared by every client (API-2): stored in data/config.json under "widget", next to the
launcher's own keys (lang, setup_done, server_at_login), which are never touched here.

Values are validated against closed lists: a client can only store what the widget knows how to use, never free
text, CSS or HTML. Unknown keys are refused.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path

import claude_usage as cu

CONFIG_NAME = "config.json"
_lock = threading.Lock()
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
THEME_PRESETS = ("claude", "contrast", "colorblind", "mono")
THEME_COLORS = ("five", "seven", "ok", "bad")          # the colours a user may override (THM-1)

DEFAULTS = {"level": "auto", "notes": True, "work_hours": False, "hours": 8, "lang": None,
            "theme": {"preset": "claude", "light": {}, "dark": {}}}


def _level(v):
    if v == "auto" or (isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 9):
        return v
    raise ValueError("level: 'auto' or 1..9")


def _bool(name):
    def check(v):
        if isinstance(v, bool):
            return v
        raise ValueError(f"{name}: true or false")
    return check


def _hours(v):
    if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 24:
        return v
    raise ValueError("hours: 1..24")


def _lang(v):
    if v in ("en", "fr", None):
        return v
    raise ValueError("lang: 'en' or 'fr'")


def _colors(v):
    if not isinstance(v, dict) or any(k not in THEME_COLORS or not isinstance(c, str) or not HEX.match(c) for k, c in v.items()):
        raise ValueError(f"theme colours: {{{', '.join(THEME_COLORS)}}} as #rrggbb")
    return {k: c.lower() for k, c in v.items()}


def _theme(v):
    if not isinstance(v, dict) or set(v) - {"preset", "light", "dark"}:
        raise ValueError("theme: {preset, light, dark}")
    preset = v.get("preset", "claude")
    if preset not in THEME_PRESETS:
        raise ValueError(f"theme.preset: one of {', '.join(THEME_PRESETS)}")
    return {"preset": preset, "light": _colors(v.get("light", {})), "dark": _colors(v.get("dark", {}))}


CHECKS = {"level": _level, "notes": _bool("notes"), "work_hours": _bool("work_hours"), "hours": _hours,
          "lang": _lang, "theme": _theme}


def validate(changes) -> dict:
    """The validated changes, or ValueError with a short reason."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("a JSON object of settings is expected")
    unknown = sorted(set(changes) - set(CHECKS))
    if unknown:
        raise ValueError("unknown setting: " + ", ".join(unknown)[:80])
    return {k: CHECKS[k](v) for k, v in changes.items()}


def _read(data_dir: Path) -> dict:
    try:
        cfg = json.loads((data_dir / CONFIG_NAME).read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def load(data_dir: Path | None = None) -> dict:
    """The widget settings: defaults, overridden by every stored value that is still valid."""
    data_dir = data_dir or cu.DATA_DIR
    stored = _read(data_dir).get("widget")
    out = json.loads(json.dumps(DEFAULTS))
    if isinstance(stored, dict):
        for k, v in stored.items():
            try:
                out.update(validate({k: v}))
            except ValueError:
                pass                                   # a hand-edited or older value: keep the default
    return out


def update(changes, data_dir: Path | None = None) -> dict:
    """Validate and store some settings; returns all of them. The rest of config.json is kept as it is."""
    data_dir = data_dir or cu.DATA_DIR
    clean = validate(changes)
    with _lock:
        cfg = _read(data_dir)
        widget = cfg.get("widget") if isinstance(cfg.get("widget"), dict) else {}
        widget.update(clean)
        cfg["widget"] = widget
        data_dir.mkdir(parents=True, exist_ok=True)
        tmp = data_dir / (CONFIG_NAME + ".tmp")
        tmp.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
        os.replace(tmp, data_dir / CONFIG_NAME)
    return load(data_dir)
