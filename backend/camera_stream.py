import threading
import time


class CameraStream:
    def __init__(self, device="/dev/video0", width=640, height=480, fps=20, quality=80):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.quality = quality
        self._cv2 = None
        self._capture = None
        self._lock = threading.Lock()
        self._last_error = None

        try:
            import cv2

            self._cv2 = cv2
        except ImportError as e:
            self._last_error = f"OpenCV nao instalado: {e}"

    @property
    def available(self):
        return self._cv2 is not None

    @property
    def is_open(self):
        return bool(self._capture and self._capture.isOpened())

    def open(self):
        if not self.available:
            return False

        with self._lock:
            if self.is_open:
                return True

            capture = self._cv2.VideoCapture(self.device)
            if self.width:
                capture.set(self._cv2.CAP_PROP_FRAME_WIDTH, self.width)
            if self.height:
                capture.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            if self.fps:
                capture.set(self._cv2.CAP_PROP_FPS, self.fps)

            if not capture.isOpened():
                self._last_error = f"Nao foi possivel abrir camera {self.device}"
                capture.release()
                return False

            self._capture = capture
            self._last_error = None
            print(f"[INFO] Camera aberta: {self.device} ({self.width}x{self.height} @ {self.fps}fps)")
            return True

    def read_jpeg(self):
        if not self.open():
            return None

        with self._lock:
            ok, frame = self._capture.read()
            if not ok:
                self._last_error = f"Falha ao ler frame da camera {self.device}"
                return None

            encode_params = [int(self._cv2.IMWRITE_JPEG_QUALITY), int(self.quality)]
            ok, encoded = self._cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                self._last_error = "Falha ao codificar frame JPEG"
                return None

            return encoded.tobytes()

    def frames(self):
        frame_delay = 1.0 / self.fps if self.fps else 0.05
        while True:
            started_at = time.time()
            jpeg = self.read_jpeg()
            if jpeg:
                yield jpeg

            elapsed = time.time() - started_at
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)

    def close(self):
        with self._lock:
            if self._capture:
                self._capture.release()
                self._capture = None
                print("[INFO] Camera encerrada.")

    def status(self):
        return {
            "available": self.available,
            "open": self.is_open,
            "device": self.device,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "quality": self.quality,
            "error": self._last_error,
        }
