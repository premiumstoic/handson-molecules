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
python -m handson                      # caffeine (N / P switches molecule)
python -m handson --molecule aspirin
python -m handson --camera 1           # if the wrong camera opens
```

The app still opens without a camera or model; the status panel says why tracking is off,
and the keyboard controls work.

**macOS camera permission:** the first run asks for camera access for your terminal or
editor (Terminal, iTerm, VS Code…). If you denied it, enable it in
System Settings → Privacy & Security → Camera, then restart that app.

## User study sessions

```bash
python -m handson --participant P01 --condition gesture   # gestures only (mouse disabled)
python -m handson --participant P01 --condition mouse     # mouse only (camera off)
```

The log file name includes the participant and condition, e.g.
`logs/session-20261110-140512-P01-gesture.csv`. Use IDs, never names.

The app has four built-in tasks (`TASKS` in `handson/study.py`, same order in both
conditions). The participant reads the current task in the box under the camera preview; the
yellow line above it tells the experimenter what to press next.

The experimenter presses these keys while the participant works:

| Key | Logs | When |
|---|---|---|
| `T` | `task_start` | Shows the next task, loads its molecule in the starting view, and starts the clock |
| `Space` | `task_end` | The participant has finished the task |
| `F` | `false_trigger` | Something moved that the participant did not mean to move |

Pressing `T` again before `Space` logs the unfinished task as `task_abandoned`.

After the sessions, summarize all study logs:

```bash
python scripts/analyze_logs.py            # reads logs/, writes results/tasks.csv and results/summary.md
```

`summary.md` has the tables for the report: tasks done, mean and median time, and false
triggers per task for each condition, then mean time per task. `results/` is git-ignored
like `logs/`.

## Tests

```bash
python -m pytest
```

## Project layout

```text
handson/
  __main__.py    command-line entry point
  app.py         main window: 3D view, webcam preview, status panel, keyboard shortcuts
  status.py      what the status card shows for each state (no Qt, unit-tested)
  status_panel.py  status card and gesture legend widgets (Ali's T4 design)
  assets/        gesture artwork from Ali's design
  molecule.py    RDKit SMILES -> 3D atoms/bonds -> PyVista ball-and-stick model
  tracking.py    webcam + MediaPipe on a background thread (Qt/VTK stay on the main thread)
  filters.py     One Euro filter that smooths the landmarks
  gestures.py    landmarks -> hand shape, hand position, stable gesture
  controller.py  hand shape + movement -> camera (rotate, zoom, reset, clutch)
  logger.py      CSV event log per session, saved in logs/
  study.py       study session: participant, condition, task markers
scripts/download_model.py
scripts/analyze_logs.py   study logs -> task times and false triggers (logic in handson/analysis.py)
tests/
```

How a frame flows:

```text
webcam -> tracking.py (thread) -> TrackingFrame -> app.py timer (30 Hz)
       -> gestures.classify() -> controller.update() -> PyVista camera
                                                      -> status panel + logs/
```

## What works now

- Six molecules as ball-and-stick models (CPK colours): caffeine, aspirin, adenine, ethanol,
  benzene, glucose; switch with the drop-down or `N` / `P`
- Webcam preview with the tracked hand skeleton drawn on it
- Gesture detection: fist, pinch and open palm, stable over 5 of 7 frames; pinch stays
  active if the fingers loosen while zooming
- Landmark smoothing (One Euro filter) and fast release: the molecule stops as soon as the
  hand changes shape
- Gesture control: fist + move rotates, pinch + move up/down zooms, open palm held 1 s resets;
  any other shape or no hand moves nothing (the clutch)
- Status card: waiting, hand detected (gesture and hint), tracking lost, camera off; a bar
  fills while an open palm is held to reset
- Keyboard controls for testing: arrow keys rotate, `+`/`-` zoom, `R` resets
- CSV log of hand, gesture and action events in `logs/`

## Next steps (in order)

1. **Everyone:** set up, run the app, and confirm your hand skeleton appears in the preview.
2. **Tuning:** adjust the thresholds in `gestures.THRESHOLDS` and the constants at the top
   of `controller.py` and `filters.py` with people who haven't used the app. Add unit tests with
   landmark arrays you record.

## Gesture set

| Gesture | Hand shape | Action |
|---|---|---|
| Rotate | Fist, then move the hand | Horizontal movement turns left/right, vertical tilts up/down |
| Zoom | Thumb and index pinched, then move the hand up or down (like a slider) | Up = closer, down = farther |
| Reset | Open palm held about 1 second | Return to the starting view |
| (none) | Any other shape, or no hand | Nothing moves |

## Logs and privacy

Each run writes `logs/session-<date>-<time>.csv` with timestamps of hand, gesture and
action events. No camera images are saved. `logs/` is git-ignored; share study logs
deliberately and without participant names.
