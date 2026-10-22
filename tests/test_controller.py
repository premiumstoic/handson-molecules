
import numpy as np
from unittest.mock import MagicMock, patch

from handson.controller import ViewController
from handson.gestures import HandShape


def make_controller():
    plotter = MagicMock()
    plotter.camera_position = [
        (0, 0, 10),
        (0, 0, 0),
        (0, 1, 0),
    ]
    return ViewController(plotter)


def make_landmarks():
    points = np.zeros((21, 3))
    points[4, 0] = 0.2
    points[8, 0] = 0.3
    return points


def test_fist_rotation():
    controller = make_controller()
    points = make_landmarks()

    with patch.object(controller, "rotate") as rotate:
        assert controller.update(HandShape.FIST, points) == "ready"

        points[0, 0] = 0.1
        assert controller.update(HandShape.FIST, points) == "rotating"
        rotate.assert_called_once()


def test_pinch_zoom():
    controller = make_controller()
    points = make_landmarks()

    with patch.object(controller, "zoom") as zoom:
        assert controller.update(HandShape.PINCH, points) == "ready"

        points[8, 0] = 0.4
        assert controller.update(HandShape.PINCH, points) == "zooming"
        zoom.assert_called_once()


def test_open_palm_reset():
    controller = make_controller()
    points = make_landmarks()

    with patch.object(controller, "reset") as reset:
        with patch("handson.controller.time.monotonic",
                   side_effect=[0.0, 0.0, 1.1]):
            assert controller.update(HandShape.OPEN, points) == "ready"
            assert controller.update(HandShape.OPEN, points) == "hold palm to reset"
            assert controller.update(HandShape.OPEN, points) == "view reset"

        reset.assert_called_once()


def test_no_hand():
    controller = make_controller()
    assert controller.update(HandShape.NONE, None) == "idle"
