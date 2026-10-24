#!/usr/bin/env python3
"""Loopback-only study server. Requests select pre-indexed assets, never filesystem paths."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, unquote
import argparse
import mimetypes

ROOT = Path(__file__).resolve().parent
# Filesystem access is based solely on trusted startup inventory. A request supplies
# a dictionary key, never a path joined to or resolved against the filesystem.
ASSETS = {
    '/' + asset.relative_to(ROOT).as_posix(): asset
    for asset in ROOT.rglob('*')
    if asset.is_file() and asset.resolve().is_relative_to(ROOT)
    and '__pycache__' not in asset.parts
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = unquote(urlsplit(self.path).path)
        if '..' in PurePosixPath(route).parts:
            self.send_error(404)
            return
        asset = ASSETS.get(route)
        if asset is None and '.' not in PurePosixPath(route).name:
            asset = ASSETS['/index.html']
        if asset is None:
            self.send_error(404)
            return
        data = asset.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(str(asset))[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    print(f'SENTINEL H study: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
