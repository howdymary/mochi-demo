"""Local-only trajectory renderer and bounded video-upload sink."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/showcase-final"
OUT.mkdir(parents=True, exist_ok=True)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web/desk"), **kwargs)

    def do_POST(self):
        name = self.path.removeprefix("/export/")
        if self.path != "/export/" + name or name not in {"02-training.h264", "03-final.h264"}:
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", 0))
        if not 0 < size <= 500_000_000:
            self.send_error(413)
            return
        data = self.rfile.read(size)
        assert len(data) == size
        (OUT / name).write_bytes(data)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"saved")

    def log_message(self, *args):
        pass

ThreadingHTTPServer(("127.0.0.1", 4127), Handler).serve_forever()
