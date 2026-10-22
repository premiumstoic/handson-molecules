"""User study session: participant, condition, and experimenter task markers.

Each task has a goal checked from the 3D view (goals.py). A task ends by itself
once its goal has been held for GOAL_HOLD_S, or fails after TIME_LIMIT_S.

The experimenter presses keys while the participant works (see README):
    T      start the next task: it is shown on screen and its molecule is loaded
    Space  skip the current task (logged as abandoned)
    F      the participant triggered something they did not mean to (false trigger)
Every marker goes into the session log, which scripts/analyze_logs.py reads.
"""

import time
from dataclasses import dataclass

from .goals import FaceAtom, MoleculeSmall, RingEdgeOn, RingFillsView
from .logger import EventLogger

CONDITIONS = ("gesture", "mouse")
GOAL_HOLD_S = 1.0     # the goal must stay met this long, so passing through it by chance does not count
TIME_LIMIT_S = 90.0   # a task not done by then is logged as task_timeout


@dataclass(frozen=True)
class StudyTask:
    molecule: str
    text: str
    goal: object  # anything with met(molecule, view) -> bool, see goals.py


# The same tasks, in the same order, for both conditions. Placeholder set until the T8
# study plan fixes the final tasks; the first two come from the project proposal.
TASKS = [
    StudyTask("caffeine", "Rotate the molecule until a red oxygen atom points straight at you.", FaceAtom("O")),
    StudyTask("caffeine", "Zoom in until the six-sided ring fills half of the view.", RingFillsView(6, 0.5)),
    StudyTask("aspirin", "Turn the molecule so the six-sided ring is seen edge-on, as a flat line.", RingEdgeOn(6)),
    StudyTask("adenine", "Find the blue nitrogen with two white hydrogens and turn it toward you.",
              FaceAtom("N", hydrogens=2)),
    StudyTask("benzene", "Zoom out until the molecule is smaller than a quarter of the view.", MoleculeSmall(0.25)),
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
        self.outcome = ""   # "done", "timeout" or "skipped" for the last finished task
        self._started = 0.0
        self._met_since: float | None = None
        logger.log("participant", participant)
        logger.log("condition", condition)

    @property
    def current(self) -> StudyTask | None:
        return self.tasks[self.task - 1] if 0 < self.task <= len(self.tasks) else None

    @property
    def finished(self) -> bool:
        return self.task >= len(self.tasks) and not self.running

    @property
    def goal_met(self) -> bool:
        return self._met_since is not None

    def start_task(self, now: float | None = None) -> StudyTask | None:
        """Start the next task and return it, or None when all tasks are done."""
        if self.running:
            self.skip_task()
        if self.task >= len(self.tasks):
            return None
        self.task += 1
        self.running = True
        self._started = time.monotonic() if now is None else now
        self._met_since = None
        self.logger.log("task_start", str(self.task))
        return self.current

    def update(self, goal_met: bool, now: float | None = None) -> str:
        """Called every frame with whether the goal is met. Returns "done", "timeout" or ""."""
        if not self.running:
            return ""
        now = time.monotonic() if now is None else now
        if not goal_met:
            self._met_since = None
        elif self._met_since is None:
            self._met_since = now
        if self._met_since is not None and now - self._met_since >= GOAL_HOLD_S:
            return self._finish("task_end", "done")
        if now - self._started >= TIME_LIMIT_S:
            return self._finish("task_timeout", "timeout")
        return ""

    def skip_task(self) -> None:
        if self.running:
            self._finish("task_abandoned", "skipped")

    def _finish(self, event: str, outcome: str) -> str:
        self.running = False
        self._met_since = None
        self.outcome = outcome
        self.logger.log(event, str(self.task))
        return outcome

    def false_trigger(self) -> None:
        self.logger.log("false_trigger", str(self.task))

    def status_text(self) -> str:
        """Experimenter's line: who, which condition, what to press next."""
        total = len(self.tasks)
        if self.task == 0:
            state = "press T to start task 1"
        elif self.running:
            state = f"task {self.task} of {total} running, Space to skip"
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
            hold = "\n✓ Goal reached, hold it there..." if self.goal_met else ""
            return f"Task {self.task} of {len(self.tasks)}\n{self.current.text}{hold}"
        if self.finished:
            return "All tasks done. Thank you!"
        result = {"done": "Well done!", "timeout": "Time is up.", "skipped": "Skipped."}.get(self.outcome, "")
        return f"{result} Wait for the next task."
