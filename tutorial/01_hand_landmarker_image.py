"""Tutorial step 1: find the 21 hand landmarks in one still image (IMAGE mode).

Follows the "Hand landmarks detection guide for Python" from Google's MediaPipe docs:
create a HandLandmarker from the .task model, give it an mp.Image, read the result.

    python tutorial/01_hand_landmarker_image.py              # takes one photo from the webcam
    python tutorial/01_hand_landmarker_image.py hand.jpg     # or uses an image file
"""

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
    capture = cv2.VideoCapture(CAMERA)
    # The first frames are often empty or dark while the camera starts (an iPhone takes
    # longer), so keep reading until 10 good frames have come in, for up to about 5 s.
    good = 0
    for _ in range(100):
        ok, image = capture.read()
        if ok:
            good = good + 1
            if good == 10:
                break
        else:
            time.sleep(0.05)
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
    if len(result.hand_landmarks) == 0:
        print("No hand found. Hold your hand up, palm to the camera, and try again.")

    height = bgr.shape[0]
    width = bgr.shape[1]
    green = (0, 255, 0)  # OpenCV colours are (blue, green, red)

    for h in range(len(result.hand_landmarks)):
        hand = result.hand_landmarks[h]       # the 21 points of this hand
        side = result.handedness[h][0]        # "Left" or "Right", and how sure MediaPipe is
        print()
        print(side.category_name, "hand, score", round(side.score, 2))

        for i in range(21):
            point = hand[i]
            print(i, NAMES[i], "x =", round(point.x, 3), "y =", round(point.y, 3), "z =", round(point.z, 3))

            # x and y are between 0 and 1, so multiply by the image size to get pixels.
            x_pixel = int(point.x * width)
            y_pixel = int(point.y * height)
            cv2.circle(bgr, (x_pixel, y_pixel), 4, green, -1)  # radius 4, -1 = filled

    cv2.imwrite(str(OUT), bgr)
    print()
    print("Saved", OUT)


if __name__ == "__main__":
    main()
