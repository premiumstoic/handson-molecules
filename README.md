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
python -m handson --participant new        # a new participant: next ID and their first condition
python -m handson --participant P07        # P07's other condition (the app remembers which is left)
python -m handson --participant P07 --condition mouse   # force a condition, e.g. to redo a session
```

Each participant does both conditions. Odd IDs do gestures first and even IDs the mouse first,
so learning effects even out (counterbalancing). The terminal prints the ID and condition, and
the results screen says which condition is next.

The log file name includes the participant and condition, e.g.
`logs/session-20261110-140512-P01-gesture.csv`. Use IDs, never names; keep the list of who got
which ID on paper, apart from the data.

The app has five built-in tasks (`TASKS` in `handson/study.py`, same order in both
conditions). The participant reads the current task in the box under the camera preview; the
yellow line above it tells the experimenter what to press next.

Before the first task, a step-by-step intro in place of the 3D view explains the app, then each
gesture on its own page (the participant can try it and the page shows when the camera sees it),
then the tasks. The mouse condition gets one mouse page instead of the gestures. Back / Next or
the left and right arrow keys move between steps, and `T` starts task 1 from any step. The
illustrations in `handson/assets/` (`intro_*.png`, `gesture_*.png`) were made with Codex image
generation. After the last task, the same area shows each task's result, time and false
triggers, and the log file name.

Each task has a goal the app checks from the 3D view (`handson/goals.py`), for example "a red
oxygen within 20° of pointing at the viewer" or "the molecule smaller than a quarter of the
view". When the goal is reached the box shows "Goal reached, hold it there"; once it has been
held for 1 s the task ends by itself (`task_end`). After 90 s without success it is logged as
`task_timeout`.

The experimenter presses these keys while the participant works:

| Key | Logs | When |
|---|---|---|
| `T` | `task_start` | Shows the next task, loads its molecule in the starting view, and starts the clock |
| `Space` | `task_abandoned` | Skip the task (e.g. the participant is stuck or something went wrong) |
| `F` | `false_trigger` | Something moved that the participant did not mean to move |

After the sessions, summarize all study logs:

```bash
python scripts/analyze_logs.py            # reads logs/, writes results/tasks.csv and results/summary.md
```

`summary.md` has the tables for the report: tasks done, timed out and skipped, mean and
median time, and false triggers per task for each condition, then mean time per task. `results/` is git-ignored
like `logs/`.

### Study backend (IDs and results from all laptops in one place)

`backend/` is a small Vercel project. It hands out participant IDs (P01, P02, ...) so two
laptops never use the same one, and collects every session's results on an admin page with
per-task means for gestures vs. mouse, per-participant progress and a CSV download.

What is sent: participant ID, condition, task results (outcome, seconds, false triggers),
start and end time, a laptop label you choose, app version (git commit), OS and Python version,
camera size and frame rate, and screen size. Nothing else: no names, host or user names, or
camera images. Tell participants on the consent form that anonymous results are stored online.

**Deploy once** (from `backend/`, with your Vercel account):
1. `npx vercel link`, then `npx vercel deploy --prod`.
2. In the Vercel project: Storage → create a **private** Blob store and connect it to the project.
3. Settings → Environment Variables: `UPLOAD_KEY` (shared with the study laptops) and
   `ADMIN_KEY` (only for the team, for the results page). Redeploy.
4. Open the deployment URL and enter the admin key to see results.

**On each study laptop**, create `study_server.json` in the repository root (git-ignored):

```json
{"url": "https://<your-project>.vercel.app", "upload_key": "<UPLOAD_KEY>", "laptop": "laptop-a"}
```

Give every laptop its own label. Without this file, or when offline, everything still works:
IDs come from a local counter (`laptop-a-L1`, `laptop-a-L2`, ...; odd/even alternation still
applies), and results wait in `logs/outbox/` and are sent the next time the app runs online.
The CSV logs in `logs/` are always kept, and `logs/participants.json` remembers each local
participant's order and finished conditions.

**Try it locally** without deploying: `cd backend && npm install && node dev-server.js`
(in-memory, keys `dev-upload` / `dev-admin`), then run the app with
`HANDSON_SERVER_URL=http://localhost:8787 HANDSON_UPLOAD_KEY=dev-upload` and open
http://localhost:8787. Backend tests: `cd backend && npm test`.

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
  assets/        gesture artwork from Ali's design, intro illustrations (Codex)
  intro_panel.py step-by-step intro shown before the first study task
  health.py      once-a-second health line in the log, to catch freezes
  remote.py      study backend: participant IDs, condition order, result uploads with an outbox
  molecule.py    RDKit SMILES -> 3D atoms/bonds -> PyVista ball-and-stick model
  tracking.py    webcam + MediaPipe on a background thread (Qt/VTK stay on the main thread)
  filters.py     One Euro filter that smooths the landmarks
  gestures.py    landmarks -> hand shape, hand position, stable gesture
  controller.py  hand shape + movement -> camera (rotate, zoom, reset, clutch)
  logger.py      CSV event log per session, saved in logs/
  study.py       study session: participant, condition, task markers
backend/         Vercel API + admin page that collects study results (see "Study backend")
tutorial/        M1 tutorial code (MediaPipe, RDKit, PyVista), see tutorial/README.md
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

## Team

CSCI 4250 Group 2. Task numbers (T1–T15) are from our implementation plan.

| Member | Role | Contributions |
|---|---|---|
| Zach | Implementation | Gesture detection: the fist, pinch and open palm rules and their tests come from his JavaScript MVP, ported to `handson/gestures.py` and `tests/test_gestures.py` (T1) |
| Mo | Implementation | First gesture-to-camera controller with unit tests (PR #1, T2) |
| Ahmet | Project management and QA | Test setup and GitHub workflow (T3); Python app, false-trigger reduction, status panel, study mode and results analysis (T5, T6, T8–T11) |
| Ali | Video and UI design | Status card design and the gesture artwork in `handson/assets/` (T4) |
