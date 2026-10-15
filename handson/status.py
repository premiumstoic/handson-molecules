"""What the status card shows for each tracking state and gesture (Ali's T4 design).

Plain data with no Qt, so it can be unit-tested anywhere; status_panel.py draws it.
Every state has a title, an icon and a text label, so no state is shown by colour alone.
"""

from dataclasses import dataclass

from .gestures import HandShape

# Ali's palette. Text uses the dark ink rather than the mockup's yellow, for contrast.
INK = "#4a3713"
STYLES = {
    "active": ("#c5e4df", "#66b0a2"),   # teal: hand detected, gesture active
    "unknown": ("#c5e4df", "#66b0a2"),  # teal: hand detected, no gesture
    "lost": ("#fbefc8", "#f0cd6c"),     # yellow: tracking lost / camera off
    "idle": ("#e4e9e8", "#9fb0ad"),     # grey: waiting for a hand
}

GESTURE_VIEWS = {
    HandShape.FIST: ("fist.png", "Fist", "Move your hand to rotate"),
    HandShape.PINCH: ("pinch.png", "Pinch", "Spread or close to zoom"),
    HandShape.OPEN: ("palm.png", "Open Palm", "Hold still to reset"),
}


@dataclass(frozen=True)
class CardView:
    style: str   # key into STYLES
    title: str
    icon: str    # file name in assets/
    label: str
    hint: str
    faded: bool = False


def card_view(tracking: str, shape: HandShape, action: str = "idle") -> CardView:
    """tracking is one of "mouse", "off", "waiting", "detected", "lost"."""
    if tracking == "mouse":
        return CardView("idle", "Mouse Condition", "palm.png", "Use the Mouse", "Drag to rotate, scroll to zoom",
                        faded=True)
    if tracking == "off":
        return CardView("lost", "Camera Off", "warning.png", "No Tracking", "Keyboard controls still work")
    if tracking == "waiting":
        return CardView("idle", "Waiting", "palm.png", "Show Your Hand", "Fist, pinch, or open palm", faded=True)
    if tracking == "lost":
        return CardView("lost", "", "warning.png", "Tracking Lost", "Please check lighting and camera")
    if shape not in GESTURE_VIEWS:
        return CardView("unknown", "Hand Detected", "palm.png", "No Gesture", "Try a fist, pinch, or open palm",
                        faded=True)
    icon, label, hint = GESTURE_VIEWS[shape]
    if shape is HandShape.OPEN and action in ("reset", "idle"):
        hint = "View reset"
    return CardView("active", "Active Gesture", icon, label, hint)
