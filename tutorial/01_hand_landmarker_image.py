"""Tutorial step 1: find the 21 hand landmarks in one still image (IMAGE mode).

Follows the "Hand landmarks detection guide for Python" from Google's MediaPipe docs:
create a HandLandmarker from the .task model, give it an mp.Image, read the result.

    python tutorial/01_hand_landmarker_image.py              # takes one photo from the webcam
    python tutorial/01_hand_landmarker_image.py hand.jpg     # or uses an image file
"""

import sys
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"
OUT = Path(__file__).resolve().parent / "step1_result.jpg"

# Landmark names from the guide's hand model diagram (index = position in the list).
NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
]


def read_image() -> "cv2.Mat":
    if len(sys.argv) > 1:
        image = cv2.imread(sys.argv[1])
        if image is None:
            sys.exit(f"Could not read {sys.argv[1]}")
        return image
    capture = cv2.VideoCapture(0)
    for _ in range(10):  # the first frames are often dark while the camera adjusts
        ok, image = capture.read()
    capture.release()
    if not ok:
        sys.exit("Could not read from the webcam (check camera permission).")
    return image


def main() -> None:
    if not MODEL.exists():
        sys.exit("Model missing. Run: python scripts/download_model.py")

    # 1. Create the landmarker with options.
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=2,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    # 2. Prepare the input. OpenCV gives BGR, MediaPipe wants RGB.
    bgr = read_image()
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

    # 3. Run the task.
    result = landmarker.detect(mp_image)
    landmarker.close()

    # 4. Handle the result: one list of 21 landmarks per detected hand.
    if not result.hand_landmarks:
        print("No hand found. Hold your hand up, palm to the camera, and try again.")
    height, width = bgr.shape[:2]
    for hand, handedness in zip(result.hand_landmarks, result.handedness):
        print(f"\n{handedness[0].category_name} hand (score {handedness[0].score:.2f})")
        for i, lm in enumerate(hand):
            print(f"  {i:2d} {NAMES[i]:<11} x={lm.x:.3f} y={lm.y:.3f} z={lm.z:+.3f}")
            # x and y are normalized to [0, 1], so scale them to pixels to draw.
            cv2.circle(bgr, (int(lm.x * width), int(lm.y * height)), 4, (0, 255, 0), -1)

    cv2.imwrite(str(OUT), bgr)
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
