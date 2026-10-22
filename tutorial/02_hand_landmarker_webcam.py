"""Tutorial step 2: track a hand live from the webcam (VIDEO mode) and draw its skeleton.

Same guide as step 1, but with RunningMode.VIDEO and detect_for_video(), which needs a
timestamp that increases every frame. On top of the guide we measure two things the
project needs and MediaPipe does not give directly:

- pinch distance: thumb tip to index tip, divided by the palm size so it does not change
  when the hand moves closer to or farther from the camera
- fingers up: a finger counts as extended when its tip is farther from the wrist than
  its middle joint

    python tutorial/02_hand_landmarker_webcam.py     # press Q or Esc to quit
"""

import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"

# Bones of the hand: pairs of landmark indices (from the guide's hand model diagram).
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]
FINGERS = {"index": (8, 6), "middle": (12, 10), "ring": (16, 14), "pinky": (20, 18)}  # tip, middle joint
PINCH_THRESHOLD = 0.35  # pinch distance below this counts as pinched (try values with your own hand)


def describe(points: np.ndarray) -> tuple[float, int]:
    """Return (pinch distance relative to palm size, number of extended fingers)."""
    wrist = points[0]
    palm = np.linalg.norm(points[9] - wrist)  # wrist to middle-finger knuckle
    pinch = np.linalg.norm(points[4] - points[8]) / palm
    up = int(sum(np.linalg.norm(points[tip] - wrist) > np.linalg.norm(points[mid] - wrist)
             for tip, mid in FINGERS.values()))
    return pinch, up


def draw(frame: np.ndarray, points: np.ndarray) -> None:
    for a, b in CONNECTIONS:
        cv2.line(frame, tuple(points[a].astype(int)), tuple(points[b].astype(int)), (255, 255, 255), 2)
    for p in points:
        cv2.circle(frame, tuple(p.astype(int)), 4, (0, 200, 0), -1)


def main() -> None:
    if not MODEL.exists():
        sys.exit("Model missing. Run: python scripts/download_model.py")
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        sys.exit("Could not open the webcam (check camera permission).")

    start = time.monotonic()
    last = start
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)  # mirror, so moving your hand right moves it right on screen
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        timestamp_ms = int((time.monotonic() - start) * 1000)
        result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)

        height, width = frame.shape[:2]
        if result.hand_landmarks:
            points = np.array([(lm.x * width, lm.y * height) for lm in result.hand_landmarks[0]])
            draw(frame, points)
            pinch, up = describe(points)
            label = "PINCH" if pinch < PINCH_THRESHOLD else ("FIST" if up == 0 else ("OPEN" if up == 4 else "-"))
            text = f"pinch {pinch:.2f}  fingers up {up}  -> {label}"
        else:
            text = "no hand"

        now = time.monotonic()
        fps, last = 1 / max(now - last, 1e-6), now
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"{fps:.0f} fps", (10, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.imshow("Tutorial step 2 - hand landmarks (Q to quit)", frame)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break

    capture.release()
    landmarker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
