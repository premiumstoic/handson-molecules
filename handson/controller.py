"""Map hand shapes and hand movement to camera actions on the 3D view."""

import time 
import numpy as np
import pyvista as pv

from .gestures import HandShape


class ViewController:
    def __init__(self, plotter: pv.Plotter):
        self.plotter = plotter
        self.plotter.reset_camera()
        self._home = self.plotter.camera_position
        self.last_shape = HandShape.NONE
        self.last_wrist= None
        self.last_pinch = None
        self.rest_done = False
        self.rotation_speed = 180.0
        self.zoom_speed = 2.0 

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


    def update(self, shape: HandShape, landmarks: np.ndarray | None) -> str:
        """Control the molecule using detected hand gestures."""

        if landmarks is None or shape == HandShape.NONE:
            self.last_shape = HandShape.NONE
            self.last_wrist = None
            self.last_pinch = None
            self.open_start = None
            self.reset_done = False
            return "idle"

        points = np.asarray(landmarks)

        if points.shape != (21, 3) and points.shape != (21, 2):
            return "invalid landmarks"

        wrist = points[0, :2].copy()
        thumb = points[4, :2]
        index = points[8, :2]

        pinch_distance = float(np.linalg.norm(thumb - index))

        # Switching gestures disengages the previous action.
        if shape != self.last_shape:
            self.last_shape = shape
            self.last_wrist = wrist
            self.last_pinch = pinch_distance
            self.open_start = None
            self.reset_done = False
            return "ready"

        # Fist: move the wrist to rotate the molecule.
        if shape == HandShape.FIST:
            if self.last_wrist is not None:
                movement = wrist - self.last_wrist

                dx = float(movement[0])
                dy = float(movement[1])

                if abs(dx) > 0.002 or abs(dy) > 0.002:
                    self.rotate(
                        dx * self.rotation_speed,
                        -dy * self.rotation_speed
                    )

            self.last_wrist = wrist
            return "rotating"

        # Pinch: change finger distance to zoom.
        if shape == HandShape.PINCH:
            if self.last_pinch is not None:
                change = pinch_distance - self.last_pinch

                if abs(change) > 0.002:
                    factor = 1.0 + change * self.zoom_speed
                    factor = max(0.8, min(1.2, factor))
                    self.zoom(factor)

            self.last_pinch = pinch_distance
            return "zooming"

        # Open palm: hold for one second to reset.
        if shape == HandShape.OPEN:
            if self.open_start is None:
                self.open_start = time.monotonic()

            elapsed = time.monotonic() - self.open_start

            if elapsed >= 1.0 and not self.reset_done:
                self.reset()
                self.reset_done = True
                return "view reset"

            if self.reset_done:
                return "reset complete"

            return "hold palm to reset"

        return "idle"
