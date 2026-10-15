"""One Euro landmark filter."""

import numpy as np

from handson.filters import OneEuroFilter

FPS = 30


def run(filt, frames):
    return [filt(frame, i / FPS) for i, frame in enumerate(frames)]


def test_first_frame_passes_through():
    hand = np.random.default_rng(0).random((21, 3))
    assert np.allclose(OneEuroFilter()(hand, 0.0), hand)


def test_still_hand_jitter_is_reduced():
    rng = np.random.default_rng(1)
    still = np.full((21, 3), 0.5)
    noisy = [still + rng.normal(0, 0.003, still.shape) for _ in range(90)]
    out = run(OneEuroFilter(), noisy)
    assert np.std(np.array(out[30:])) < 0.5 * np.std(np.array(noisy[30:]))


def test_fast_move_catches_up():
    frames = [np.full((21, 3), 0.3)] * 10 + [np.full((21, 3), 0.7)] * 20
    out = run(OneEuroFilter(), frames)
    assert np.allclose(out[-1], 0.7, atol=0.01)  # within 20 frames (~0.7 s)


def test_no_hand_resets():
    filt = OneEuroFilter()
    filt(np.full((21, 3), 0.2), 0.0)
    assert filt(None, 0.1) is None
    # The hand comes back elsewhere: no drag from the old position.
    assert np.allclose(filt(np.full((21, 3), 0.8), 0.2), 0.8)
