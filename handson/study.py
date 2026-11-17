"""User study session: participant, condition, and experimenter task markers.

Each task has a goal checked from the 3D view (goals.py). A task ends by itself
once its goal has been held for GOAL_HOLD_S, or fails after TIME_LIMIT_S.

The experimenter presses keys while the participant works (see README):
    T      start the next task: it is shown on screen and its molecule is loaded
    Space  skip the current task (logged as abandoned)
    F      the participant triggered something they did not mean to (false trigger)
Every marker goes into the session log, which scripts/analyze_logs.py reads.
The app shows intro_pages() before the first task and the results after the last one.
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


@dataclass(frozen=True)
class TaskResult:
    task: int             # 1-based, as shown to the participant
    outcome: str          # "done", "timeout" or "skipped"
    seconds: float        # from task start to its end (for "done", including the hold)
    false_triggers: int


@dataclass(frozen=True)
class IntroPage:
    title: str
    text: str             # paragraphs separated by a blank line
    image: str = ""       # file name in assets/, or none
    try_gesture: str = "" # HandShape value the participant can practise on this page


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
        self._finished: list[tuple[int, str, float]] = []  # (task, outcome, seconds)
        self._started = 0.0
        self._met_since: float | None = None
        self._false_triggers: dict[int, int] = {}
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

    @property
    def results(self) -> list[TaskResult]:
        """Finished tasks so far. False triggers are counted at read time, since the experimenter
        may press F just after a task has ended."""
        return [TaskResult(task, outcome, seconds, self._false_triggers.get(task, 0))
                for task, outcome, seconds in self._finished]

    def start_task(self, now: float | None = None) -> StudyTask | None:
        """Start the next task and return it, or None when all tasks are done."""
        if self.running:
            self.skip_task(now)
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
            return self._finish("task_end", "done", now)
        if now - self._started >= TIME_LIMIT_S:
            return self._finish("task_timeout", "timeout", now)
        return ""

    def skip_task(self, now: float | None = None) -> None:
        if self.running:
            self._finish("task_abandoned", "skipped", now)

    def _finish(self, event: str, outcome: str, now: float | None) -> str:
        now = time.monotonic() if now is None else now
        self.running = False
        self._met_since = None
        self.outcome = outcome
        self._finished.append((self.task, outcome, now - self._started))
        self.logger.log(event, str(self.task))
        return outcome

    def false_trigger(self) -> None:
        self._false_triggers[self.task] = self._false_triggers.get(self.task, 0) + 1
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

    def intro_pages(self) -> list[IntroPage]:
        """Step-by-step intro shown in place of the 3D view before the first task:
        the app, then each control, then the tasks."""
        gesture = self.condition == "gesture"
        about = IntroPage(
            "Welcome to HandsOn Molecules",
            "This app lets you explore molecules in 3D: you can turn one around, look closer, "
            "and see how its atoms sit in space.\n\n"
            + ("You control it with your hand in front of the camera, no mouse or keyboard. "
               "The camera only follows your hand; no pictures or video are saved."
               if gesture else
               "In this session you control it with the mouse.")
            + "\n\nThe next pages show you how, one step at a time.",
            "intro_app.png")
        if gesture:
            controls = [
                IntroPage(
                    "Rotate: make a fist and move it",
                    "Make a fist and move your hand. The molecule turns with it: left and right "
                    "turns it around, up and down tilts it.\n\n"
                    "To stop, just open or relax your hand. Any other hand shape moves nothing, "
                    "so you can talk and point freely.",
                    "gesture_fist.png", "fist"),
                IntroPage(
                    "Zoom: pinch and move up or down",
                    "Touch your thumb and index finger together, like holding a small coin. "
                    "Keep pinching and move your hand up to come closer, or down to move away, "
                    "like a slider.",
                    "gesture_pinch.png", "pinch"),
                IntroPage(
                    "Reset: hold an open palm",
                    "Show an open palm with your fingers spread and hold it still. A bar on the "
                    f"right fills up, and after about {GOAL_HOLD_S:g} second the molecule goes back "
                    "to how it looked at the start.\n\n"
                    "Use it whenever you feel lost.",
                    "gesture_palm.png", "open palm"),
            ]
        else:
            controls = [IntroPage(
                "Using the mouse",
                "Drag with the mouse to turn the molecule. Scroll to zoom in and out.",
                "")]
        tasks = IntroPage(
            f"Your {len(self.tasks)} tasks",
            "Each task asks you to bring the molecule into a certain view, for example to turn "
            "an atom toward you. It appears in the box on the right, one at a time.\n\n"
            f"When you reach the goal, hold still: the task ends by itself after {GOAL_HOLD_S:g} "
            f"second. You have up to {TIME_LIMIT_S:g} seconds for each one.\n\n"
            "We are testing the app, not you, so there are no wrong answers. "
            "Please say out loud what you are thinking while you work.",
            "intro_tasks.png")
        return [about, *controls, tasks]

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
