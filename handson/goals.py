"""Study task goals, checked from the 3D view so a task ends only when it is really done.

Each goal looks at the molecule (centred on the origin) and the camera, and says
whether the goal is met right now. Plain numpy, no rendering, so it is unit-tested.
"""

import math
from dataclasses import dataclass

import numpy as np

from .molecule import Molecule


@dataclass(frozen=True)
class CameraView:
    position: np.ndarray     # camera position
    focal_point: np.ndarray  # point the camera looks at (the molecule centre unless panned)
    view_angle_deg: float    # vertical field of view

    @property
    def toward_viewer(self) -> np.ndarray:
        """Unit vector from the focal point to the camera."""
        d = np.asarray(self.position, float) - np.asarray(self.focal_point, float)
        return d / np.linalg.norm(d)

    def view_height_at(self, point: np.ndarray) -> float:
        """Height of the visible area at the depth of `point`."""
        depth = abs(float(np.dot(np.asarray(self.position, float) - point, self.toward_viewer)))
        return 2 * depth * math.tan(math.radians(self.view_angle_deg) / 2)


def _angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    cos = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return math.degrees(math.acos(float(np.clip(cos, -1, 1))))


def _ring(molecule: Molecule, size: int) -> np.ndarray:
    ring = next(r for r in molecule.rings if len(r) == size)
    return molecule.positions[list(ring)]


@dataclass(frozen=True)
class FaceAtom:
    """An atom of `element` (with exactly `hydrogens` H neighbours, if given) points at the viewer."""
    element: str
    hydrogens: int | None = None
    max_angle_deg: float = 20

    def candidates(self, molecule: Molecule) -> list[int]:
        h_count = [0] * len(molecule.symbols)
        for a, b, _order in molecule.bonds:
            if molecule.symbols[b] == "H":
                h_count[a] += 1
            if molecule.symbols[a] == "H":
                h_count[b] += 1
        return [i for i, s in enumerate(molecule.symbols)
                if s == self.element and (self.hydrogens is None or h_count[i] == self.hydrogens)]

    def met(self, molecule: Molecule, view: CameraView) -> bool:
        return any(_angle_deg(molecule.positions[i], view.toward_viewer) <= self.max_angle_deg
                   for i in self.candidates(molecule))


@dataclass(frozen=True)
class RingEdgeOn:
    """The ring's plane points at the viewer, so the ring looks like a flat line."""
    size: int = 6
    max_tilt_deg: float = 15

    def met(self, molecule: Molecule, view: CameraView) -> bool:
        ring = _ring(molecule, self.size)
        normal = np.linalg.svd(ring - ring.mean(axis=0))[2][2]
        return abs(float(np.dot(normal, view.toward_viewer))) <= math.sin(math.radians(self.max_tilt_deg))


@dataclass(frozen=True)
class RingFillsView:
    """The ring is zoomed in to at least `min_fraction` of the view height."""
    size: int = 6
    min_fraction: float = 0.5

    def met(self, molecule: Molecule, view: CameraView) -> bool:
        ring = _ring(molecule, self.size)
        diameter = max(np.linalg.norm(a - b) for a in ring for b in ring)
        return diameter / view.view_height_at(ring.mean(axis=0)) >= self.min_fraction


@dataclass(frozen=True)
class MoleculeSmall:
    """Zoomed out until the whole molecule is at most `max_fraction` of the view height."""
    max_fraction: float = 0.25

    def met(self, molecule: Molecule, view: CameraView) -> bool:
        diameter = 2 * float(np.linalg.norm(molecule.positions, axis=1).max())
        return diameter / view.view_height_at(np.zeros(3)) <= self.max_fraction
