#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local server for the widget (Windows, Linux, macOS; standard library only).

    python server.py                    -> http://127.0.0.1:8765/
    python server.py --open             -> same, and opens the browser
                                           (if a server is already running: only opens the browser)
    python server.py --open --lang fr   -> opens the widget in French (fr or en)

Routes:
    GET  /                   -> redirects to /web/index.html   (also at http://claude.localhost:8765/)
    GET  /web/...            -> widget files
    GET  /data/latest.json   -> latest state (also latest.js)
    GET  /data/poller.json   -> state of the adaptive poller (when the next reading is due)
    GET  /api/ping           -> identifies this server (and its process id, so the launcher can stop it)
    POST /api/refresh        -> takes a reading now and returns the new state
  Read API, version 1 (the same data for every client: widget, VS Code, phone; never the Claude token):
    GET  /api/v1/latest              -> data/latest.json (field "schema": 1)
    GET  /api/v1/history?since=ISO   -> every reading since then: [{t, h5, d7, r5, r7}]
    GET  /api/v1/tokens?since=DAY    -> token counters per day since YYYY-MM-DD
    GET  /api/v1/model[?hours=N]     -> the gauge values, limits and paces computed here (model.py), ready to draw
    GET  /api/v1/config              -> shared widget settings (settings.py)
    POST /api/v1/config              -> change some of them: JSON object, validated; same Origin rule as /api/refresh

Listens on 127.0.0.1 only: nothing is exposed to the network. Other protections: Host check (DNS rebinding),
Sec-Fetch-Site check (a page of another site cannot read /data/ with <script src> or fetch), Origin required on POST,
at most one real reading every MIN_REFRESH_GAP_S seconds, no path outside web/, security headers (CSP, nosniff...).
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import claude_usage as cu
import model
import settings

ROOT = Path(__file__).resolve().parent
WEB = (ROOT / "web").resolve()
APP_ID = "claude-usage-tracker"
DEFAULT_PORT = 8765
_refresh_lock = threading.Lock()
MIN_REFRESH_GAP_S = 20                      # POST /api/refresh inside this gap answers with the saved state, no API call
_last_refresh = [0.0]
CONFIG_POSTS = (20, 10.0)                   # at most 20 settings changes per 10 s (a slider sends a few per second)
_config_posts: list = []
MAX_BODY = 4096

# Sent with every answer. The page has no inline script or handler, so scripts can be limited to our own files.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


def web_file(rel: str) -> Path | None:
    """The file of web/ for a request path, or None. The path is checked BEFORE it touches the file system: on Windows
    a path like //host/share replaces the base folder and resolving it would open a network connection."""
    if not rel or any(c in rel for c in ("\\", ":", "%", "\0")) or rel.startswith("/"):
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        return None
    f = WEB.joinpath(*parts).resolve()
    return f if WEB in f.parents and f.is_file() else None

# Fixed table: on Windows, mimetypes reads the registry and sometimes serves .js as text/plain.
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "ClaudeUsage/1.1.1"
    sys_version = ""                        # do not announce the Python version
    timeout = 15                            # a client that opens a connection and says nothing does not keep a thread forever

    def log_message(self, fmt, *args):  # silent (pythonw has no console)
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy", CSP)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), TYPES[".json"])

    def _not_found(self):
        self._json(404, {"error": "not found"})

    def _host_ok(self) -> bool:
        """Anti DNS-rebinding: only the local address is accepted in the Host header.
        Without this, a remote page could point its domain name at 127.0.0.1
        and query this server from the browser. claude.localhost is an easier address to remember: browsers
        resolve every *.localhost name to this machine without asking any DNS server."""
        port = self.server.server_address[1]
        return (self.headers.get("Host") or "").lower() in (f"127.0.0.1:{port}", f"localhost:{port}", f"claude.localhost:{port}")

    def _fetch_ok(self) -> bool:
        """Browsers say where a request comes from (Sec-Fetch-Site). A page of another site, or of another port on this
        machine, must not read our data: only our own pages ("same-origin") and the address bar ("none") may."""
        return self.headers.get("Sec-Fetch-Site") in (None, "same-origin", "none")

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "host refused"})
        path = self.path.split("?", 1)[0]
        if path == "/api/ping":                 # the launcher asks without browser headers; it only says who we are
            return self._json(200, {"app": APP_ID, "pid": os.getpid()})
        if not self._fetch_ok():
            return self._json(403, {"error": "cross-site request refused"})
        if path.startswith("/api/v1/"):
            return self._api_get(path[len("/api/v1/"):], self._query())
        if path in ("/", "/index.html", "/web", "/web/"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            target = "/web/index.html" + ("?" + query if query else "")
            return self._send(302, b"", "text/plain", {"Location": target})
        if path in ("/data/latest.json", "/data/latest.js", "/data/poller.json"):
            f = cu.DATA_DIR / path.rsplit("/", 1)[1]
        elif path.startswith("/web/"):
            f = web_file(path[len("/web/"):])
            if f is None:
                return self._not_found()
        else:
            return self._not_found()
        if not f.is_file():
            return self._not_found()
        self._send(200, f.read_bytes(), TYPES.get(f.suffix.lower(), "application/octet-stream"))

    def _query(self) -> dict:
        from urllib.parse import parse_qs
        q = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        return {k: v[0] for k, v in q.items()}

    def _api_get(self, name: str, q: dict):
        state = self._saved_state()
        if name == "latest":
            return self._json(200, state) if state else self._json(404, {"error": "no reading yet"})
        if name == "history":
            # an unencoded "+" of the time zone arrives as a space
            since = cu.parse_dt(q["since"].replace(" ", "+")) if q.get("since") else None
            if q.get("since") and since is None:
                return self._json(400, {"error": "since: an ISO date-time"})
            rows = cu.load_history(cu.DATA_DIR / "usage.csv")
            out = [{"t": r["timestamp"], "h5": cu.num(r.get("five_hour_pct")), "d7": cu.num(r.get("seven_day_pct")),
                    "r5": r.get("five_hour_resets_at") or None, "r7": r.get("seven_day_resets_at") or None}
                   for r in rows if since is None or cu.parse_dt(r["timestamp"]) >= since]
            return self._json(200, {"schema": 1, "readings": out})
        if name == "tokens":
            since = q.get("since", "")
            if since and not (len(since) == 10 and since[4] == "-" and since[7] == "-" and since.replace("-", "").isdigit()):
                return self._json(400, {"error": "since: YYYY-MM-DD"})
            tok = (state or {}).get("tokens") or {"days": [], "week": None}
            return self._json(200, {"schema": 1, "days": [d for d in tok.get("days", []) if d.get("day", "") >= since],
                                    "week": tok.get("week")})
        if name == "model":
            prefs = settings.load()
            hours = (prefs["hours"] if prefs["work_hours"] else 24)
            if "hours" in q:
                if not q["hours"].isdigit() or not 1 <= int(q["hours"]) <= 24:
                    return self._json(400, {"error": "hours: 1..24"})
                hours = int(q["hours"])
            m = model.compute(state, time.time() * 1000, hours) if state else None
            return self._json(200, m) if m else self._json(404, {"error": "no reading yet"})
        if name == "config":
            return self._json(200, {"schema": 1, "widget": settings.load()})
        return self._not_found()

    def _origin_ok(self) -> bool:
        # Only the widget itself: a browser always sends Origin on a POST, so a missing one is not the widget.
        return self.headers.get("Origin") == f"http://{self.headers.get('Host', '')}" and self._fetch_ok()

    def _post_config(self):
        now = time.monotonic()
        _config_posts[:] = [t for t in _config_posts if now - t < CONFIG_POSTS[1]]
        if len(_config_posts) >= CONFIG_POSTS[0]:
            return self._json(429, {"error": "too many changes, wait a few seconds"})
        _config_posts.append(now)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n <= 0 or n > MAX_BODY:
            return self._json(400, {"error": f"a JSON body of at most {MAX_BODY} bytes is expected"})
        try:
            changes = json.loads(self.rfile.read(n).decode("utf-8"))
            return self._json(200, {"schema": 1, "widget": settings.update(changes)})
        except (ValueError, UnicodeDecodeError) as e:
            return self._json(400, {"error": str(e)[:200]})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "host refused"})
        path = self.path.split("?", 1)[0]
        if path not in ("/api/refresh", "/api/v1/config"):
            return self._not_found()
        if not self._origin_ok():
            return self._json(403, {"error": "origin refused"})
        if path == "/api/v1/config":
            return self._post_config()
        with _refresh_lock:
            if time.monotonic() - _last_refresh[0] < MIN_REFRESH_GAP_S:     # clicks in a row must not turn into 429s
                return self._json(200, {"ok": True, "cached": True, "error": None, "state": self._saved_state()})
            importlib.reload(cu)          # picks up script updates without restarting the server
            row, error, state = cu.run()
            _last_refresh[0] = time.monotonic()
        self._json(200 if error is None else 502, {"ok": error is None, "error": error, "state": state})

    def _saved_state(self):
        try:
            return json.loads((cu.DATA_DIR / "latest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None


def ping(port: int) -> dict | None:
    """Return the /api/ping answer if OUR server listens on `port`, else None."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # ignore system proxies
    try:
        with opener.open(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            data = json.load(r)
            return data if data.get("app") == APP_ID else None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Local server for the Claude usage widget")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--open", action="store_true", help="open the widget in the browser")
    ap.add_argument("--lang", choices=("en", "fr"), help="language the widget opens in")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}/web/index.html" + (f"?lang={args.lang}" if args.lang else "")

    if ping(args.port):
        print("Server already running:", url)
        if args.open:
            webbrowser.open(url)
        return 0
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as e:
        print(f"Cannot listen on port {args.port}: {e}. Try --port 8766.")
        return 1
    print(f"Widget: {url}   (Ctrl+C to stop)")
    if args.open:
        threading.Timer(0.4, webbrowser.open, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
