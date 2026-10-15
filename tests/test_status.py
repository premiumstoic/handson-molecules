"""What the status card shows (no Qt needed)."""

from pathlib import Path

import pytest

from handson.gestures import HandShape
from handson.status import STYLES, card_view

ASSETS = Path(__file__).resolve().parent.parent / "handson" / "assets"
TRACKING = ["mouse", "off", "waiting", "detected", "lost"]


@pytest.mark.parametrize("tracking", TRACKING)
@pytest.mark.parametrize("shape", list(HandShape))
def test_every_state_has_a_label_an_existing_icon_and_a_style(tracking, shape):
    view = card_view(tracking, shape)
    assert view.label  # never colour alone
    assert (ASSETS / view.icon).exists()
    assert view.style in STYLES


def test_teal_when_detected_yellow_when_lost():
    assert card_view("detected", HandShape.FIST).style == "active"
    assert STYLES["active"] != STYLES["lost"]
    assert card_view("lost", HandShape.NONE).style == "lost"
    assert card_view("lost", HandShape.NONE).label == "Tracking Lost"


def test_each_gesture_shows_its_own_icon_and_name():
    assert card_view("detected", HandShape.FIST).icon == "fist.png"
    assert card_view("detected", HandShape.PINCH).label == "Pinch"
    assert card_view("detected", HandShape.NONE).label == "No Gesture"


def test_open_palm_hint_follows_the_reset():
    assert card_view("detected", HandShape.OPEN, "hold to reset").hint == "Hold still to reset"
    assert card_view("detected", HandShape.OPEN, "reset").hint == "View reset"
