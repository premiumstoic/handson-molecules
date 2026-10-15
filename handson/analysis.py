"""Turn user study session logs into task times and false-trigger counts (T11).

Only sessions started with --participant are used. Each task runs from its
task_start to its task_end row; abandoned tasks are counted but have no time.
"""

import csv
import statistics
from dataclasses import dataclass, field
from pathlib import Path

GESTURE_ACTIONS = ("rotate", "zoom", "reset")


@dataclass
class TaskResult:
    participant: str
    condition: str
    task: int
    seconds: float | None = None  # None if the task was abandoned or never ended
    false_triggers: int = 0
    actions: dict[str, int] = field(default_factory=lambda: dict.fromkeys(GESTURE_ACTIONS, 0))

    @property
    def completed(self) -> bool:
        return self.seconds is not None


def read_session(path: Path) -> list[TaskResult]:
    """One study session log -> one result per task. Non-study sessions give []."""
    with path.open(newline="") as file:
        rows = [(float(row["time_s"]), row["event"], row["detail"]) for row in csv.DictReader(file)]
    info = {event: detail for _t, event, detail in rows if event in ("participant", "condition")}
    if "participant" not in info:
        return []

    results: dict[int, TaskResult] = {}
    current: TaskResult | None = None
    started = 0.0
    for t, event, detail in rows:
        if event == "task_start":
            current = results.setdefault(int(detail), TaskResult(info["participant"], info["condition"], int(detail)))
            started = t
        elif event == "task_end" and current is not None:
            current.seconds = round(t - started, 3)
            current = None
        elif event == "task_abandoned":
            current = None
        elif event == "false_trigger" and detail and int(detail) in results:
            results[int(detail)].false_triggers += 1  # by task number, so a late F still counts
        elif event == "action" and current is not None and detail in GESTURE_ACTIONS:
            current.actions[detail] += 1
    return list(results.values())


def read_logs(directory: Path) -> list[TaskResult]:
    results = []
    for path in sorted(directory.glob("session-*.csv")):
        results.extend(read_session(path))
    return results


def summarize(results: list[TaskResult]) -> dict[str, dict[str, float]]:
    """Per condition: tasks done, abandoned, mean and median seconds, false triggers per completed task."""
    summary = {}
    for condition in sorted({r.condition for r in results}):
        rows = [r for r in results if r.condition == condition]
        times = [r.seconds for r in rows if r.completed]
        summary[condition] = {
            "participants": len({r.participant for r in rows}),
            "tasks_completed": len(times),
            "tasks_abandoned": sum(not r.completed for r in rows),
            "mean_s": round(statistics.mean(times), 2) if times else float("nan"),
            "median_s": round(statistics.median(times), 2) if times else float("nan"),
            "false_triggers_per_task": round(sum(r.false_triggers for r in rows) / len(times), 2) if times
            else float("nan"),
        }
    return summary


def write_task_csv(results: list[TaskResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["participant", "condition", "task", "seconds", "completed", "false_triggers",
                         *GESTURE_ACTIONS])
        for r in sorted(results, key=lambda r: (r.participant, r.condition, r.task)):
            writer.writerow([r.participant, r.condition, r.task, "" if r.seconds is None else r.seconds,
                             r.completed, r.false_triggers, *(r.actions[a] for a in GESTURE_ACTIONS)])


def markdown_report(results: list[TaskResult]) -> str:
    """Tables for the final report: per condition, then mean seconds per task and condition."""
    summary = summarize(results)
    lines = ["| Condition | Participants | Tasks done | Abandoned | Mean (s) | Median (s) | False triggers / task |",
             "|---|---|---|---|---|---|---|"]
    for condition, s in summary.items():
        lines.append(f"| {condition} | {s['participants']} | {s['tasks_completed']} | {s['tasks_abandoned']} | "
                     f"{s['mean_s']} | {s['median_s']} | {s['false_triggers_per_task']} |")

    conditions = list(summary)
    lines += ["", "| Task | " + " | ".join(f"{c} mean (s)" for c in conditions) + " |",
              "|---|" + "---|" * len(conditions)]
    for task in sorted({r.task for r in results}):
        cells = []
        for condition in conditions:
            times = [r.seconds for r in results if r.task == task and r.condition == condition and r.completed]
            cells.append(f"{statistics.mean(times):.2f}" if times else "-")
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
