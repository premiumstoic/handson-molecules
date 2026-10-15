"""User study session: participant, condition, and experimenter task markers.

The experimenter presses keys while the participant works (see README):
    T      start the next task
    Space  task done
    F      the participant triggered something they did not mean to (false trigger)
Every marker goes into the session log, which scripts/analyze_logs.py reads.
"""

from .logger import EventLogger

CONDITIONS = ("gesture", "mouse")


class StudySession:
    def __init__(self, logger: EventLogger, participant: str, condition: str):
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition '{condition}'. Choose from: {', '.join(CONDITIONS)}")
        self.logger = logger
        self.participant = participant
        self.condition = condition
        self.task = 0
        self.running = False
        logger.log("participant", participant)
        logger.log("condition", condition)

    def start_task(self) -> None:
        if self.running:
            self.logger.log("task_abandoned", str(self.task))
        self.task += 1
        self.running = True
        self.logger.log("task_start", str(self.task))

    def end_task(self) -> None:
        if not self.running:
            return
        self.running = False
        self.logger.log("task_end", str(self.task))

    def false_trigger(self) -> None:
        self.logger.log("false_trigger", str(self.task))

    def status_text(self) -> str:
        if self.task == 0:
            state = "press T to start task 1"
        elif self.running:
            state = f"task {self.task} running"
        else:
            state = f"task {self.task} done, T for next"
        return f"{self.participant} · {self.condition} · {state}"
