from math import hypot
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import monotonic

from logique import Signal


def measure(points, width, height, timestamp):
    def point(i):
        return points[i].x * width, points[i].y * height

    def distance(a, b):
        x, y = point(a)
        u, v = point(b)
        return hypot(x-u, y-v)

    # MediaPipe's anatomical right eye surrounds iris 468. The raw frame
    # is never mirrored before inference.
    ax, ay = point(33)
    bx, by = point(133)
    ix, iy = point(468)
    dx, dy = bx-ax, by-ay
    size = dx*dx + dy*dy
    left_width = distance(362, 263)
    if size < 64 or left_width < 8:
        return None
    return Signal(timestamp,
                  ((ix-ax)*dx + (iy-ay)*dy)/size,
                  ((iy-ay)*dx - (ix-ax)*dy)/size,
                  distance(386, 374)/left_width, distance(159, 145)/size**.5)


class Camera:
    def __init__(self, model, index):
        self.messages = Queue(maxsize=16)
        self.stop = Event()
        self.worker = Thread(target=self.run, args=(Path(model), index), daemon=True)
        self.worker.start()

    def post(self, kind, payload):
        try:
            self.messages.put_nowait((kind, payload))
        except Full:
            # Missing observations invalidate any gesture crossing this gap.
            while True:
                try:
                    self.messages.get_nowait()
                except Empty:
                    break
            self.messages.put_nowait(("signal", None))
            self.messages.put_nowait((kind, payload))

    def run(self, model, index):
        capture = None
        try:
            if not model.is_file():
                raise RuntimeError(f"Modèle absent : {model}. Voir le README.")
            import cv2
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            capture = cv2.VideoCapture(index)
            if not capture.isOpened():
                raise RuntimeError(f"Webcam {index} inaccessible.")
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.VIDEO, num_faces=1)
            with vision.FaceLandmarker.create_from_options(options) as detector:
                last_ms = -1
                failures = 0
                while not self.stop.is_set():
                    ok, frame = capture.read()
                    stamp = monotonic()
                    if not ok:
                        self.post("signal", None)
                        failures += 1
                        if failures >= 10:
                            raise RuntimeError("La webcam ne renvoie plus d’images.")
                        self.stop.wait(.05)
                        continue
                    failures = 0
                    last_ms = max(int(stamp*1000), last_ms+1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), last_ms)
                    points = result.face_landmarks
                    sample = measure(points[0], frame.shape[1], frame.shape[0], stamp) if points else None
                    self.post("signal", sample)
        except Exception as error:
            self.post("error", str(error))
        finally:
            if capture is not None:
                capture.release()
