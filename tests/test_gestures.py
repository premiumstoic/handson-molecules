"""Gesture rules on synthetic hands (ported from Zach's MVP tests).

Each finger is given as [MCP, PIP, DIP, tip] offsets from the wrist, in
normalized image coordinates (y grows downward). aspect=1 because the
synthetic coordinates are already square.
"""

import numpy as np

from handson.gestures import GestureFilter, HandShape, classify, palm_center

WRIST = np.array([0.5, 0.8])


def hand(thumb, index, middle, ring, pinky):
    points = [WRIST] + [WRIST + offset for finger in (thumb, index, middle, ring, pinky) for offset in finger]
    return np.column_stack([np.array(points), np.zeros(21)])


def extended(x):
    return [[x, -0.2], [x, -0.28], [x, -0.33], [x, -0.38]]


def curled(x):
    return [[x, -0.2], [x, -0.26], [x, -0.2], [x, -0.15]]


THUMB_OUT = [[-0.06, -0.06], [-0.12, -0.1], [-0.17, -0.13], [-0.22, -0.15]]
THUMB_TUCKED = [[-0.05, -0.06], [-0.07, -0.12], [-0.04, -0.16], [0.0, -0.18]]

PALM = hand(THUMB_OUT, extended(-0.06), extended(0), extended(0.05), extended(0.1))
FIST = hand(THUMB_TUCKED, curled(-0.06), curled(0), curled(0.05), curled(0.1))
# Index bent forward so its tip meets the thumb tip; other fingers curled.
PINCH = hand([[-0.06, -0.06], [-0.11, -0.12], [-0.13, -0.18], [-0.12, -0.23]],
             [[-0.06, -0.2], [-0.08, -0.27], [-0.11, -0.27], [-0.12, -0.245]],
             curled(0), curled(0.05), curled(0.1))
# Same hand with thumb and index spread apart, as when zooming.
PINCH_SPREAD = hand(THUMB_OUT, extended(-0.06), curled(0), curled(0.05), curled(0.1))
POINTING = hand(THUMB_TUCKED, extended(-0.06), curled(0), curled(0.05), curled(0.1))
PEACE = hand(THUMB_TUCKED, extended(-0.06), extended(0), curled(0.05), curled(0.1))


def feed(gestures, landmarks, frames=7):
    for _ in range(frames):
        shape = gestures.update(landmarks, aspect=1)
    return shape


def test_each_shape():
    assert classify(PALM, aspect=1) is HandShape.OPEN
    assert classify(FIST, aspect=1) is HandShape.FIST
    assert classify(PINCH, aspect=1) is HandShape.PINCH


def test_other_shapes_are_none():
    assert classify(POINTING, aspect=1) is HandShape.NONE
    assert classify(PEACE, aspect=1) is HandShape.NONE


def test_left_hand_is_mirror_of_right():
    mirrored = PALM.copy()
    mirrored[:, 0] = 1 - mirrored[:, 0]
    assert classify(mirrored, aspect=1) is HandShape.OPEN
    fist = FIST.copy()
    fist[:, 0] = 1 - fist[:, 0]
    assert classify(fist, aspect=1) is HandShape.FIST


def test_works_at_any_distance():
    # Half the size, as if the hand were twice as far from the camera.
    far = (FIST - [0.5, 0.8, 0]) * 0.5 + [0.5, 0.8, 0]
    assert classify(far, aspect=1) is HandShape.FIST


def test_one_stray_frame_does_not_flip_the_gesture():
    gestures = GestureFilter()
    assert feed(gestures, PALM) is HandShape.OPEN
    assert gestures.update(FIST, aspect=1) is HandShape.OPEN


def test_pinch_stays_active_while_spreading():
    gestures = GestureFilter()
    assert feed(gestures, PINCH) is HandShape.PINCH
    assert classify(PINCH_SPREAD, aspect=1) is HandShape.NONE  # on its own it is not a pinch
    assert feed(gestures, PINCH_SPREAD) is HandShape.PINCH


def test_pinch_ends_when_hand_opens_fully():
    gestures = GestureFilter()
    feed(gestures, PINCH)
    feed(gestures, PINCH_SPREAD)
    assert feed(gestures, PALM) is HandShape.OPEN
    assert feed(gestures, PINCH_SPREAD) is HandShape.NONE


def test_no_hand_clears_at_once():
    gestures = GestureFilter()
    feed(gestures, FIST)
    assert gestures.update(None) is HandShape.NONE
    assert not gestures.pinch_latched


def test_palm_center_follows_the_hand_not_the_fingers():
    # Same knuckles, different finger shapes: same position.
    assert np.allclose(palm_center(PINCH_SPREAD), palm_center(POINTING))
    # Whole hand moved: position moves by the same amount.
    moved = FIST + [0.1, -0.05, 0]
    assert np.allclose(palm_center(moved) - palm_center(FIST), [0.1, -0.05])
    assert palm_center(None) is None


def test_letting_go_is_fast_but_engaging_still_needs_votes():
    gestures = GestureFilter()
    assert feed(gestures, FIST) is HandShape.FIST
    assert gestures.update(POINTING, aspect=1) is HandShape.FIST  # one frame: could be noise
    assert gestures.update(POINTING, aspect=1) is HandShape.NONE  # two frames: let go now
    assert feed(gestures, FIST, frames=4) is HandShape.NONE
    assert gestures.update(FIST, aspect=1) is HandShape.FIST      # fifth vote
