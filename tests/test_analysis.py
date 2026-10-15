"""Study log analysis on hand-written logs."""

import math

from handson.analysis import markdown_report, read_logs, read_session, summarize, write_task_csv

GESTURE_LOG = """time_s,event,detail
0.000,app_start,caffeine
0.000,participant,P01
0.000,condition,gesture
1.000,task_start,1
2.000,action,rotate
2.500,action,idle
3.000,action,rotate
4.000,false_trigger,1
11.000,task_end,1
11.200,false_trigger,1
12.000,task_start,2
20.000,task_abandoned,2
21.000,task_start,3
25.000,action,zoom
26.000,task_end,3
"""

MOUSE_LOG = """time_s,event,detail
0.000,app_start,caffeine
0.000,participant,P01
0.000,condition,mouse
1.000,task_start,1
5.000,task_end,1
"""

PLAIN_LOG = """time_s,event,detail
0.000,app_start,caffeine
1.000,gesture,fist
"""


def write_logs(tmp_path):
    for name, text in [("session-1-P01-gesture.csv", GESTURE_LOG), ("session-2-P01-mouse.csv", MOUSE_LOG),
                       ("session-3.csv", PLAIN_LOG)]:
        (tmp_path / name).write_text(text)


def test_task_times_false_triggers_and_actions(tmp_path):
    write_logs(tmp_path)
    task1, task2, task3 = read_session(tmp_path / "session-1-P01-gesture.csv")
    assert (task1.seconds, task1.false_triggers, task1.actions["rotate"]) == (10.0, 2, 2)  # late F still counts
    assert not task2.completed
    assert (task3.seconds, task3.actions["zoom"]) == (5.0, 1)


def test_sessions_without_a_participant_are_skipped(tmp_path):
    write_logs(tmp_path)
    assert read_session(tmp_path / "session-3.csv") == []
    assert len(read_logs(tmp_path)) == 4


def test_summary_per_condition(tmp_path):
    write_logs(tmp_path)
    summary = summarize(read_logs(tmp_path))
    gesture, mouse = summary["gesture"], summary["mouse"]
    assert (gesture["tasks_completed"], gesture["tasks_abandoned"]) == (2, 1)
    assert gesture["mean_s"] == 7.5 and gesture["false_triggers_per_task"] == 1.0
    assert (mouse["mean_s"], mouse["false_triggers_per_task"]) == (4.0, 0.0)


def test_report_and_csv(tmp_path):
    write_logs(tmp_path)
    results = read_logs(tmp_path)
    report = markdown_report(results)
    assert "| gesture | 1 | 2 | 1 | 7.5 |" in report
    assert "| 1 | 10.00 | 4.00 |" in report
    write_task_csv(results, tmp_path / "out" / "tasks.csv")
    lines = (tmp_path / "out" / "tasks.csv").read_text().splitlines()
    assert lines[0].startswith("participant,condition,task,seconds")
    assert len(lines) == 5


def test_no_completed_tasks_gives_nan_not_an_error(tmp_path):
    (tmp_path / "session-1.csv").write_text(
        "time_s,event,detail\n0,participant,P09\n0,condition,mouse\n1,task_start,1\n2,task_abandoned,1\n")
    assert math.isnan(summarize(read_logs(tmp_path))["mouse"]["mean_s"])
