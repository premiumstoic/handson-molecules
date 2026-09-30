import csv

from handson import molecule
from handson.gestures import HandShape, classify
from handson.logger import EventLogger


def test_caffeine_has_expected_atoms_and_bonds():
    caffeine = molecule.load("caffeine")
    # C8H10N4O2 = 24 atoms; 15 heavy-atom bonds + 10 C-H bonds = 25
    assert len(caffeine.symbols) == 24
    assert sorted(set(caffeine.symbols)) == ["C", "H", "N", "O"]
    assert len(caffeine.bonds) == 25
    assert caffeine.positions.shape == (24, 3)


def test_molecule_is_centred():
    aspirin = molecule.load("aspirin")
    assert abs(aspirin.positions.mean(axis=0)).max() < 1e-6


def test_no_hand_is_none():
    assert classify(None) is HandShape.NONE


def test_logger_writes_csv(tmp_path):
    logger = EventLogger(tmp_path)
    logger.log("gesture", "fist")
    logger.close()
    rows = list(csv.reader(logger.path.open()))
    assert rows[0] == ["time_s", "event", "detail"]
    assert rows[1][1:] == ["gesture", "fist"]
