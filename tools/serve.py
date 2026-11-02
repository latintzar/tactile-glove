#!/usr/bin/env python3
"""Serve the public glove design locally, without a device or provider account."""
from __future__ import annotations
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = {'hardware', 'firmware', 'static', 'assets', 'docs', 'provenance', 'LICENSES'}
PUBLIC_FILES = {'README.md', 'LICENSE', 'THIRD-PARTY-NOTICES.md'}

class DesignHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        # Requests contain local file paths only. No headers/cookies are logged.
        pass

    def do_GET(self):
        return self._respond(False)

    def do_HEAD(self):
        return self._respond(True)

    def _respond(self, head):
        raw = unquote(urlsplit(self.path).path)
        if '\\' in raw or '\x00' in raw:
            self.send_error(404); return
        parts = PurePosixPath(raw).parts
        if any(p.startswith('.') or p == '..' for p in parts):
            self.send_error(404); return
        if raw in ('/', '/device', '/device/'):
            dst = '/hardware/glove-v4/software-preview/index.html' if raw.startswith('/device') else '/hardware/glove-v4/enclosure/viewer.html'
            self.send_response(302); self.send_header('Location', dst); self.end_headers(); return
        # Device hand asset URLs are absolute in the original bundled UI.
        if raw.startswith('/assets/') and not (ROOT / raw.lstrip('/')).is_file():
            raw = '/static/glove-viewer/' + raw.removeprefix('/assets/')
        # The original engineering viewer also used this named static mount.
        if raw.startswith('/build-v4-reference/'):
            raw = '/hardware/glove-v4/' + raw.removeprefix('/build-v4-reference/')
        rel = raw.lstrip('/')
        first = rel.split('/', 1)[0]
        if first not in PUBLIC_DIRS and rel not in PUBLIC_FILES:
            self.send_error(404); return
        target = (ROOT / rel).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            self.send_error(404); return
        self.path = '/' + target.relative_to(ROOT).as_posix()
        return super().do_HEAD() if head else super().do_GET()

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        super().end_headers()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=8070)
    args = ap.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', args.port), DesignHandler) as server:
        print(f'Artisan Glove design viewer: http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()
