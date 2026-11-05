"""Serve the web app and forward /api/* to the login API, so both share one origin.

    RISKAUTH_SIM_MODE=1 uvicorn api.app:app --port 8000
    python web/serve.py                 # http://localhost:5173
    python web/serve.py --port 5173 --api http://127.0.0.1:8000

Development only. In production, put both behind one reverse proxy (nginx, Caddy).
"""
from __future__ import annotations

import argparse
import http.server
import urllib.error
import urllib.request
from functools import partial
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent
FORWARD_HEADERS = ("content-type", "authorization", "x-sim-context", "x-admin-token")


class Handler(http.server.SimpleHTTPRequestHandler):
    api_base = "http://127.0.0.1:8000"
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json", ".js": "text/javascript",
                      ".svg": "image/svg+xml"}

    def end_headers(self):
        if self.path.endswith(("sw.js", ".html", "/")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _proxy(self):
        target = self.api_base + self.path[len("/api"):]
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() in FORWARD_HEADERS}
        req = urllib.request.Request(target, data=body, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                status, ctype, data = r.status, r.headers.get("content-type", ""), r.read()
        except urllib.error.HTTPError as e:
            status, ctype, data = e.code, e.headers.get("content-type", ""), e.read()
        except (urllib.error.URLError, TimeoutError):
            status, ctype = 502, "application/json"
            data = b'{"status":"api_unreachable","message":"The login API is not running."}'
        self.send_response(status)
        if ctype:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)

    def log_message(self, fmt, *args):
        if not self.path.startswith(("/icons", "/vendor")):
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5173)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    Handler.api_base = args.api.rstrip("/")
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), partial(Handler, directory=str(WEB_ROOT)))
    print(f"RiskLogin web app on http://localhost:{args.port}  (API → {Handler.api_base})")
    server.serve_forever()


if __name__ == "__main__":
    main()
