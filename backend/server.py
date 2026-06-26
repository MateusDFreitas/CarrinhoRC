import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

from carrinho_serial import ArduinoBridge

DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
DIST_DIR = DASHBOARD_DIR / "dist"


class DashboardHandler(BaseHTTPRequestHandler):
    bridge = None

    def log_message(self, fmt, *args):
        print(f"[HTTP] {self.address_string()} - {fmt % args}")

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self, path, include_body=True):
        static_root = DIST_DIR

        if path == "/":
            file_path = static_root / "index.html"
        else:
            requested = path.lstrip("/")
            file_path = (static_root / requested).resolve()
            if not str(file_path).startswith(str(static_root.resolve())):
                self.send_error(403)
                return

        if not file_path.is_file():
            index_path = static_root / "index.html"
            if index_path.is_file():
                file_path = index_path
            else:
                self.send_error(404)
                return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if include_body:
            self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send_json(200, {"ok": True, "status": self.bridge.status()})
            return
        self._serve_static(path)

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            return
        self._serve_static(path, include_body=False)

    def do_POST(self):
        path = urlparse(self.path).path

        try:
            if path == "/api/command":
                data = self._read_json()
                channel = str(data.get("channel", "")).lower()
                value = int(data.get("value"))

                if not 1000 <= value <= 2000:
                    self._send_json(400, {"ok": False, "error": "PWM fora da faixa 1000..2000"})
                    return

                if channel == "esc":
                    ok = self.bridge.send_esc(value)
                elif channel == "servo":
                    ok = self.bridge.send_servo(value)
                else:
                    self._send_json(400, {"ok": False, "error": "Canal invalido"})
                    return

                self._send_json(200 if ok else 503, {"ok": ok, "status": self.bridge.status()})
                return

            if path == "/api/stop":
                ok = self.bridge.stop_all()
                self._send_json(200 if ok else 503, {"ok": ok, "status": self.bridge.status()})
                return

            self.send_error(404)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            self._send_json(400, {"ok": False, "error": f"Requisicao invalida: {e}"})


def main():
    parser = argparse.ArgumentParser(description="Dashboard web para controle serial do CarrinhoRC.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Porta serial do Arduino")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate da serial")
    parser.add_argument("--host", default="0.0.0.0", help="Host HTTP")
    parser.add_argument("--http-port", type=int, default=8000, help="Porta HTTP da dashboard")
    args = parser.parse_args()

    DashboardHandler.bridge = ArduinoBridge(serial_port=args.port, baud_rate=args.baud)
    server = ThreadingHTTPServer((args.host, args.http_port), DashboardHandler)

    print(f"[INFO] Dashboard em http://localhost:{args.http_port}")
    print(f"[INFO] Serial configurada: {args.port} @ {args.baud}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando dashboard...")
    finally:
        DashboardHandler.bridge.close()
        server.server_close()


if __name__ == "__main__":
    main()
