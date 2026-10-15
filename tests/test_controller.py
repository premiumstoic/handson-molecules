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


def hand_at(x, y):
    """Hand with its palm centre at (x, y) and hand size 0.2."""
    points = np.zeros((21, 3))
    points[:, 0], points[:, 1] = x, y
    points[0, 1] = y + 0.16             # wrist
    points[[5, 9, 13, 17], 1] = y - 0.04  # knuckles: wrist -> middle knuckle = 0.2, palm centre stays at y
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


def test_pinch_up_zooms_in_and_down_zooms_out():
    c = RecordingController()
    c.update(HandShape.PINCH, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.PINCH, hand_at(0.5, 0.4), now=0.033)  # up
    c.update(HandShape.PINCH, hand_at(0.5, 0.6), now=0.066)  # down
    (_, closer), (_, farther) = c.calls
    assert closer > 1 > farther
    assert closer * farther < 1  # moved down further than up: net zoom out


def test_zoom_out_can_be_repeated_without_a_reverse_move():
    # The old pinch-spread zoom could never zoom out; pinch-and-pull must work again and again.
    c = RecordingController()
    for start in range(3):
        c.update(HandShape.PINCH, hand_at(0.5, 0.3), now=start)
        c.update(HandShape.PINCH, hand_at(0.5, 0.5), now=start + 0.1)  # pull down
        c.update(HandShape.NONE, hand_at(0.5, 0.3), now=start + 0.2)   # let go, move back up
    factors = [factor for _, factor in c.calls]
    assert len(factors) == 3 and all(f < 1 for f in factors)


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


def test_hand_lost_and_back_elsewhere_does_not_jump():
    c = RecordingController()
    c.update(HandShape.FIST, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.NONE, None, now=0.033)               # tracking lost
    c.update(HandShape.FIST, hand_at(0.1, 0.9), now=0.5)    # back somewhere else
    c.update(HandShape.FIST, hand_at(0.1, 0.9), now=0.533)
    assert c.calls == []


def test_hold_progress_for_the_status_panel():
    c = RecordingController()
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=RESET_HOLD_S / 2)
    assert c.hold_progress == pytest.approx(0.5)
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=RESET_HOLD_S)
    assert c.hold_progress == 0  # reset done
    c.update(HandShape.OPEN, hand_at(0.5, 0.5), now=0)
    c.update(HandShape.FIST, hand_at(0.5, 0.5), now=0.1)
    assert c.hold_progress == 0
