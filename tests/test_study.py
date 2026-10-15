"""Study session: tasks, automatic ending, and markers in the event log."""

import csv

import pytest

from handson import molecule
from handson.logger import EventLogger
from handson.study import GOAL_HOLD_S, TASKS, TIME_LIMIT_S, StudySession, StudyTask

GOAL = object()  # the session itself never calls the goal; the app does


def events(logger):
    logger.close()
    return [row[1:] for row in list(csv.reader(logger.path.open()))[1:]]


def two_tasks(tmp_path):
    tasks = [StudyTask("caffeine", "First", GOAL), StudyTask("aspirin", "Second", GOAL)]
    logger = EventLogger(tmp_path)
    return logger, StudySession(logger, "P01", "gesture", tasks)


def test_log_file_name_has_participant_and_condition(tmp_path):
    logger = EventLogger(tmp_path, tag="P01-gesture")
    assert logger.path.name.endswith("-P01-gesture.csv")
    logger.close()


def test_goal_held_ends_the_task(tmp_path):
    logger, study = two_tasks(tmp_path)
    study.start_task(now=0)
    assert study.update(True, now=1) == ""                  # reached, not held yet
    assert study.goal_met and "hold it there" in study.task_text()
    assert study.update(True, now=1 + GOAL_HOLD_S) == "done"
    assert not study.running and "Well done" in study.task_text()
    assert events(logger)[-2:] == [["task_start", "1"], ["task_end", "1"]]


def test_passing_through_the_goal_does_not_count(tmp_path):
    _logger, study = two_tasks(tmp_path)
    study.start_task(now=0)
    study.update(True, now=1)
    study.update(False, now=1.5)                             # moved past it
    assert study.update(True, now=1.6 + GOAL_HOLD_S / 2) == ""
    assert study.running


def test_time_limit(tmp_path):
    logger, study = two_tasks(tmp_path)
    study.start_task(now=0)
    assert study.update(False, now=TIME_LIMIT_S) == "timeout"
    assert "Time is up" in study.task_text()
    assert events(logger)[-1] == ["task_timeout", "1"]


def test_skip_false_trigger_and_finish(tmp_path):
    logger, study = two_tasks(tmp_path)
    study.skip_task()                                        # nothing running: ignored
    study.start_task(now=0)
    study.false_trigger()
    study.skip_task()
    assert study.start_task(now=10).text == "Second"
    study.start_task(now=20)                                 # T while running skips it
    assert study.start_task(now=30) is None                  # no task 3
    assert study.finished and "Thank you" in study.task_text()
    assert "all tasks done" in study.status_text()
    assert events(logger) == [
        ["participant", "P01"], ["condition", "gesture"],
        ["task_start", "1"], ["false_trigger", "1"], ["task_abandoned", "1"],
        ["task_start", "2"], ["task_abandoned", "2"],
    ]


def test_status_text_tells_the_experimenter_what_is_next(tmp_path):
    _logger, study = two_tasks(tmp_path)
    assert "press T" in study.status_text()
    study.start_task(now=0)
    assert "task 1 of 2 running, Space to skip" in study.status_text()


def test_unknown_condition_is_refused(tmp_path):
    with pytest.raises(ValueError):
        StudySession(EventLogger(tmp_path), "P03", "keyboard")


def test_every_task_uses_a_molecule_the_app_has_and_a_goal():
    assert TASKS
    for task in TASKS:
        assert task.molecule in molecule.MOLECULES
        assert hasattr(task.goal, "met")
