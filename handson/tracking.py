"""Webcam capture and MediaPipe hand tracking on a background thread.

The Qt/VTK window must stay on the main thread (required on macOS), so this
thread only produces results. The window polls `latest()` on a timer.
"""

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Pairs of landmark indices to draw the hand skeleton in the preview.
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),
]


@dataclass
class TrackingFrame:
    image: np.ndarray             # RGB preview, mirrored, skeleton drawn
    landmarks: np.ndarray | None  # (21, 3) normalized x, y in [0, 1], z relative depth; None if no hand
    handedness: str | None        # "Left" / "Right" as seen in the mirrored image
    timestamp: float              # time.monotonic() when the frame was captured
    fps: float


class HandTracker:
    def __init__(self, model_path: Path, camera_index: int = 0, num_hands: int = 1):
        self.model_path = Path(model_path)
        self.camera_index = camera_index
        self.num_hands = num_hands
        self._capture: cv2.VideoCapture | None = None
        self._landmarker = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._latest: TrackingFrame | None = None

    def start(self) -> None:
        """Open the camera and model on the calling (main) thread, then start tracking."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}. Run: python scripts/download_model.py")
        self._capture = cv2.VideoCapture(self.camera_index)
        if not self._capture.isOpened():
            raise RuntimeError(
                f"Could not open camera {self.camera_index}. On macOS, allow camera access for your "
                "terminal/editor in System Settings > Privacy & Security > Camera.")
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=self.num_hands,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._running.set()
        self._thread = threading.Thread(target=self._run, name="hand-tracker", daemon=True)
        self._thread.start()

    def latest(self) -> TrackingFrame | None:
        with self._lock:
            return self._latest

    def stop(self) -> None:
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2)
        if self._capture:
            self._capture.release()
        if self._landmarker:
            self._landmarker.close()

    def _run(self) -> None:
        start = time.monotonic()
        last_ms = -1
        last_time = start
        fps = 0.0
        while self._running.is_set():
            ok, frame = self._capture.read()
            if not ok:
                time.sleep(0.01)
                continue
            now = time.monotonic()
            # Mirror so moving your hand right moves it right on screen.
            rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
            # VIDEO mode needs strictly increasing timestamps.
            timestamp_ms = max(int((now - start) * 1000), last_ms + 1)
            last_ms = timestamp_ms
            result = self._landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)

            landmarks = handedness = None
            if result.hand_landmarks:
                landmarks = np.array([[p.x, p.y, p.z] for p in result.hand_landmarks[0]])
                handedness = result.handedness[0][0].category_name
                _draw_skeleton(rgb, landmarks)

            fps = 0.9 * fps + 0.1 / max(now - last_time, 1e-6)
            last_time = now
            with self._lock:
                self._latest = TrackingFrame(rgb, landmarks, handedness, now, fps)


def _draw_skeleton(image: np.ndarray, landmarks: np.ndarray) -> None:
    height, width = image.shape[:2]
    points = [(int(x * width), int(y * height)) for x, y, _ in landmarks]
    for a, b in HAND_CONNECTIONS:
        cv2.line(image, points[a], points[b], (100, 205, 185), 2)
    for point in points:
        cv2.circle(image, point, 4, (255, 198, 109), -1)
