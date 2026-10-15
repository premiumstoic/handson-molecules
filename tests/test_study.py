"""Study session markers in the event log."""

import csv

import pytest

from handson.logger import EventLogger
from handson import molecule
from handson.study import TASKS, StudySession, StudyTask


def events(logger):
    logger.close()
    return [row[1:] for row in list(csv.reader(logger.path.open()))[1:]]


def test_log_file_name_has_participant_and_condition(tmp_path):
    logger = EventLogger(tmp_path, tag="P01-gesture")
    assert logger.path.name.endswith("-P01-gesture.csv")
    logger.close()


def test_task_markers(tmp_path):
    logger = EventLogger(tmp_path)
    study = StudySession(logger, "P01", "gesture")
    study.end_task()          # nothing running: ignored
    study.start_task()
    study.false_trigger()
    study.end_task()
    study.start_task()
    study.start_task()        # task 2 never finished
    assert events(logger) == [
        ["participant", "P01"], ["condition", "gesture"],
        ["task_start", "1"], ["false_trigger", "1"], ["task_end", "1"],
        ["task_start", "2"], ["task_abandoned", "2"], ["task_start", "3"],
    ]


def test_status_text_tells_the_experimenter_what_is_next(tmp_path):
    study = StudySession(EventLogger(tmp_path), "P02", "mouse")
    assert "press T" in study.status_text()
    study.start_task()
    assert "task 1 of 4 running" in study.status_text()
    study.end_task()
    assert "task 1 done" in study.status_text()


def test_unknown_condition_is_refused(tmp_path):
    with pytest.raises(ValueError):
        StudySession(EventLogger(tmp_path), "P03", "keyboard")


def test_tasks_are_shown_in_order_then_finish(tmp_path):
    tasks = [StudyTask("caffeine", "First"), StudyTask("aspirin", "Second")]
    study = StudySession(EventLogger(tmp_path), "P04", "gesture", tasks)
    assert "first task will appear" in study.task_text()
    assert study.start_task().text == "First"
    assert study.task_text() == "Task 1 of 2\nFirst"
    study.end_task()
    assert "Wait for the next task" in study.task_text()
    assert study.start_task().molecule == "aspirin"
    study.end_task()
    assert study.start_task() is None  # no task 3
    assert study.finished
    assert "Thank you" in study.task_text()
    assert "all tasks done" in study.status_text()


def test_every_task_uses_a_molecule_the_app_has():
    assert TASKS
    assert all(task.molecule in molecule.MOLECULES for task in TASKS)
