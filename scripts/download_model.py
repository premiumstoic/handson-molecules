"""Download the MediaPipe Hand Landmarker model into models/."""

import urllib.request
from pathlib import Path

URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
       "hand_landmarker/float16/latest/hand_landmarker.task")
TARGET = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"


def main() -> None:
    if TARGET.exists():
        print(f"Model already present: {TARGET}")
        return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL}")
    urllib.request.urlretrieve(URL, TARGET)
    print(f"Saved {TARGET} ({TARGET.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
