"""Participant IDs, condition order and the upload outbox, with a fake backend (no network)."""

import json
import socket

from handson import remote


class FakeClient:
    def __init__(self, offline=False):
        self.offline = offline
        self.calls = []
        self.next_number = 7

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if self.offline:
            raise OSError("no network")
        if path == "/api/participants":
            number, self.next_number = self.next_number, self.next_number + 1
            return {"id": f"P{number:02d}", "order": remote.condition_order(number)}
        if path.startswith("/api/participants?id="):
            return {"order": ["mouse", "gesture"]}
        return {"ok": True}


CONFIG = remote.ServerConfig("https://example.test", "key", "laptop-a")


def test_odd_ids_start_with_gestures():
    assert remote.condition_order(7) == ["gesture", "mouse"]
    assert remote.condition_order(8) == ["mouse", "gesture"]


def test_new_participant_gets_an_id_and_their_first_condition(tmp_path):
    registry = remote.Registry(tmp_path / "participants.json")
    participant, condition, order, note = remote.resolve("new", None, CONFIG, registry, FakeClient())
    assert (participant, condition, order, note) == ("P07", "gesture", ["gesture", "mouse"], "")


def test_second_run_picks_the_condition_still_to_do(tmp_path):
    registry = remote.Registry(tmp_path / "participants.json")
    remote.resolve("new", None, CONFIG, registry, FakeClient())
    registry.mark_done("P07", "gesture")
    reopened = remote.Registry(tmp_path / "participants.json")   # e.g. the next day
    assert remote.resolve("P07", None, CONFIG, reopened, FakeClient())[1] == "mouse"


def test_offline_gives_a_local_id_that_still_alternates(tmp_path):
    registry = remote.Registry(tmp_path / "participants.json")
    first = remote.resolve("new", None, CONFIG, registry, FakeClient(offline=True))
    second = remote.resolve("new", None, CONFIG, registry, None)
    assert first[0] == "laptop-a-L1" and first[1] == "gesture" and "Offline ID" in first[3]
    assert second[0] == "laptop-a-L2" and second[1] == "mouse"


def test_known_id_from_another_laptop_asks_the_backend_for_its_order(tmp_path):
    registry = remote.Registry(tmp_path / "participants.json")
    assert remote.resolve("P12", None, CONFIG, registry, FakeClient())[2] == ["mouse", "gesture"]
    # Offline and unknown: the order follows from the number.
    assert remote.resolve("P13", None, CONFIG, remote.Registry(tmp_path / "other.json"),
                          FakeClient(offline=True))[1] == "gesture"


def test_laptop_label_is_cleaned_and_env_wins(tmp_path):
    (tmp_path / "study_server.json").write_text(json.dumps({"url": "https://a.test/", "upload_key": "k",
                                                             "laptop": "Ahmet's MacBook!"}))
    config = remote.ServerConfig.load(tmp_path, {})
    assert config.url == "https://a.test" and config.laptop == "ahmet-s-macbook" and config.enabled
    assert remote.ServerConfig.load(tmp_path, {"HANDSON_LAPTOP": "laptop-b"}).laptop == "laptop-b"
    assert not remote.ServerConfig.load(tmp_path / "missing", {}).enabled


def test_session_info_has_no_host_or_user_name(tmp_path):
    info = remote.session_info(tmp_path, "laptop-a")
    assert {"session_id", "started", "laptop", "app_version", "os", "python"} <= info.keys()
    text = json.dumps(info).lower()
    assert socket.gethostname().lower() not in text


def test_outbox_keeps_records_until_they_are_sent(tmp_path):
    client = FakeClient(offline=True)
    uploader = remote.Uploader(tmp_path / "outbox", None)       # no thread; we send by hand
    uploader.client = client
    record = {"participant": "P07", "condition": "gesture", "session_id": "abc12345", "tasks": []}
    uploader.submit(record)
    uploader.submit({**record, "tasks": [{"task": 1}]})           # same session: replaces the file
    assert uploader.send_pending() == 0 and len(list((tmp_path / "outbox").glob("*.json"))) == 1
    client.offline = False
    assert uploader.send_pending() == 1
    assert not list((tmp_path / "outbox").glob("*.json"))
    assert client.calls[-1][2]["tasks"] == [{"task": 1}]
