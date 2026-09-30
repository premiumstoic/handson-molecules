"""Run with: python -m handson [--molecule caffeine] [--camera 0]"""

import argparse
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
    args = parser.parse_args()

    from PySide6.QtWidgets import QApplication

    from .app import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(args.molecule, args.model, args.camera, args.log_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
