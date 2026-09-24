"""Server lokal non-Flask untuk Rekap Gaji Art Pro."""
import argparse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.app import ApiApp, MAX_BODY


class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "RekapGaji"
    sys_version = ""

    def _run(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY:
            status, out_headers, body = self.app.fail(413, "BODY_TOO_LARGE", "Ukuran data melebihi batas.")
            self.close_connection = True
            self.send_response(status)
            for key, value in out_headers.items(): self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        raw = self.rfile.read(length) if length else b""
        headers = {key: value for key, value in self.headers.items()}
        status, out_headers, body = self.app.handle(self.command, self.path, headers, raw)
        self.send_response(status)
        for key, value in out_headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _run

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    Handler.app = ApiApp(root)
    host = "127.0.0.1"
    server = ThreadingHTTPServer((host, args.port), Handler)
    url = f"http://{host}:{args.port}"
    print(f"Rekap Gaji Art Pro siap di {url}", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
