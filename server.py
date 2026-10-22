#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serveur local du widget (Windows, Linux, macOS ; bibliotheque standard uniquement).

    python server.py            -> http://127.0.0.1:8765/
    python server.py --open     -> idem + ouvre le navigateur (s'il tourne deja : ouvre juste le navigateur)

Routes :
    GET  /                   -> redirige vers /web/index.html
    GET  /web/...            -> fichiers du widget
    GET  /data/latest.json   -> dernier etat
    GET  /api/ping           -> verifie que c'est bien ce serveur
    POST /api/refresh        -> lance un releve (comme releve_maintenant) et renvoie l'etat

Ecoute uniquement sur 127.0.0.1 : rien n'est expose sur le reseau.
"""
from __future__ import annotations

import argparse
import importlib
import json
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

# Table fixe : sous Windows, mimetypes lit le registre et sert parfois le .js en text/plain.
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
    server_version = "ClaudeUsage/0.2"

    def log_message(self, fmt, *args):  # silencieux (pythonw n'a pas de console)
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
        self._json(404, {"error": "introuvable"})

    def _host_ok(self) -> bool:
        """Anti DNS-rebinding : seule l'adresse locale est acceptee dans l'en-tete Host.
        Sans ca, une page distante pourrait pointer son nom de domaine vers 127.0.0.1
        et interroger ce serveur depuis le navigateur."""
        port = self.server.server_address[1]
        return (self.headers.get("Host") or "").lower() in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "hote refuse"})
        path = self.path.split("?", 1)[0]
        if path == "/api/ping":
            return self._json(200, {"app": APP_ID})
        if path in ("/", "/index.html", "/web", "/web/"):
            return self._send(302, b"", "text/plain", {"Location": "/web/index.html"})
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
            return self._json(403, {"error": "hote refuse"})
        if self.path.split("?", 1)[0] != "/api/refresh":
            return self._not_found()
        # Refuse les requetes venant d'une autre page web que le widget lui-meme.
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host', '')}":
            return self._json(403, {"error": "origine refusee"})
        with _refresh_lock:
            importlib.reload(cu)          # prend en compte les mises a jour du script sans redemarrer le serveur
            row, error, state = cu.run()
        self._json(200 if error is None else 502, {"ok": error is None, "error": error, "state": state})


def already_running(port: int) -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # ignore les proxys systeme
    try:
        with opener.open(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return json.load(r).get("app") == APP_ID
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Serveur local du widget de quota Claude")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--open", action="store_true", help="ouvre le widget dans le navigateur")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}/web/index.html"

    if already_running(args.port):
        print("Serveur deja lance :", url)
        if args.open:
            webbrowser.open(url)
        return 0
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as e:
        print(f"Impossible d'ecouter sur le port {args.port} : {e}. Essaie --port 8766.")
        return 1
    print(f"Widget : {url}   (Ctrl+C pour arreter)")
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
