"""Google's hand_landmarker.ipynb (mediapipe-samples), cell by cell, to run on a Mac.

Same code as the notebook; only the Colab-only parts are changed:
- `!pip install` / `!wget` cells are skipped (the handson env has MediaPipe, the model is
  in models/, and the test photo is downloaded as shown in tutorial/README.md)
- `cv2_imshow` from google.colab is replaced by saving the picture and opening it
- the 4-channel image is cut to 3 channels before drawing (see STEP 5)

    python tutorial/00_mediapipe_notebook.py tutorial/woman_hands.jpg   # the notebook's test photo
    python tutorial/00_mediapipe_notebook.py my_hand.jpg                # your own photo (the upload cell)
"""

import subprocess
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

# --- Notebook cell "Visualization utilities" (unchanged) ---
mp_hands = mp.tasks.vision.HandLandmarksConnections
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles

MARGIN = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)  # vibrant green


def draw_landmarks_on_image(rgb_image, detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness
    annotated_image = np.copy(rgb_image)

    # Loop through the detected hands to visualize.
    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        handedness = handedness_list[idx]

        # Draw the hand landmarks.
        mp_drawing.draw_landmarks(
            annotated_image,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style())

        # Get the top left corner of the detected hand's bounding box.
        height, width, _ = annotated_image.shape
        x_coordinates = [landmark.x for landmark in hand_landmarks]
        y_coordinates = [landmark.y for landmark in hand_landmarks]
        text_x = int(min(x_coordinates) * width)
        text_y = int(min(y_coordinates) * height) - MARGIN

        # Draw handedness (left or right hand) on the image.
        cv2.putText(annotated_image, f"{handedness[0].category_name}",
                    (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
                    FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

    return annotated_image


# Stand-in for google.colab's cv2_imshow: save the picture and open it in Preview.
def show(bgr_image, name):
    cv2.imwrite(name, bgr_image)
    print(f"Saved {name}")
    if "--no-open" not in sys.argv:
        subprocess.run(["open", name])


# --- Notebook cell "Download test image" (the image is already here) ---
args = [a for a in sys.argv[1:] if a != "--no-open"]
if not args:
    sys.exit("Give a photo, e.g. tutorial/woman_hands.jpg (see tutorial/README.md to download it).")
IMAGE_FILE = args[0]
HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / "models" / "hand_landmarker.task"

# --- Notebook cell "Running inference and visualizing the results" ---
# STEP 1: Import the necessary modules.
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# STEP 2: Create an HandLandmarker object.
base_options = python.BaseOptions(model_asset_path=str(MODEL))
options = vision.HandLandmarkerOptions(base_options=base_options,
                                       num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

# STEP 3: Load the input image.
image = mp.Image.create_from_file(IMAGE_FILE)

# STEP 4: Detect hand landmarks from the input image.
detection_result = detector.detect(image)

# STEP 5: Process the classification result. In this case, visualize it.
# Change from the notebook: MediaPipe 0.10.35 loads the JPEG with 4 channels (RGBA), but the
# drawing helper wants 3, so drop the alpha channel.
annotated_image = draw_landmarks_on_image(image.numpy_view()[:, :, :3], detection_result)
show(cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR), str(HERE / "step0_result.jpg"))
