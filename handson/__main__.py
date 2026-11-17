"""Run with: python -m handson [--molecule caffeine] [--camera 0]

User study session:
    python -m handson --participant new        # next ID from the study backend, its first condition
    python -m handson --participant P07        # P07's remaining condition
    python -m handson --participant P07 --condition mouse   # a specific condition
"""

import argparse
import os
import sys
from pathlib import Path

from . import molecule

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore a 3D molecule with hand gestures.")
    parser.add_argument("--molecule", default="caffeine", choices=sorted(molecule.MOLECULES))
    parser.add_argument("--camera", type=int, default=0, help="webcam index (try 1 if 0 is wrong)")
    parser.add_argument("--model", type=Path, default=ROOT / "models" / "hand_landmarker.task")
    parser.add_argument("--log-dir", type=Path, default=ROOT / "logs")
    parser.add_argument("--participant",
                        help='turns on study mode: "new" for the next ID, or an existing ID such as P07')
    parser.add_argument("--condition", choices=["gesture", "mouse"],
                        help="study condition; by default the participant's next one in their order")
    args = parser.parse_args()

    link = None
    participant, condition = args.participant, args.condition
    if participant:
        from . import remote

        config = remote.ServerConfig.load(ROOT, os.environ)
        client = remote.Client(config) if config.enabled else None
        registry = remote.Registry(args.log_dir / "participants.json")
        participant, condition, order, note = remote.resolve(participant, condition, config, registry, client)
        uploader = remote.Uploader(args.log_dir / "outbox", client)
        link = remote.StudyLink(remote.session_info(ROOT, config.laptop), order, registry, uploader, note)
        print(f"Participant {participant}, {condition} condition (order: {' then '.join(order)})")
        if note:
            print(note)
        if not config.enabled:
            print("No study backend set up (study_server.json): results stay in logs/ only.")

    from PySide6.QtWidgets import QApplication

    from .app import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(args.molecule, args.model, args.camera, args.log_dir,
                        participant=participant, condition=condition or "gesture", link=link)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
