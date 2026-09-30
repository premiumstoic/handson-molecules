"""CSV event log for the user study (one file per app session)."""

import csv
import time
from datetime import datetime
from pathlib import Path


class EventLogger:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"session-{datetime.now():%Y%m%d-%H%M%S}.csv"
        self._file = self.path.open("w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["time_s", "event", "detail"])
        self._start = time.monotonic()

    def log(self, event: str, detail: str = "") -> None:
        self._writer.writerow([f"{time.monotonic() - self._start:.3f}", event, detail])
        self._file.flush()

    def close(self) -> None:
        self._file.close()
