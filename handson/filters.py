"""Landmark smoothing with the One Euro filter (Casiez, Roussel and Vogel, CHI 2012).

A low-pass filter whose cutoff rises with speed: when the hand is still it
smooths strongly (no jitter), and when the hand moves fast it smooths little
(no lag). Applied to every landmark coordinate at once.
"""

import math

import numpy as np

# Tune with testers (QA checklist section C: "hand held still for 10 s").
MIN_CUTOFF_HZ = 1.0  # smoothing when still: lower = steadier but laggier
BETA = 5.0           # how fast the cutoff rises with speed: higher = less lag when moving
D_CUTOFF_HZ = 1.0    # smoothing of the speed estimate itself


def _alpha(cutoff_hz: float | np.ndarray, dt: float) -> float | np.ndarray:
    tau = 1.0 / (2 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = MIN_CUTOFF_HZ, beta: float = BETA, d_cutoff: float = D_CUTOFF_HZ):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def __call__(self, values: np.ndarray | None, t: float) -> np.ndarray | None:
        """Filter one frame of values taken at time `t` (seconds). None (no hand) resets the filter."""
        if values is None:
            self.reset()
            return None
        values = np.asarray(values, dtype=float)
        if self._value is None:
            self._value, self._speed, self._t = values.copy(), np.zeros_like(values), t
            return values
        dt = t - self._t
        if dt <= 0:
            return self._value
        speed = (values - self._value) / dt
        self._speed = self._speed + _alpha(self.d_cutoff, dt) * (speed - self._speed)
        cutoff = self.min_cutoff + self.beta * np.abs(self._speed)
        self._value = self._value + _alpha(cutoff, dt) * (values - self._value)
        self._t = t
        return self._value

    def reset(self) -> None:
        self._value: np.ndarray | None = None
        self._speed: np.ndarray | None = None
        self._t = 0.0
