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

Rules from Zach's gesture detector MVP. All distances are divided by hand size
(wrist -> middle knuckle), so they work at any distance from the camera.
"""

from collections import Counter, deque
from enum import Enum

import numpy as np


class HandShape(Enum):
    NONE = "none"
    OPEN = "open palm"
    FIST = "fist"
    PINCH = "pinch"


# Tunable thresholds, in units of hand size.
THRESHOLDS = {
    "pinch_max": 0.3,          # thumb tip <-> index tip must be closer than this to start a pinch
    "pinch_index_reach": 0.85,  # index tip must still be out from the wrist (separates pinch from a fist)
    "extend_ratio": 1.1,       # finger tip this much farther from the wrist than its PIP joint = extended
    "curl_ratio": 1.0,         # finger tip closer to the wrist than this x PIP joint = curled
    "thumb_out": 0.55,         # thumb tip <-> index knuckle distance for an open thumb
}

FINGERS = [(8, 6), (12, 10), (16, 14), (20, 18)]  # (tip, PIP) for index, middle, ring, pinky
PALM_POINTS = [0, 5, 9, 13, 17]  # wrist and the four knuckles


def classify(landmarks: np.ndarray | None, aspect: float = 4 / 3, t: dict = THRESHOLDS) -> HandShape:
    """Classify one hand's (21, 3) normalized landmarks from a single frame.

    `aspect` is the camera image width / height. Landmarks are normalized to the
    image size, so x (and z, which uses the same scale) are stretched by it to
    get true proportions.
    """
    if landmarks is None:
        return HandShape.NONE
    points = np.asarray(landmarks, dtype=float) * [aspect, 1.0, aspect]

    def dist(a: int, b: int) -> float:
        return float(np.linalg.norm(points[a] - points[b]))

    size = dist(0, 9) or 1e-6
    extended = curled = 0
    for tip, pip in FINGERS:
        if dist(0, tip) > dist(0, pip) * t["extend_ratio"]:
            extended += 1
        elif dist(0, tip) < dist(0, pip) * t["curl_ratio"]:
            curled += 1

    pinch_dist = dist(4, 8) / size
    index_reach = dist(0, 8) / size
    thumb_open = dist(4, 5) / size > t["thumb_out"]

    if pinch_dist < t["pinch_max"] and index_reach > t["pinch_index_reach"]:
        return HandShape.PINCH
    if extended == 4 and thumb_open:
        return HandShape.OPEN
    if curled >= 4 or (curled >= 3 and extended == 0):
        return HandShape.FIST
    return HandShape.NONE


def palm_center(landmarks: np.ndarray | None) -> np.ndarray | None:
    """Hand position for movement-based actions: mean (x, y) of the wrist and knuckles.

    Steadier than the wrist alone, and it does not move when the fingers curl or
    spread, so changing shape does not count as moving the hand.
    """
    if landmarks is None:
        return None
    return np.asarray(landmarks, dtype=float)[PALM_POINTS, :2].mean(axis=0)


class GestureFilter:
    """Turns per-frame shapes into a stable gesture.

    - A shape only becomes the gesture once it wins `min_votes` of the last
      `window` frames, so the display and the camera do not flicker.
    - Pinch is latched: once a pinch starts, it stays PINCH while the thumb and
      index spread apart (which the per-frame rule sees as NONE), until the hand
      opens fully, makes a fist, or disappears. This gives pinch-to-zoom its range.
    - Letting go is fast: once `release_frames` frames in a row disagree with the
      current gesture, it drops to NONE straight away, so the molecule stops
      moving as soon as the hand changes shape.
    - No hand clears everything at once, so nothing moves without a hand.
    """

    def __init__(self, window: int = 7, min_votes: int = 5, release_frames: int = 2):
        self.min_votes = min_votes
        self.release_frames = release_frames
        self.history: deque[HandShape] = deque(maxlen=window)
        self.stable = HandShape.NONE
        self.pinch_latched = False

    def update(self, landmarks: np.ndarray | None, aspect: float = 4 / 3) -> HandShape:
        if landmarks is None:
            self.reset()
            return self.stable

        shape = classify(landmarks, aspect)
        if shape is HandShape.PINCH:
            self.pinch_latched = True
        elif shape in (HandShape.OPEN, HandShape.FIST):
            self.pinch_latched = False
        elif self.pinch_latched:
            shape = HandShape.PINCH

        self.history.append(shape)
        recent = list(self.history)[-self.release_frames:]
        if (self.stable is not HandShape.NONE and len(recent) == self.release_frames
                and all(s is not self.stable for s in recent)):
            # Release, and keep only the frames that disagreed, so the old gesture
            # cannot win the vote again and the new one still needs `min_votes`.
            self.stable = HandShape.NONE
            self.history = deque(recent, maxlen=self.history.maxlen)
            return self.stable
        winner, votes = Counter(self.history).most_common(1)[0]
        if votes >= self.min_votes:
            self.stable = winner
        return self.stable

    def reset(self) -> None:
        self.history.clear()
        self.stable = HandShape.NONE
        self.pinch_latched = False
