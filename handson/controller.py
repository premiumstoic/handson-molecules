"""Map hand shapes and hand movement to camera actions on the 3D view."""

import numpy as np
import pyvista as pv

from .gestures import HandShape


class ViewController:
    def __init__(self, plotter: pv.Plotter):
        self.plotter = plotter
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

    def update(self, shape: HandShape, landmarks: np.ndarray | None) -> str:
        """Called every frame. Returns a short description of the current action for the status panel.

        TODO (implementation team):
          - FIST held: rotate by how far the wrist (landmark 0) moved since the last
            frame (relative movement). Horizontal -> azimuth, vertical -> elevation.
          - PINCH held: zoom by the change in thumb-index distance since the last frame.
          - OPEN held ~1 s: reset() once, then wait until the hand changes shape.
          - Any other shape: do nothing (this is the "clutch").
          - Smooth landmarks with a One Euro filter before computing movement.
          - Start with one sensitivity constant per action and tune it with testers.
        """
        return "idle"
