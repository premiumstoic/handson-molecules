"""Study backend: participant IDs, condition order, and uploading results.

The backend (backend/ in this repo, deployed on Vercel) hands out IDs P01, P02, ... so that
laptops never give out the same one, and stores each session's results for the admin page.
Odd IDs do gestures first, even IDs the mouse first (counterbalancing).

Without a backend, or offline, the app still works: IDs come from a local counter
(laptop-a-L1, laptop-a-L2, ...), and results wait in logs/outbox/ until they can be sent.
The CSV log in logs/ stays the source of truth either way.

Set the backend in study_server.json at the repository root (git-ignored):
    {"url": "https://....vercel.app", "upload_key": "...", "laptop": "laptop-a"}
or with HANDSON_SERVER_URL, HANDSON_UPLOAD_KEY and HANDSON_LAPTOP.
"""

import json
import platform
import re
import subprocess
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CONDITIONS = ("gesture", "mouse")
TIMEOUT_S = 5.0
RETRY_EVERY_S = 30.0


@dataclass(frozen=True)
class ServerConfig:
    url: str = ""
    upload_key: str = ""
    laptop: str = "laptop"

    @classmethod
    def load(cls, root: Path, environ: dict) -> "ServerConfig":
        values = {}
        path = root / "study_server.json"
        if path.exists():
            values = json.loads(path.read_text())
        url = environ.get("HANDSON_SERVER_URL", values.get("url", ""))
        key = environ.get("HANDSON_UPLOAD_KEY", values.get("upload_key", ""))
        laptop = environ.get("HANDSON_LAPTOP", values.get("laptop", "laptop"))
        # Laptop labels go into local IDs, so keep them to lowercase letters, digits and dashes.
        laptop = re.sub(r"[^a-z0-9-]+", "-", laptop.lower()).strip("-")[:24] or "laptop"
        return cls(url.rstrip("/"), key, laptop)

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.upload_key)


def condition_order(number: int) -> list[str]:
    """Odd participants start with gestures, even ones with the mouse."""
    return ["gesture", "mouse"] if number % 2 == 1 else ["mouse", "gesture"]


def id_number(participant: str) -> int | None:
    found = re.search(r"(\d+)$", participant)
    return int(found.group(1)) if found else None


class Client:
    """Talks to the backend. Every call can raise OSError when offline."""

    def __init__(self, config: ServerConfig):
        self.config = config

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.config.url}{path}", data=data, method=method, headers={
            "Authorization": f"Bearer {self.config.upload_key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:200]
            raise OSError(f"{error.code} from the study backend: {detail}") from error


class Registry:
    """This laptop's participants (logs/participants.json): their order and finished conditions."""

    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {"local_count": 0, "participants": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))

    def remember(self, participant: str, order: list[str]) -> None:
        entry = self.data["participants"].setdefault(participant, {"order": order, "done": []})
        entry["order"] = order
        self._save()

    def order(self, participant: str) -> list[str] | None:
        entry = self.data["participants"].get(participant)
        return entry["order"] if entry else None

    def mark_done(self, participant: str, condition: str) -> None:
        entry = self.data["participants"].setdefault(participant, {"order": list(CONDITIONS), "done": []})
        if condition not in entry["done"]:
            entry["done"].append(condition)
        self._save()

    def remaining(self, participant: str) -> list[str]:
        entry = self.data["participants"].get(participant)
        if not entry:
            return []
        return [c for c in entry["order"] if c not in entry["done"]]

    def new_local_id(self, laptop: str) -> tuple[str, list[str]]:
        self.data["local_count"] += 1
        number = self.data["local_count"]
        participant = f"{laptop}-L{number}"
        self.remember(participant, condition_order(number))
        return participant, condition_order(number)


def resolve(participant: str, condition: str | None, config: ServerConfig, registry: Registry,
            client: Client | None) -> tuple[str, str, list[str], str]:
    """Work out who and which condition this session is.

    participant is "new" (get the next ID) or an existing ID. condition overrides the order.
    Returns (participant, condition, order, note), where note explains any offline fallback.
    """
    note = ""
    if participant == "new":
        try:
            if client is None:
                raise OSError("no study backend set up")
            record = client.request("POST", "/api/participants", {"laptop": config.laptop})
            participant, order = record["id"], record["order"]
            registry.remember(participant, order)
        except (OSError, KeyError, ValueError) as error:
            participant, order = registry.new_local_id(config.laptop)
            note = f"Offline ID {participant} ({error})"
    else:
        order = registry.order(participant)
        if order is None and client is not None:
            try:
                order = client.request("GET", f"/api/participants?id={participant}")["order"]
            except (OSError, KeyError, ValueError):
                order = None
        if order is None:
            number = id_number(participant)
            order = condition_order(number) if number is not None else list(CONDITIONS)
        registry.remember(participant, order)
    if condition is None:
        left = registry.remaining(participant)
        condition = left[0] if left else order[0]
    return participant, condition, order, note


def app_version(root: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=2).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def session_info(root: Path, laptop: str) -> dict:
    """What we record about the setup. Deliberately no host name, user name or hardware IDs."""
    return {
        "session_id": uuid.uuid4().hex[:16],
        "started": datetime.now().astimezone().isoformat(timespec="seconds"),
        "laptop": laptop,
        "app_version": app_version(root),
        "os": f"{platform.system()} {platform.mac_ver()[0] or platform.release()} ({platform.machine()})",
        "python": platform.python_version(),
    }


@dataclass
class StudyLink:
    """Everything the study window needs from this module for one session."""
    info: dict          # from session_info()
    order: list[str]
    registry: Registry
    uploader: "Uploader"
    note: str = ""      # shown to the experimenter, e.g. when the ID is an offline one

    def record(self, participant: str, condition: str, results: list, tasks: list, finished: bool,
               camera: dict | None, screen: dict | None) -> dict:
        return {
            **self.info, "participant": participant, "condition": condition, "finished": finished,
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds") if finished else "",
            "camera": camera, "screen": screen,
            "tasks": [{"task": r.task, "molecule": tasks[r.task - 1].molecule, "outcome": r.outcome,
                       "seconds": round(r.seconds, 3), "false_triggers": r.false_triggers} for r in results],
        }


class Uploader:
    """Sends session records in the background. Each record is first written to the outbox
    folder, so nothing is lost if the app closes or the network is down; it is retried later."""

    def __init__(self, outbox: Path, client: Client | None):
        self.outbox = outbox
        self.client = client
        self._wake = threading.Event()
        self._stop = threading.Event()
        self.last_error = ""
        self._thread = threading.Thread(target=self._run, name="study-upload", daemon=True)
        if client is not None:
            self._thread.start()

    def submit(self, record: dict) -> None:
        self.outbox.mkdir(parents=True, exist_ok=True)
        name = f"{record['participant']}-{record['condition']}-{record['session_id']}.json"
        tmp = self.outbox / f".{name}.tmp"
        tmp.write_text(json.dumps(record))
        tmp.replace(self.outbox / name)  # whole file or nothing, even if the app is killed
        self._wake.set()

    def send_pending(self) -> int:
        """Try to send everything in the outbox; returns how many were sent."""
        if self.client is None or not self.outbox.exists():
            return 0
        sent = 0
        for path in sorted(self.outbox.glob("*.json")):
            try:
                self.client.request("POST", "/api/sessions", json.loads(path.read_text()))
            except (OSError, ValueError) as error:
                self.last_error = str(error)
                break
            path.unlink(missing_ok=True)
            sent += 1
        return sent

    def _run(self) -> None:
        while True:
            self.send_pending()  # also once more after close(), for the record submitted last
            if self._stop.is_set():
                return
            self._wake.wait(RETRY_EVERY_S)
            self._wake.clear()

    def close(self, wait_s: float = 3.0) -> None:
        """Give the last upload a moment; whatever is left is sent next time the app runs."""
        self._stop.set()
        self._wake.set()
        if self._thread.is_alive():
            self._thread.join(wait_s)
