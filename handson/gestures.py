"""Turn 21 hand landmarks into a hand shape.

Landmark indices (MediaPipe hand model):
    0 wrist
    1-4   thumb   (4 = tip)
    5-8   index   (5 = knuckle/MCP, 6 = PIP, 8 = tip)
    9-12  middle  (12 = tip)
    13-16 ring    (16 = tip)
    17-20 pinky   (20 = tip)

Agreed gesture set (see README):
    FIST  - all four fingertips curled toward the palm      -> rotate while held
    PINCH - thumb tip touching index tip, others relaxed     -> zoom while held
    OPEN  - all five fingers extended                        -> reset if held ~1 s
    NONE  - anything else, or no hand                        -> do nothing
"""

from enum import Enum

import numpy as np


class HandShape(Enum):
    NONE = "none"
    OPEN = "open palm"
    FIST = "fist"
    PINCH = "pinch"


def classify(landmarks: np.ndarray | None) -> HandShape:
    """Classify one hand's (21, 3) landmarks.

    TODO (implementation team): implement FIST, PINCH and OPEN.
    Hints:
      - Normalize distances by hand size (e.g. wrist 0 -> middle knuckle 9)
        so the result does not depend on how far the hand is from the camera.
      - A finger is extended when its tip is farther from the wrist than its PIP joint.
      - PINCH: distance(4, 8) / hand size below a threshold (start around 0.3).
      - Tune thresholds with real hands; add unit tests with recorded landmarks.
    """
    if landmarks is None:
        return HandShape.NONE
    return HandShape.NONE
