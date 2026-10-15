"""Map hand shapes and hand movement to camera actions on the 3D view."""

import math
import time

import numpy as np
import pyvista as pv

from .gestures import HandShape, palm_center

# Sensitivities: tune these with testers (QA checklist section B).
ROTATE_DEG_PER_UNIT = 300  # moving the hand across the whole camera image turns the molecule 300 degrees
ZOOM_PER_HAND_SIZE = 1.0   # spreading thumb and index by one hand size zooms by e^1 (about 2.7x)
MOVE_DEADZONE = 0.002      # palm movement smaller than this (in image units) is treated as jitter
RESET_HOLD_S = 1.0         # open palm must be held this long before the view resets


class ViewController:
    def __init__(self, plotter: pv.Plotter):
        self.plotter = plotter
        self.set_home()
        self._release()

    def set_home(self) -> None:
        """Fit the camera to what is drawn and make that the view reset() returns to."""
        self.plotter.reset_camera()
        self._home = self.plotter.camera_position

    # --- Camera actions (already working; used by keyboard shortcuts) ---

    def rotate(self, azimuth_deg: float, elevation_deg: float) -> None:
        camera = self.plotter.camera
        camera.Azimuth(azimuth_deg)
        camera.Elevation(elevation_deg)
        camera.OrthogonalizeViewUp()  # keeps the view stable when rotating over the top
        self.plotter.render()

    def zoom(self, factor: float) -> None:
        """factor > 1 moves closer, < 1 moves away."""
        # Dolly moves the camera itself, so reset() can restore it exactly.
        self.plotter.camera.Dolly(factor)
        self.plotter.renderer.ResetCameraClippingRange()
        self.plotter.render()

    def reset(self) -> None:
        self.plotter.camera_position = self._home
        self.plotter.render()

    # --- Gesture mapping ---

    def update(self, shape: HandShape, landmarks: np.ndarray | None, now: float | None = None) -> str:
        """Called every frame. Returns a short description of the current action for the status panel.

        Movement is measured relative to the previous frame of the same gesture, so
        starting a gesture never makes the molecule jump. Any other shape, or no
        hand, releases the clutch and nothing moves.
        """
        now = time.monotonic() if now is None else now
        if shape is not self._shape or landmarks is None:
            self._release()
            self._shape = shape if landmarks is not None else HandShape.NONE

        if self._shape is HandShape.FIST:
            return self._rotate_with(palm_center(landmarks))
        if self._shape is HandShape.PINCH:
            return self._zoom_with(_pinch_spread(landmarks))
        if self._shape is HandShape.OPEN:
            return self._reset_after_hold(now)
        return "idle"

    def _rotate_with(self, position: np.ndarray) -> str:
        if self._last_position is not None:
            dx, dy = position - self._last_position
            if math.hypot(dx, dy) < MOVE_DEADZONE:
                return "rotate"  # keep the old reference so slow drifts still add up
            # Same directions as the arrow keys: hand right = Right, hand up = Up (image y grows downward).
            self.rotate(dx * ROTATE_DEG_PER_UNIT, -dy * ROTATE_DEG_PER_UNIT)
        self._last_position = position
        return "rotate"

    def _zoom_with(self, spread: float) -> str:
        if self._last_spread is not None:
            self.zoom(math.exp((spread - self._last_spread) * ZOOM_PER_HAND_SIZE))
        self._last_spread = spread
        return "zoom"

    def _reset_after_hold(self, now: float) -> str:
        if self._reset_done:
            return "idle"
        if self._open_since is None:
            self._open_since = now
        self.hold_progress = min((now - self._open_since) / RESET_HOLD_S, 1.0)
        if self.hold_progress < 1.0:
            return "hold to reset"
        self.reset()
        self._reset_done = True  # wait until the hand changes shape before resetting again
        self.hold_progress = 0.0
        return "reset"

    def _release(self) -> None:
        self._shape = HandShape.NONE
        self._last_position: np.ndarray | None = None
        self._last_spread: float | None = None
        self._open_since: float | None = None
        self._reset_done = False
        self.hold_progress = 0.0  # 0..1 while an open palm is held, for the status panel


def _pinch_spread(landmarks: np.ndarray) -> float:
    """Thumb tip to index tip distance, in hand sizes (wrist -> middle knuckle)."""
    points = np.asarray(landmarks, dtype=float)[:, :2]
    size = np.linalg.norm(points[9] - points[0]) or 1e-6
    return float(np.linalg.norm(points[8] - points[4]) / size)
