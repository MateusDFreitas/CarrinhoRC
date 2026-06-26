import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

from camera_stream import CameraStream
from carrinho_serial import ArduinoBridge

DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
DIST_DIR = DASHBOARD_DIR / "dist"


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DashboardHandler(BaseHTTPRequestHandler):
    bridge = None
    camera = None

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

    def _serve_camera_stream(self):
        if not self.camera or not self.camera.available:
            self._send_json(503, {"ok": False, "camera": self.camera.status() if self.camera else None})
            return

        if not self.camera.open():
            self._send_json(503, {"ok": False, "camera": self.camera.status()})
            return

        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        try:
            for jpeg in self.camera.frames():
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            pass

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
            self._send_json(200, {"ok": True, "status": self.bridge.status(), "camera": self.camera.status() if self.camera else None})
            return
        if path == "/api/camera/status":
            self._send_json(200, {"ok": True, "camera": self.camera.status() if self.camera else None})
            return
        if path == "/api/camera/stream":
            self._serve_camera_stream()
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
    parser.add_argument("--camera-device", default="/dev/video0", help="Dispositivo da camera")
    parser.add_argument("--camera-width", type=int, default=640, help="Largura do video da camera")
    parser.add_argument("--camera-height", type=int, default=480, help="Altura do video da camera")
    parser.add_argument("--camera-fps", type=int, default=20, help="FPS do stream da camera")
    parser.add_argument("--camera-quality", type=int, default=80, help="Qualidade JPEG do stream da camera")
    args = parser.parse_args()

    DashboardHandler.bridge = ArduinoBridge(serial_port=args.port, baud_rate=args.baud)
    DashboardHandler.camera = CameraStream(
        device=args.camera_device,
        width=args.camera_width,
        height=args.camera_height,
        fps=args.camera_fps,
        quality=args.camera_quality,
    )
    server = ThreadedHTTPServer((args.host, args.http_port), DashboardHandler)

    print(f"[INFO] Dashboard em http://localhost:{args.http_port}")
    print(f"[INFO] Serial configurada: {args.port} @ {args.baud}")
    print(f"[INFO] Camera configurada: {args.camera_device} ({args.camera_width}x{args.camera_height} @ {args.camera_fps}fps)")
    if not DashboardHandler.camera.available:
        print("[AVISO] OpenCV nao instalado. Instale python3-opencv ou opencv-python para usar a camera.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando dashboard...")
    finally:
        DashboardHandler.bridge.close()
        DashboardHandler.camera.close()
        server.server_close()


if __name__ == "__main__":
    main()
