"""Once-a-second health line for the session log, to find out what stops when the app freezes.

No Qt, so it can be unit-tested anywhere; app.py feeds it. Each line tells apart:
- the main loop stalling (few ticks, a long max_gap_ms),
- the camera stalling (few new frames while ticks are normal),
- slow drawing (a long max_render_ms),
- or none of these, which points at the screen not showing what the app draws.
"""

REPORT_EVERY_S = 1.0


class HealthMonitor:
    def __init__(self, now: float):
        self._reset(now)

    def _reset(self, now: float) -> None:
        self._since = now
        self._last_tick: float | None = None
        self.ticks = 0
        self.frames = 0
        self.renders = 0
        self.max_gap = 0.0
        self.max_render = 0.0
        self._render_started: float | None = None

    def tick(self, now: float) -> None:
        """The app's timer fired (it should, about 30 times a second)."""
        if self._last_tick is not None:
            self.max_gap = max(self.max_gap, now - self._last_tick)
        self._last_tick = now
        self.ticks += 1

    def frame(self) -> None:
        """A new camera frame reached the main thread."""
        self.frames += 1

    def render_started(self, now: float) -> None:
        self._render_started = now

    def render_ended(self, now: float) -> None:
        if self._render_started is not None:
            self.max_render = max(self.max_render, now - self._render_started)
            self._render_started = None
        self.renders += 1

    def report(self, now: float, window: str) -> str | None:
        """The health line once REPORT_EVERY_S has passed, else None. Starts a new period."""
        if now - self._since < REPORT_EVERY_S:
            return None
        line = (f"ticks={self.ticks} frames={self.frames} renders={self.renders} "
                f"max_gap_ms={self.max_gap * 1000:.0f} max_render_ms={self.max_render * 1000:.0f} window={window}")
        last_tick = self._last_tick
        self._reset(now)
        self._last_tick = last_tick  # keep measuring the gap across the period boundary
        return line
