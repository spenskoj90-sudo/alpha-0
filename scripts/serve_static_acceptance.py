"""Serve Next's exported site locally with Render's clean-URL behavior for browser CI."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class ExportHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        resolved = super().translate_path(path)
        if not Path(resolved).exists() and not Path(urlsplit(path).path).suffix:
            resolved = resolved.rstrip("/") + ".html"
        return resolved


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 3001), lambda *args, **kwargs: ExportHandler(*args, directory="site/out", **kwargs)).serve_forever()
