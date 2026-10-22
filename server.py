#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local server for the widget (Windows, Linux, macOS; standard library only).

    python server.py                    -> http://127.0.0.1:8765/
    python server.py --open             -> same, and opens the browser
                                           (if a server is already running: only opens the browser)
    python server.py --open --lang fr   -> opens the widget in French (fr or en)

Routes:
    GET  /                   -> redirects to /web/index.html
    GET  /web/...            -> widget files
    GET  /data/latest.json   -> latest state (also latest.js)
    GET  /api/ping           -> identifies this server (and its process id, so the launcher can stop it)
    POST /api/refresh        -> takes a reading now and returns the new state

Listens on 127.0.0.1 only: nothing is exposed to the network.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import claude_usage as cu

ROOT = Path(__file__).resolve().parent
WEB = (ROOT / "web").resolve()
APP_ID = "claude-usage-tracker"
DEFAULT_PORT = 8765
_refresh_lock = threading.Lock()

# Fixed table: on Windows, mimetypes reads the registry and sometimes serves .js as text/plain.
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "ClaudeUsage/0.3"

    def log_message(self, fmt, *args):  # silent (pythonw has no console)
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
        and query this server from the browser."""
        port = self.server.server_address[1]
        return (self.headers.get("Host") or "").lower() in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "host refused"})
        path = self.path.split("?", 1)[0]
        if path == "/api/ping":
            return self._json(200, {"app": APP_ID, "pid": os.getpid()})
        if path in ("/", "/index.html", "/web", "/web/"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            target = "/web/index.html" + ("?" + query if query else "")
            return self._send(302, b"", "text/plain", {"Location": target})
        if path in ("/data/latest.json", "/data/latest.js"):
            f = cu.DATA_DIR / path.rsplit("/", 1)[1]
        elif path.startswith("/web/"):
            f = (WEB / path[len("/web/"):]).resolve()
            if WEB not in f.parents:
                return self._not_found()
        else:
            return self._not_found()
        if not f.is_file():
            return self._not_found()
        self._send(200, f.read_bytes(), TYPES.get(f.suffix.lower(), "application/octet-stream"))

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "host refused"})
        if self.path.split("?", 1)[0] != "/api/refresh":
            return self._not_found()
        # Refuse requests coming from a web page other than the widget itself.
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host', '')}":
            return self._json(403, {"error": "origin refused"})
        with _refresh_lock:
            importlib.reload(cu)          # picks up script updates without restarting the server
            row, error, state = cu.run()
        self._json(200 if error is None else 502, {"ok": error is None, "error": error, "state": state})


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
