"""Health line: counts per second, so the log shows what stopped during a freeze."""

from handson.health import REPORT_EVERY_S, HealthMonitor


def test_reports_once_per_period_with_counts():
    health = HealthMonitor(now=0)
    for i in range(30):
        health.tick(now=i / 30)
        health.frame()
    health.render_started(now=0.5)
    health.render_ended(now=0.52)
    assert health.report(now=0.9, window="normal-active") is None    # period not over yet
    line = health.report(now=REPORT_EVERY_S, window="fullscreen-active")
    assert line == "ticks=30 frames=30 renders=1 max_gap_ms=33 max_render_ms=20 window=fullscreen-active"
    assert health.ticks == health.frames == health.renders == 0          # a new period starts


def test_a_stalled_main_loop_shows_as_a_long_gap():
    health = HealthMonitor(now=0)
    health.tick(now=0.9)
    health.report(now=1.0, window="normal-active")
    health.tick(now=3.4)                                                  # nothing ran for 2.5 s
    line = health.report(now=3.4, window="normal-active")
    assert "ticks=1 frames=0" in line and "max_gap_ms=2500" in line
