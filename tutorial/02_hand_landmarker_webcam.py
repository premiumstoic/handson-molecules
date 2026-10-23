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

import math
import os
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

CAMERA = int(os.environ.get("HANDSON_CAMERA", "0"))  # webcam index; e.g. HANDSON_CAMERA=1 for a second camera
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
# For each finger (not the thumb): the number of its tip and of its middle joint.
FINGERS = [
    (8, 6),    # index
    (12, 10),  # middle
    (16, 14),  # ring
    (20, 18),  # pinky
]
PINCH_THRESHOLD = 0.35  # pinch distance below this counts as pinched (try values with your own hand)


def distance(a, b):
    """Distance between two points (x, y), with Pythagoras."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def describe(points):
    """Return the pinch distance (relative to palm size) and the number of fingers up."""
    wrist = points[0]

    # Palm size: wrist to middle-finger knuckle. Dividing by it means moving the hand
    # closer to the camera does not change the pinch number.
    palm = distance(points[9], wrist)

    # Pinch: thumb tip (4) to index tip (8).
    pinch = distance(points[4], points[8]) / palm

    # A finger is up when its tip is farther from the wrist than its middle joint.
    fingers_up = 0
    for tip, middle_joint in FINGERS:
        if distance(points[tip], wrist) > distance(points[middle_joint], wrist):
            fingers_up = fingers_up + 1

    return pinch, fingers_up


def gesture_name(pinch, fingers_up):
    if pinch < PINCH_THRESHOLD:
        return "PINCH"
    if fingers_up == 0:
        return "FIST"
    if fingers_up == 4:
        return "OPEN"
    return "-"


def draw(frame, points):
    white = (255, 255, 255)
    green = (0, 200, 0)
    for a, b in CONNECTIONS:
        cv2.line(frame, points[a], points[b], white, 2)
    for point in points:
        cv2.circle(frame, point, 4, green, -1)


def main() -> None:
    if not MODEL.exists():
        sys.exit("Model missing. Run: python scripts/download_model.py")

    # VIDEO mode: MediaPipe follows the hand from one frame to the next.
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    capture = cv2.VideoCapture(CAMERA)
    if not capture.isOpened():
        sys.exit("Could not open the webcam (check camera permission).")

    start = time.monotonic()
    failed_reads = 0
    while True:
        # 1. Read one frame from the camera. Some cameras (like an iPhone through
        # Continuity Camera) send empty frames for a moment while they start, so wait.
        ok, frame = capture.read()
        if not ok:
            failed_reads = failed_reads + 1
            if failed_reads > 100:
                print("The camera sends no pictures. Is another app using it, or is it the wrong camera number?")
                break
            time.sleep(0.05)
            continue
        failed_reads = 0
        frame = cv2.flip(frame, 1)  # mirror, so moving your hand right moves it right on screen

        # 2. Give it to MediaPipe. It wants RGB colours and a time that goes up every frame.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.monotonic() - start) * 1000)
        result = landmarker.detect_for_video(image, timestamp_ms)

        # 3. If there is a hand, turn its 21 points into pixels, draw them, and name the gesture.
        height = frame.shape[0]
        width = frame.shape[1]
        if len(result.hand_landmarks) > 0:
            hand = result.hand_landmarks[0]
            points = []
            for i in range(21):
                x_pixel = int(hand[i].x * width)
                y_pixel = int(hand[i].y * height)
                points.append((x_pixel, y_pixel))

            draw(frame, points)
            pinch, fingers_up = describe(points)
            text = "pinch " + str(round(pinch, 2)) + "  fingers up " + str(fingers_up)
            text = text + "  -> " + gesture_name(pinch, fingers_up)
        else:
            text = "no hand"

        # 4. Show it. Q or Esc closes the window.
        yellow = (0, 255, 255)
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, yellow, 2)
        cv2.imshow("Tutorial step 2 - hand landmarks (Q to quit)", frame)
        key = cv2.waitKey(1)
        if key == ord("q") or key == 27:
            break

    capture.release()
    landmarker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
