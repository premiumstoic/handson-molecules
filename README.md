# HandsOn Molecules

Explore a 3D molecule with hand gestures from an ordinary webcam.
Python + MediaPipe Hand Landmarker + PyVista (Qt window) + RDKit.

## Setup

With conda (recommended):

```bash
conda env create -f environment.yml
conda activate handson
python scripts/download_model.py
```

Or with venv (Python 3.10–3.12):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_model.py
```

`download_model.py` saves `models/hand_landmarker.task` (about 8 MB) from Google's
MediaPipe model storage. It is git-ignored, so each person runs it once.

## Run

```bash
python -m handson                      # caffeine
python -m handson --molecule aspirin
python -m handson --camera 1           # if the wrong camera opens
```

The app still opens without a camera or model; the status panel says why tracking is off,
and the keyboard controls work.

**macOS camera permission:** the first run asks for camera access for your terminal or
editor (Terminal, iTerm, VS Code…). If you denied it, enable it in
System Settings → Privacy & Security → Camera, then restart that app.

## Tests

```bash
python -m pytest
```

## Project layout

```text
handson/
  __main__.py    command-line entry point
  app.py         main window: 3D view, webcam preview, status panel, keyboard shortcuts
  molecule.py    RDKit SMILES -> 3D atoms/bonds -> PyVista ball-and-stick model
  tracking.py    webcam + MediaPipe on a background thread (Qt/VTK stay on the main thread)
  gestures.py    landmarks -> hand shape               <- TODO
  controller.py  hand shape + movement -> camera       <- TODO (camera actions already work)
  logger.py      CSV event log per session, saved in logs/
scripts/download_model.py
tests/
```

How a frame flows:

```text
webcam -> tracking.py (thread) -> TrackingFrame -> app.py timer (30 Hz)
       -> gestures.classify() -> controller.update() -> PyVista camera
                                                      -> status panel + logs/
```

## What works now

- Caffeine or aspirin rendered as a ball-and-stick model (CPK colours)
- Webcam preview with the tracked hand skeleton drawn on it
- Status panel: hand detected / tracking lost, gesture, action, camera fps
- Keyboard controls for testing: arrow keys rotate, `+`/`-` zoom, `R` resets
- CSV log of hand, gesture and action events in `logs/`

## Next steps (in order)

1. **Everyone:** set up, run the app, and confirm your hand skeleton appears in the preview.
2. **`gestures.classify`:** detect FIST, PINCH and OPEN. Watch the "Gesture" line in the
   status panel while you test. Add unit tests with landmark arrays you record.
3. **`controller.update`:** rotate while a fist is held, zoom while pinching, reset after an
   open palm is held ~1 s. Anything else does nothing (the clutch).
4. **Smoothing:** add a One Euro filter to the landmarks before computing movement.
5. **Tuning:** adjust sensitivities with people who haven't used the app.

## Gesture set

| Gesture | Hand shape | Action |
|---|---|---|
| Rotate | Fist, then move the hand | Horizontal movement turns left/right, vertical tilts up/down |
| Zoom | Thumb and index pinched, then spread or close them | Spread = closer, close = farther |
| Reset | Open palm held about 1 second | Return to the starting view |
| (none) | Any other shape, or no hand | Nothing moves |

## Logs and privacy

Each run writes `logs/session-<date>-<time>.csv` with timestamps of hand, gesture and
action events. No camera images are saved. `logs/` is git-ignored; share study logs
deliberately and without participant names.
