#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Usage Tracker : releve du quota Claude (fenetre 5 heures et 7 jours).

    python claude_usage.py        -> un releve (c'est ce que lance la tache planifiee)

A chaque releve :
  - data/usage.csv          : une ligne ajoutee (historique complet)
  - data/latest.json        : dernier etat + historique recent + ratio estime
  - data/latest.js          : la meme chose, lisible par web/index.html (meme ouvert en file://)
  - data/last_response.json : reponse brute de l'API (pour debug)
  - data/tracker.log        : journal (utile car la tache tourne sans console)

Source : l'endpoint que Claude Code utilise pour /status (non documente officiellement,
il peut changer). Le jeton OAuth est lu dans ~/.claude/.credentials.json
(%USERPROFILE%\\.claude\\.credentials.json sous Windows).
Uniquement la bibliotheque standard : rien a installer.
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

# Hypothese de depart : une fenetre 5 h consommee a 100 % ~ 10 % du quota hebdo.
# Remplacee automatiquement par une estimation des que l'historique le permet.
DEFAULT_RATIO = 10.0
MIN_5H_POINTS_FOR_RATIO = 20.0   # cumul de % 5 h observes avant de faire confiance a l'estimation
HISTORY_DAYS = 8                 # historique embarque dans latest.js pour les futurs graphiques
SAME_WINDOW_TOLERANCE_S = 300    # deux resets_at a moins de 5 min = meme fenetre
MAX_LOG_BYTES = 200_000


class TrackerError(Exception):
    """Erreur attendue (jeton absent, reseau, format) : journalisee, pas de traceback."""


# --------------------------------------------------------------------------- dates

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value) -> datetime | None:
    """ISO 8601 (avec ou sans fraction / Z) ou epoch secondes -> datetime UTC."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    s = str(value).strip().replace("Z", "+00:00")
    s = re.sub(r"(\.\d+)(?=[+-]\d\d:\d\d$|$)", "", s)  # Python < 3.11 n'aime pas toutes les fractions
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
            f"Identifiants Claude Code introuvables ({path}). "
            "Lance Claude Code et connecte-toi (/login) avec ton abonnement Claude."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise TrackerError(f"Lecture impossible de {path} : {e}")
    token = (data.get("claudeAiOauth") or {}).get("accessToken")
    if not token:
        raise TrackerError("Pas de accessToken dans .credentials.json : il faut une connexion par abonnement, pas par cle API.")
    return token


def fetch_usage(token: str) -> dict:
    req = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
            "User-Agent": "claude-usage-tracker/0.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        if e.code in (401, 403):
            raise TrackerError(
                f"Acces refuse ({e.code}) : le jeton a sans doute expire. "
                f"Ouvre Claude Code une fois, il le rafraichit tout seul. Detail : {body}"
            )
        raise TrackerError(f"Erreur HTTP {e.code} : {body}")
    except urllib.error.URLError as e:
        raise TrackerError(f"Reseau indisponible : {e.reason}")
    except ValueError as e:
        raise TrackerError(f"Reponse non JSON : {e}")


def window(payload: dict, key: str) -> tuple[float | None, datetime | None]:
    w = payload.get(key) or {}
    if not isinstance(w, dict):
        return None, None
    return num(w.get("utilization")), parse_dt(w.get("resets_at"))


def build_row(payload: dict, ts: datetime) -> dict:
    f5, r5 = window(payload, "five_hour")
    f7, r7 = window(payload, "seven_day")
    if f5 is None and f7 is None:
        raise TrackerError(f"Reponse inattendue, cles recues : {sorted(payload)[:12]}")
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


# --------------------------------------------------------------------------- stockage

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
    Combien de % hebdo coute une fenetre 5 h pleine.
    On cumule, entre releves consecutifs dans les MEMES fenetres (pas de reset entre deux),
    la hausse du 5 h et la hausse du 7 j : ratio = 100 * somme(d7) / somme(d5).
    Retourne (ratio ou None si pas assez de donnees, cumul de points 5 h observes).
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
    """Repartition de l'usage hebdo par produit (Claude Code, Chats, Cowork...), en % de ce qui a ete consomme."""
    b = payload.get("seven_day_breakdown")
    if not isinstance(b, dict) or not isinstance(b.get("rows"), list):
        return None
    rows = [
        {"key": r.get("key"), "name": r.get("display_name") or r.get("key"), "pct": num(r.get("percent"))}
        for r in b["rows"] if isinstance(r, dict)
    ]
    return {"as_of": b.get("as_of"), "rows": rows}


def previous_breakdown(data_dir: Path) -> dict | None:
    try:
        return json.loads((data_dir / "latest.json").read_text(encoding="utf-8")).get("breakdown")
    except (OSError, ValueError, AttributeError):
        return None


def write_outputs(data_dir: Path, rows: list[dict], now: datetime, error: str | None,
                  breakdown: dict | None = None) -> dict:
    last = rows[-1] if rows else None
    ratio, ratio_points = estimate_ratio(rows)
    cutoff = now - timedelta(days=HISTORY_DAYS)
    history = [
        {"t": r["timestamp"], "h5": num(r.get("five_hour_pct")), "d7": num(r.get("seven_day_pct"))}
        for r in rows if parse_dt(r["timestamp"]) >= cutoff
    ]
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


# --------------------------------------------------------------------------- point d'entree

def run(data_dir: Path = DATA_DIR, payload: dict | None = None, now: datetime | None = None):
    """Un releve complet. `payload` permet aux tests d'injecter une reponse API."""
    now = now or now_utc()
    data_dir.mkdir(parents=True, exist_ok=True)
    row, error, breakdown = None, None, None
    try:
        if payload is None:
            payload = fetch_usage(read_token())
        _atomic_write(data_dir / "last_response.json", json.dumps(payload, ensure_ascii=False, indent=2))
        row = build_row(payload, now)
        append_csv(data_dir / "usage.csv", row)
        breakdown = extract_breakdown(payload)
    except TrackerError as e:
        error = str(e)
    if breakdown is None:
        breakdown = previous_breakdown(data_dir)
    state = write_outputs(data_dir, load_history(data_dir / "usage.csv"), now, error, breakdown)
    if error:
        log(data_dir, "ERREUR " + error)
    else:
        log(data_dir, f"OK 5h={row['five_hour_pct']}% 7j={row['seven_day_pct']}%")
    return row, error, state


def _fmt_reset(s: str) -> str:
    d = parse_dt(s)
    if not d:
        return "pas de fenetre active"
    left = d - now_utc()
    h, m = divmod(max(0, int(left.total_seconds() // 60)), 60)
    j, h = divmod(h, 24)
    when = d.astimezone().strftime("%a %d/%m %H:%M")
    return f"reset {when} (dans {f'{j} j ' if j else ''}{h} h {m:02d})"


def main() -> int:
    row, error, state = run()
    if error:
        print("ERREUR :", error)
        return 1
    print(f"5 heures : {row['five_hour_pct'] or '-'} %  | {_fmt_reset(row['five_hour_resets_at'])}")
    print(f"7 jours  : {row['seven_day_pct'] or '-'} %  | {_fmt_reset(row['seven_day_resets_at'])}")
    r = state["ratio_estimate"]
    print(f"Releves enregistres : {state['samples']}  | ratio 5h->7j : "
          + (f"{r} % (estime)" if r else f"{DEFAULT_RATIO} % (hypothese, pas encore assez de donnees)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
