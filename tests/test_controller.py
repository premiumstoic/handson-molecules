"""Gesture-to-camera mapping, without opening a 3D window.

RecordingController skips the PyVista setup and records the camera actions
that update() asks for.
"""

import numpy as np
import pytest

from handson.controller import RESET_HOLD_S, ROTATE_DEG_PER_UNIT, ViewController
from handson.gestures import HandShape


class RecordingController(ViewController):
    def __init__(self):
        self.calls = []
        self._release()

    def rotate(self, azimuth_deg, elevation_deg):
        self.calls.append(("rotate", azimuth_deg, elevation_deg))

    def zoom(self, factor):
        self.calls.append(("zoom", factor))

    def reset(self):
        self.calls.append(("reset",))


def hand_at(x, y, spread=0.0):
    """Hand with its palm centre at (x, y), hand size 0.2, and thumb and index tips `spread` hand sizes apart."""
    points = np.zeros((21, 3))
    points[:, 0], points[:, 1] = x, y
    points[0, 1] = y + 0.16             # wrist
    points[[5, 9, 13, 17], 1] = y - 0.04  # knuckles: wrist -> middle knuckle = 0.2, palm centre stays at y
    points[4, 0] = x - spread * 0.1     # thumb tip
    points[8, 0] = x + spread * 0.1     # index tip
    return points


def test_no_hand_or_other_shape_does_nothing():
    c = RecordingController()
    assert c.update(HandShape.NONE, None, now=0) == "idle"
    assert c.update(HandShape.NONE, hand_at(0.5, 0.5), now=0.1) == "idle"
    assert c.calls == []


def test_fist_rotates_with_hand_movement_and_never_jumps_on_start():
    c = RecordingController()
    assert c.update(HandShape.FIST, hand_at(0.5, 0.5), now=0) == "rotate"
    assert c.calls == []  # first frame only sets the reference
    c.update(HandShape.FIST, hand_at(0.6, 0.4), now=0.033)  # right and up
    (name, azimuth, elevation), = c.calls
    assert name == "rotate"
    assert azimuth == pytest.approx(0.1 * ROTATE_DEG_PER_UNIT)
    assert elevation == pytest.approx(0.1 * ROTATE_DEG_PER_UNIT)


def test_jitter_is_ignored_but_slow_drift_adds_up():
    c = RecordingController()
    c.update(HandShape.FIST, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.FIST, hand_at(0.501, 0.5), now=0.033)
    assert c.calls == []
    c.update(HandShape.FIST, hand_at(0.503, 0.5), now=0.066)
    assert c.calls[0][1] == pytest.approx(0.003 * ROTATE_DEG_PER_UNIT)


def test_releasing_the_fist_is_the_clutch():
    c = RecordingController()
    c.update(HandShape.FIST, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.NONE, hand_at(0.2, 0.2), now=0.033)  # moved while not a fist
    c.update(HandShape.FIST, hand_at(0.2, 0.2), now=0.066)  # grab again somewhere else
    assert c.calls == []


def test_pinch_spread_zooms_in_and_close_zooms_out():
    c = RecordingController()
    c.update(HandShape.PINCH, hand_at(0.5, 0.5, spread=0.1), now=0)
    c.update(HandShape.PINCH, hand_at(0.5, 0.5, spread=0.6), now=0.033)
    c.update(HandShape.PINCH, hand_at(0.5, 0.5, spread=0.3), now=0.066)
    (_, closer), (_, farther) = c.calls
    assert closer > 1 > farther


def test_open_palm_resets_once_after_holding():
    c = RecordingController()
    assert c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=0) == "hold to reset"
    assert c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=RESET_HOLD_S / 2) == "hold to reset"
    assert c.calls == []
    assert c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=RESET_HOLD_S) == "reset"
    assert c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=RESET_HOLD_S + 1) == "idle"
    assert c.calls == [("reset",)]


def test_short_open_palm_does_not_reset():
    c = RecordingController()
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.NONE, hand_at(0.5, 0.5), now=0.5)
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=0.6)
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=1.2)
    assert c.calls == []
