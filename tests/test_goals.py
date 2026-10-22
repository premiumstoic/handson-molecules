"""Task goals checked from the camera, on real molecules."""

import numpy as np
import pytest

from handson import molecule
from handson.goals import CameraView, FaceAtom, MoleculeSmall, RingEdgeOn, RingFillsView
from handson.study import TASKS


def looking_from(direction, distance=10.0, angle=30.0):
    direction = np.asarray(direction, float)
    return CameraView(direction / np.linalg.norm(direction) * distance, np.zeros(3), angle)


@pytest.fixture(scope="module")
def caffeine():
    return molecule.load("caffeine")


def test_face_atom(caffeine):
    goal = FaceAtom("O")
    oxygen = caffeine.positions[goal.candidates(caffeine)[0]]
    assert goal.met(caffeine, looking_from(oxygen))
    assert not goal.met(caffeine, looking_from(-oxygen))


def test_face_atom_with_hydrogen_count():
    adenine = molecule.load("adenine")
    goal = FaceAtom("N", hydrogens=2)
    (amine,) = goal.candidates(adenine)  # only the NH2 nitrogen
    assert goal.met(adenine, looking_from(adenine.positions[amine]))


def test_ring_edge_on():
    aspirin = molecule.load("aspirin")
    ring = aspirin.positions[list(aspirin.rings[0])]
    normal = np.linalg.svd(ring - ring.mean(axis=0))[2][2]
    in_plane = ring[0] - ring.mean(axis=0)
    assert RingEdgeOn().met(aspirin, looking_from(in_plane))
    assert not RingEdgeOn().met(aspirin, looking_from(normal))


def test_ring_fills_view_needs_zooming_in(caffeine):
    assert not RingFillsView().met(caffeine, looking_from([1, 1, 1], distance=20))
    assert RingFillsView().met(caffeine, looking_from([1, 1, 1], distance=3))


def test_molecule_small_needs_zooming_out():
    benzene = molecule.load("benzene")
    assert not MoleculeSmall().met(benzene, looking_from([1, 1, 1], distance=10))
    assert MoleculeSmall().met(benzene, looking_from([1, 1, 1], distance=60))


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.text[:30])
def test_no_task_is_done_from_the_default_view(task):
    """PyVista's reset_camera looks from (1, 1, 1); no task may start already solved."""
    mol = molecule.load(task.molecule)
    radius = float(np.linalg.norm(mol.positions, axis=1).max())
    assert not task.goal.met(mol, looking_from([1, 1, 1], distance=radius / np.sin(np.radians(15))))
