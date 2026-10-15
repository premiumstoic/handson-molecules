"""User study session: participant, condition, and experimenter task markers.

The experimenter presses keys while the participant works (see README):
    T      start the next task: it is shown on screen and its molecule is loaded
    Space  task done
    F      the participant triggered something they did not mean to (false trigger)
Every marker goes into the session log, which scripts/analyze_logs.py reads.
"""

from dataclasses import dataclass

from .logger import EventLogger

CONDITIONS = ("gesture", "mouse")


@dataclass(frozen=True)
class StudyTask:
    molecule: str
    text: str


# The same tasks, in the same order, for both conditions. Placeholder set until the T8
# study plan fixes the final tasks; the first two come from the project proposal.
TASKS = [
    StudyTask("caffeine", "Rotate the molecule until a red oxygen atom points straight at you."),
    StudyTask("caffeine", "Zoom in until the six-sided ring fills most of the view."),
    StudyTask("aspirin", "Turn the molecule so the six-sided ring is seen edge-on, as a flat line."),
    StudyTask("adenine", "Find the blue nitrogen with two white hydrogens and turn it toward you."),
]


class StudySession:
    def __init__(self, logger: EventLogger, participant: str, condition: str, tasks: list[StudyTask] = TASKS):
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition '{condition}'. Choose from: {', '.join(CONDITIONS)}")
        self.logger = logger
        self.participant = participant
        self.condition = condition
        self.tasks = tasks
        self.task = 0
        self.running = False
        logger.log("participant", participant)
        logger.log("condition", condition)

    @property
    def current(self) -> StudyTask | None:
        return self.tasks[self.task - 1] if 0 < self.task <= len(self.tasks) else None

    @property
    def finished(self) -> bool:
        return self.task >= len(self.tasks) and not self.running

    def start_task(self) -> StudyTask | None:
        """Start the next task and return it, or None when all tasks are done."""
        if self.running:
            self.logger.log("task_abandoned", str(self.task))
            self.running = False
        if self.task >= len(self.tasks):
            return None
        self.task += 1
        self.running = True
        self.logger.log("task_start", str(self.task))
        return self.current

    def end_task(self) -> None:
        if not self.running:
            return
        self.running = False
        self.logger.log("task_end", str(self.task))

    def false_trigger(self) -> None:
        self.logger.log("false_trigger", str(self.task))

    def status_text(self) -> str:
        """Experimenter's line: who, which condition, what to press next."""
        total = len(self.tasks)
        if self.task == 0:
            state = "press T to start task 1"
        elif self.running:
            state = f"task {self.task} of {total} running, Space when done"
        elif self.finished:
            state = "all tasks done"
        else:
            state = f"task {self.task} done, T for next"
        return f"{self.participant} · {self.condition} · {state}"

    def task_text(self) -> str:
        """What the participant reads."""
        if self.task == 0:
            return "Get ready. Your first task will appear here."
        if self.running:
            return f"Task {self.task} of {len(self.tasks)}\n{self.current.text}"
        if self.finished:
            return "All tasks done. Thank you!"
        return "Done. Wait for the next task."
